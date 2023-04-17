import ast
import os
import typing as ty
from pathlib import Path



if ty.TYPE_CHECKING:
    from enre.analysis.env import Bindings

from enre.analysis.env import EntEnv, ScopeEnv
from enre.cfg.module_tree import FileSummary, SummaryBuilder, ModuleSummary, ClassSummary, FunctionSummary, Scene
from enre.ent.EntKind import RefKind
from enre.ent.entity import Module, UnknownModule, Package, Entity, get_anonymous_ent, Class, Function, Location, _Nil_Span
from enre.ref.Ref import Ref
import enre.typeshed_client as typeshed_client
from enre.typeshed_client.typeshed.frozen_path import app_path

from enre.util.logger import Logging

typeshed_path = Path(app_path("\stdlib"))
typeshed_ctx = typeshed_client.get_search_context(typeshed=typeshed_path)
builtins_stub_names = typeshed_client.get_stub_names("builtins", search_context=typeshed_ctx)
builtins_stub_file = typeshed_client.get_stub_file("builtins", search_context=typeshed_ctx)
builtins_path = Path("builtins.py")

log = Logging().getLogger(__name__)


class ModuleStack:
    def __init__(self) -> None:
        self.finished_module_set: ty.Set[Path] = set()
        self.checking_stack: ty.List[Path] = []

    def pop(self) -> Path:
        finished = self.checking_stack.pop()
        self.finished_module_set.add(finished)
        return finished

    def push(self, path: Path) -> None:
        self.checking_stack.append(path)

    def finished_module(self, path: Path) -> bool:
        return path in self.finished_module_set

    def in_process(self, path: Path) -> bool:
        return path in self.checking_stack


class ModuleDB:
    def __init__(self, project_root: Path, module_ent: Module, env: EntEnv = None, get_stub=None, stub_file=None):
        from enre.dep.DepDB import DepDB
        self.project_root = project_root
        self.module_path = module_ent.module_path
        self.module_ent = module_ent
        self.dep_db = DepDB()
        self.dep_db.add_ent(self.module_ent)
        self.ent_id_set: ty.Set[int] = set()
        self._tree = self.parse_a_module(self.module_path)
        self.analyzed_set: ty.Set[ast.AST] = set()
        self._env = env
        self._get_stub = get_stub
        self._stub_file = stub_file

    def add_ent(self, ent: "Entity") -> None:
        if ent.id not in self.ent_id_set:
            self.ent_id_set.add(ent.id)
            self.dep_db.add_ent(ent)

    @property
    def tree(self) -> ast.Module:
        return self._tree

    def parse_a_module(self, module_path: Path) -> ast.Module:
        absolute_path = self.project_root.parent.joinpath(module_path)
        try:
            return ast.parse(absolute_path.read_text(encoding="utf-8"), module_path.name)
        except (SyntaxError, UnicodeDecodeError, FileNotFoundError, OSError):
            return ast.Module([])

    def get_module_level_bindings(self) -> "Bindings":
        bindings: Bindings = []
        for name, ents in self.module_ent.names.items():
            bound_ents = [(ent, ent.direct_type()) for ent in ents]
            bindings.append((name, bound_ents))
        return bindings

    def set_env(self, env: EntEnv) -> None:
        self._env = env


class RootDB:
    def __init__(self, root_path: Path):
        from enre.dep.DepDB import DepDB
        self.root_dir = root_path
        self.global_db = DepDB()
        self.tree: ty.Dict[Path, ModuleDB] = dict()
        self.stub_tree: ty.Dict[Path, ModuleDB] = dict()
        self.package_tree: ty.Dict[Path, Package] = dict()
        self.initialize_tree(root_path)
        self.global_db.add_ent(get_anonymous_ent())

    def initialize_tree(self, path: Path) -> ty.List[Path]:
        py_files: ty.List[Path] = []
        rel_path = path.relative_to(self.root_dir.parent)
        if path.is_file() and path.name.endswith(".py"):
            py_files.append(rel_path)
            from enre.dep.DepDB import DepDB
            module_ent = Module(rel_path)
            module_ent.absolute_path = path
            self.tree[rel_path] = ModuleDB(self.root_dir, module_ent)
        elif path.is_dir():
            sub_py_files = []
            for file in path.iterdir():
                sub_py_files.extend(self.initialize_tree(file))
            py_files.extend(sub_py_files)
            if sub_py_files:
                package_ent = Package(rel_path)
                self.global_db.add_ent(package_ent)
                self.package_tree[rel_path] = package_ent
                for file in path.iterdir():
                    sub_path = file.relative_to(self.root_dir.parent)
                    if sub_path in self.package_tree:
                        sub_package_ent = self.package_tree[sub_path]
                        package_ent.add_ref(Ref(RefKind.ContainKind, sub_package_ent, -1, -1, False, None))
                        sub_package_ent.add_ref(Ref(RefKind.ChildOfKind, package_ent, -1, -1, False, None))
                    elif sub_path in self.tree:
                        module_ent = self.tree[sub_path].module_ent
                        package_ent.add_ref(Ref(RefKind.ContainKind, module_ent, -1, -1, False, None))
                        module_ent.add_ref(Ref(RefKind.ChildOfKind, package_ent, -1, -1, False, None))

        return py_files

    def __getitem__(self, item: Path) -> ModuleDB:
        return self.tree[item]

    def get_path_ent(self, path: Path) -> Module | Package | None:
        if path in self.tree:
            return self.tree[path].module_ent
        else:
            if path in self.package_tree:
                return self.package_tree[path]
            else:
                return None

    def add_ent_global(self, ent: "Entity") -> None:
        self.global_db.add_ent(ent)

    def add_ent_local(self, file_path: Path, ent: "Entity") -> None:
        self.tree[file_path].add_ent(ent)


def merge_db(package_db: RootDB) -> "DepDB":
    raise NotImplementedError("not implemented yet")


class AnalyzeManager:
    def __init__(self, root_path: Path):
        self.builtins_bindings = None
        self.project_root = root_path
        self.root_db = RootDB(root_path)
        self.module_stack = ModuleStack()
        self.scene: Scene = Scene()
        self.counter = 0

        # typeshed builtins setup
        builtins_module = Module(builtins_stub_file, hard_longname=["builtins"])
        builtins_module_summary = self.create_file_summary(builtins_module)

        self.builtins_env = EntEnv(ScopeEnv(ctx_ent=builtins_module, location=Location(builtins_stub_file, _Nil_Span, ["builtins"]),
                                            builder=SummaryBuilder(builtins_module_summary)))
        module_db = ModuleDB(builtins_stub_file, builtins_module, self.builtins_env, builtins_stub_names, builtins_stub_file)
        self.root_db.tree[builtins_path] = module_db
        self.module_stack.finished_module_set.add(builtins_path)

        self.func_invoking_set: ty.Set[Function] = set()
        self.func_uncalled_set: ty.Set[Function] = set()

    def dir_structure_init(self, file_path: ty.Optional[Path] = None) -> bool:
        in_package = False
        if file_path is None:
            file_path = self.project_root

        if file_path.is_dir():

            for sub_file_path in file_path.iterdir():
                if self.dir_structure_init(sub_file_path):
                    in_package = True
            if in_package:
                package_ent = Package(file_path.relative_to(self.project_root.parent))
                # todo: create dependency tree per file
                self.root_db.add_ent_global(package_ent)

        elif file_path.name.endswith(".py"):
            in_package = True

        return in_package

    def work_flow(self) -> None:
        from enre.passes.entity_pass import EntityPass
        from enre.passes.build_possible_candidates import BuildPossibleCandidates
        from enre.passes.build_visibility import BuildVisibility

        self.iter_dir(self.project_root)
        self.invoke_uncalled_func(self.func_uncalled_set)
        # self.save_root_db_pickle()

        EntityPass(self.root_db)
        build_possible_candidates = BuildPossibleCandidates(self.root_db)
        build_possible_candidates.execute_pass()
        build_visibility_pass = BuildVisibility(self.root_db)
        build_visibility_pass.work_flow()

    def iter_dir(self, path: Path) -> None:
        from .analyze_stmt import Analyzer

        if path.is_dir():
            for sub_file in path.iterdir():
                self.iter_dir(sub_file)
        elif path.name.endswith(".py"):
            log.info(f"Analyzing Module[{path}].")
            # print(path)
            rel_path = path.relative_to(self.project_root.parent)
            if self.module_stack.finished_module(rel_path):
                # print(f"the module {rel_path} already imported by some analyzed module")
                return
            else:
                module_ent = self.root_db[rel_path].module_ent
                checker = Analyzer(rel_path, self)
                self.module_stack.push(rel_path)
                module_summary = self.create_file_summary(module_ent)
                builder = SummaryBuilder(module_summary)

                builtins_module_db = self.root_db[builtins_path]
                top_scope = ScopeEnv(module_ent, module_ent.location, SummaryBuilder(module_summary))
                self.add_builtins_binding_to_scope(builtins_module_db, top_scope)

                checker.analyze_top_stmts(checker.current_db.tree.body, builder,
                                          EntEnv(top_scope))
                self.module_stack.pop()

    def add_builtins_binding_to_scope(self, module_db: ModuleDB, scope: ScopeEnv) -> None:
        if self.builtins_bindings:
            scope.add_continuous(self.builtins_bindings)
            return
        bindings: Bindings = module_db.get_module_level_bindings()
        bindings.append(("builtins", [(module_db.module_ent, module_db.module_ent.direct_type())]))
        scope.add_continuous(bindings)
        self.builtins_bindings = bindings

    def save_root_db_pickle(self):
        import pickle
        os.chdir(r"C:\Users\yoghurts\Desktop\Research\ENRE\Codes\ENRE-py\feat-invoke\ENRE-py")
        with open('root_db_pickle.dat', 'wb+') as f:
            pickle.dump(self.root_db, f)

        with open('root_db_pickle.dat', 'rb+') as f:
            cache_root_db = pickle.load(f)

            assert isinstance(cache_root_db, RootDB)
            rel_path = Path(r"Exp07_test10_Typename\lib.py")
            target_name = "foo"
            ret = []
            module_ent = cache_root_db[rel_path].module_ent
            for ref in module_ent.refs():
                if ref.ref_kind == RefKind.DefineKind:
                    if ref.target_ent.longname.name == target_name:
                        ret.append(ref.target_ent)

            print(ret)

    def invoke_uncalled_func(self, func_uncalled_set):
        from enre.analysis.analyze_expr import InvokeContext
        from enre.analysis.analyze_expr import invoke
        for callee in func_uncalled_set.copy():
            possible_callees = [(callee, callee.type)]
            args = []
            # if callee.longname.longname == "httpie.httpie.output.writer.write_stream_with_colors_win":
            #     print(callee)
            for pos_arg in callee.signatures[0].posonlyargs:
                args.append([(get_anonymous_ent(), pos_arg.type)])
            kwargs = dict()
            for kw, kw_arg in callee.signatures[0].kwonlyargs.items():
                kwargs[kw] = [(get_anonymous_ent(), kw_arg.type)]
            parameters = dict()
            parameters["args"] = args
            parameters["kwargs"] = kwargs
            invoke_ctx = InvokeContext(possible_callees, parameters, self, callee.current_db, None)
            invoke(invoke_ctx)

    def import_module(self, from_module_ent: Module, module_identifier: str,
                      lineno: int, col_offset: int, strict: bool) -> ty.Tuple[
        ty.Union[Module, Package], ty.Union[Module, Package]]:
        rel_path, head_module_path = self.alias2path(from_module_ent.module_path, module_identifier)
        module_name = module_identifier.split(".")[-1]
        if not rel_path.name.endswith(".py"):
            rel_path = rel_path.joinpath("__init__.py")
        if self.module_stack.in_process(rel_path) or self.module_stack.finished_module(rel_path):
            ref_ent = self.root_db[rel_path].module_ent
            head_ent = self.root_db.get_path_ent(head_module_path)
            if not head_ent:
                head_ent = ref_ent
            return ref_ent, head_ent
        elif (p := resolve_import(from_module_ent, rel_path, self.project_root)) is not None:
           #  p_init = p.joinpath("__init__.py")
            if p.is_file():
                module_ent = self.root_db[rel_path].module_ent
                if strict:
                    self.strict_analyze_module(module_ent)
                return module_ent, self.root_db.get_path_ent(head_module_path)
            elif rel_path in self.root_db.package_tree:
                package_ent = self.root_db.package_tree[rel_path]
                return package_ent, self.root_db.get_path_ent(rel_path)
            else:
                package_ent = Package(rel_path)
                self.root_db.package_tree[rel_path] = package_ent
                return package_ent, self.root_db.get_path_ent(rel_path)
        else:
            """Unknown Module Issue:
            """
            unknown_module_name = module_name
            try_get_stub = typeshed_client.get_stub_names(unknown_module_name, search_context=typeshed_ctx)
            if try_get_stub:
                stub_module_name = unknown_module_name
                stub_file_path = typeshed_client.get_stub_file(unknown_module_name, search_context=typeshed_ctx)
                stub_module = Module(stub_file_path, hard_longname=[stub_module_name], is_stub=True)
                stub_module_summary = self.create_file_summary(stub_module)
                stub_env = EntEnv(
                    ScopeEnv(ctx_ent=stub_module, location=Location(stub_file_path, _Nil_Span, [stub_module_name]),
                             builder=SummaryBuilder(stub_module_summary)))
                stub_module_db = ModuleDB(stub_file_path, stub_module, stub_env, try_get_stub, stub_file_path)
                stub_path = Path(stub_module_name + '.py')
                self.root_db.tree[stub_path] = stub_module_db
                self.module_stack.finished_module_set.add(stub_path)

                return stub_module, stub_module

            unknown_module_ent = UnknownModule(unknown_module_name)
            unknown_module_path = Path(unknown_module_name + '.py')
            if unknown_module_path in self.root_db.tree:
                cached_unknown_module = self.root_db.tree[unknown_module_path].module_ent
                return cached_unknown_module, cached_unknown_module

            stub_module_summary = self.create_file_summary(unknown_module_ent)
            stub_env = EntEnv(
                ScopeEnv(ctx_ent=unknown_module_ent,
                         location=Location(unknown_module_path,
                         _Nil_Span, [unknown_module_name]),
                         builder=SummaryBuilder(stub_module_summary)))
            stub_module_db = ModuleDB(unknown_module_path, unknown_module_ent, stub_env)

            self.root_db.tree[unknown_module_path] = stub_module_db
            self.module_stack.finished_module_set.add(unknown_module_path)

            # module_db = self.root_db[from_module_ent.module_path]
            # module_db.add_ent(unknown_module_ent)
            from_module_ent.add_ref(Ref(RefKind.ImportKind, unknown_module_ent, lineno, col_offset, False, None))
            return unknown_module_ent, unknown_module_ent
            # raise NotImplementedError("unknown module not implemented yet")

    def strict_analyze_module(self, module_ent: Module) -> None:
        if str(module_ent.module_path).endswith(".pyi"):
            module_path = Path(module_ent.longname.name + '.py')
        else:
            module_path = module_ent.module_path
        if self.module_stack.in_process(module_path) or \
                self.module_stack.finished_module(module_path):
            return
        from enre.analysis.analyze_stmt import Analyzer
        rel_path = module_ent.module_path
        checker = Analyzer(rel_path, self)
        self.module_stack.push(rel_path)
        log.info(f'Importing Module[{module_ent.absolute_path}], go to analyze this module.')
        top_stmts = self.root_db.tree[rel_path].tree.body
        module_summary = self.create_file_summary(module_ent)
        builder = SummaryBuilder(module_summary)
        module_env = EntEnv(ScopeEnv(module_ent, module_ent.location, builder))
        checker.analyze_top_stmts(top_stmts, builder, module_env)
        log.info(f"Accomplished analyzing Module[{module_ent.absolute_path}].")
        self.module_stack.pop()

    def alias2path(self, from_path: Path, alias: str) -> ty.Tuple[Path, Path]:
        def resolve_head_path(imported_path: Path, head_path: Path) -> ty.Tuple[Path, Path]:
            if str(imported_path) == str(head_path) + ".py":
                return imported_path, imported_path
            else:
                return imported_path, head_path

        path_elems = alias.split(".")
        head_module_name = path_elems[0]
        rel_path = Path("/".join(path_elems) + ".py")
        dir_rel_path = Path("/".join(path_elems))
        from_path = from_path.parent
        while True:
            if from_path == Path():
                break
            if self.project_root.parent.joinpath(from_path).joinpath(rel_path).exists():
                return resolve_head_path(from_path.joinpath(rel_path), from_path.joinpath(head_module_name))
            elif self.project_root.parent.joinpath(from_path).joinpath(dir_rel_path).exists():
                return resolve_head_path(from_path.joinpath(dir_rel_path), from_path.joinpath(head_module_name))
            from_path = from_path.parent
        return rel_path, from_path.joinpath(head_module_name)

    def add_summary(self, summary: ModuleSummary) -> None:
        self.scene.summaries.append(summary)

    def create_file_summary(self, module_ent: Module) -> FileSummary:
        summary = FileSummary(module_ent)
        self.scene.summary_map[module_ent] = summary
        self.add_summary(summary)
        return summary

    def create_class_summary(self, class_ent: Class) -> ClassSummary:
        summary = ClassSummary(class_ent)
        self.scene.summary_map[class_ent] = summary
        self.add_summary(summary)
        return summary

    def create_function_summary(self, function_ent: Function) -> FunctionSummary:
        summary = FunctionSummary(function_ent)
        self.scene.summary_map[function_ent] = summary
        self.add_summary(summary)
        return summary


def resolve_import(from_module: Module, rel_path: Path, project_root: Path) -> ty.Optional[Path]:
    parent_dir = project_root.parent.joinpath(from_module.module_path.parent)
    while not parent_dir.samefile(project_root.parent.parent):
        target_module_path = parent_dir.joinpath(rel_path)
        if target_module_path.exists():
            return target_module_path
        parent_dir = parent_dir.parent
    return None


from enre.dep.DepDB import DepDB
