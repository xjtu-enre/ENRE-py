import ast
import typing as ty
from pathlib import Path

from enre.analysis.env import EntEnv, ScopeEnv, get_from_bindings
from enre.cfg.module_tree import FileSummary, SummaryBuilder, ModuleSummary, ClassSummary, FunctionSummary, Scene
from enre.ent.EntKind import RefKind
from enre.ent.entity import Module, UnknownModule, Package, Entity, get_anonymous_ent, Class, Function, AbstractValue
from enre.ref.Ref import Ref

if ty.TYPE_CHECKING:
    from enre.analysis.env import Bindings


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
    def __init__(self, project_root: Path, module_ent: Module):
        from enre.dep.DepDB import DepDB
        self.project_root = project_root
        self.module_path = module_ent.module_path
        self.module_ent = module_ent
        self.dep_db = DepDB()
        self.dep_db.add_ent(self.module_ent)
        self.ent_id_set: ty.Set[int] = set()
        self._tree = self.parse_a_module(self.module_path)
        self.analyzed_set: ty.Set[ast.AST] = set()

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
        except (SyntaxError, UnicodeDecodeError):
            return ast.Module([])

    def get_module_level_bindings(self) -> "Bindings":
        bindings: Bindings = []
        for name, ents in self.module_ent.names.items():
            bound_ents = [(ent, ent.direct_type()) for ent in ents]
            bindings.append((name, bound_ents))
        return bindings


class RootDB:
    def __init__(self, root_path: Path):
        from enre.dep.DepDB import DepDB
        self.root_dir = root_path
        self.global_db = DepDB()
        self.tree: ty.Dict[Path, ModuleDB] = dict()
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
                        package_ent.add_ref(Ref(RefKind.ContainKind, sub_package_ent, 0, 0, False, None))
                    elif sub_path in self.tree:
                        module_ent = self.tree[sub_path].module_ent
                        package_ent.add_ref(Ref(RefKind.ContainKind, module_ent, 0, 0, False, None))

        return py_files

    def get_module_db_of_path(self, item: Path) -> ModuleDB:
        return self.tree[item]

    def get_path_ent(self, path: Path) -> ty.Union["Package", "Module"]:
        if path in self.tree:
            return self.tree[path].module_ent
        else:
            return self.package_tree[path]

    def add_ent_global(self, ent: "Entity") -> None:
        self.global_db.add_ent(ent)

    def add_ent_local(self, file_path: Path, ent: "Entity") -> None:
        self.tree[file_path].add_ent(ent)


def merge_db(package_db: RootDB) -> "DepDB":
    raise NotImplementedError("not implemented yet")


class AnalyzeManager:
    def __init__(self, root_path: Path, builtin_path: ty.Optional[Path]):
        self.project_root = root_path
        self.root_db = RootDB(root_path)
        self.module_stack = ModuleStack()
        self.scene: Scene = Scene()
        self.builtin_path = builtin_path
        self.builtins_bindings: ty.Optional[Bindings] = None
        if builtin_path:
            self.root_db.tree[builtin_path] = ModuleDB(self.project_root,
                                                       Module(builtin_path, hard_longname=["builtins"]))

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
        from enre.passes.build_ambiguous import BuildAmbiguous
        from enre.passes.build_visibility import BuildVisibility
        self.analyze_builtins()
        self.iter_dir(self.project_root)
        build_ambiguous_pass = BuildAmbiguous(self.root_db)
        build_ambiguous_pass.execute_pass()
        build_visibility_pass = BuildVisibility(self.root_db)
        build_visibility_pass.work_flow()

    def iter_dir(self, path: Path) -> None:
        from enre.analysis.analyze_stmt import Analyzer
        print(path)
        if path.is_dir():
            for sub_file in path.iterdir():
                self.iter_dir(sub_file)
        elif path.name.endswith(".py"):
            rel_path = path.relative_to(self.project_root.parent)
            if self.module_stack.finished_module(rel_path):
                print(f"the module {rel_path} already imported by some analyzed module")
                return
            else:
                self.module_stack.push(rel_path)
                self.analyze_module_top_stmts(rel_path)
                self.module_stack.pop()

    def analyze_module_top_stmts(self, rel_path: Path) -> None:
        from enre.analysis.analyze_stmt import Analyzer
        module_ent = self.root_db.get_module_db_of_path(rel_path).module_ent
        checker = Analyzer(rel_path, self)
        module_summary = self.create_file_summary(module_ent)
        builder = SummaryBuilder(module_summary)
        top_scope = ScopeEnv(module_ent, module_ent.location, SummaryBuilder(module_summary))
        if self.builtin_path:
            builtins_module_db = self.root_db.get_module_db_of_path(self.builtin_path)
            self.add_builtins_binding_to_scope(builtins_module_db, top_scope)
        checker.analyze_top_stmts(checker.current_db.tree.body, builder,
                                  EntEnv(top_scope))

    def add_builtins_binding_to_scope(self, module_db: ModuleDB, scope: ScopeEnv) -> None:
        if self.builtins_bindings:
            scope.add_continuous(self.builtins_bindings)
            return
        bindings: Bindings = module_db.get_module_level_bindings()
        bindings.append(("builtins", [(module_db.module_ent, module_db.module_ent.direct_type())]))
        scope.add_continuous(bindings)
        self.builtins_bindings = bindings

    def analyze_builtins(self) -> None:
        from enre.analysis.analyze_stmt import Analyzer
        if not self.builtin_path:
            return
        checker = Analyzer(self.builtin_path, self)
        module_ent = self.root_db.get_module_db_of_path(self.builtin_path).module_ent
        module_summary = self.create_file_summary(module_ent)
        builder = SummaryBuilder(module_summary)
        checker.analyze_top_stmts(checker.current_db.tree.body, builder,
                                  EntEnv(ScopeEnv(module_ent, module_ent.location,
                                                  SummaryBuilder(module_summary))))

    def need_analyze(self, rel_path: Path) -> bool:
        return self.module_stack.in_process(rel_path) or self.module_stack.finished_module(rel_path)

    def import_module(self, from_module_ent: Module, module_identifier: str,
                      lineno: int, col_offset: int, strict: bool) -> ty.Tuple[
        ty.Union[Module, Package], ty.Union[Module, Package]]:
        rel_path, head_module_path = self.alias2path(from_module_ent.module_path, module_identifier)
        if self.need_analyze(rel_path):
            return self.root_db.get_module_db_of_path(rel_path).module_ent, self.root_db.get_path_ent(head_module_path)
        elif (p := self.resolve_import(from_module_ent, rel_path)) is not None:
            if p.is_file():
                module_ent = self.root_db.get_module_db_of_path(rel_path).module_ent
                if strict:
                    self.strict_analyze_module(module_ent)
                return module_ent, self.root_db.get_path_ent(head_module_path)
            elif rel_path in self.root_db.package_tree:
                package_ent = self.root_db.package_tree[rel_path]
                if p.joinpath("__init__.py").exists():
                    return self.import_module(from_module_ent, f"{module_identifier}.__init__", lineno, col_offset,
                                              strict)
                return package_ent, self.root_db.get_path_ent(rel_path)
            else:
                package_ent = Package(rel_path)
                self.root_db.package_tree[rel_path] = package_ent
                return package_ent, self.root_db.get_path_ent(rel_path)
        else:
            unknown_module_name = module_identifier.split(".")[-1]
            unknown_module_ent = UnknownModule(unknown_module_name)
            module_db = self.root_db.get_module_db_of_path(from_module_ent.module_path)
            module_db.add_ent(unknown_module_ent)
            from_module_ent.add_ref(Ref(RefKind.ImportKind, unknown_module_ent, lineno, col_offset, False, None))
            return unknown_module_ent, unknown_module_ent
            # raise NotImplementedError("unknown module not implemented yet")

    def strict_analyze_module(self, module_ent: Module) -> None:
        if self.module_stack.in_process(module_ent.module_path) or \
                self.module_stack.finished_module(module_ent.module_path):
            return
        from enre.analysis.analyze_stmt import Analyzer
        rel_path = module_ent.module_path
        self.module_stack.push(rel_path)
        print(f"importing the module {rel_path} now analyzing this module")
        self.analyze_module_top_stmts(rel_path)
        print(f"module {rel_path} finished")
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

    def get_from_builtins(self, name: str) -> "ty.Optional[AbstractValue]":
        if self.builtins_bindings:
            return get_from_bindings(name, self.builtins_bindings)
        else:
            return None

    def resolve_import(self, from_module: Module, rel_path: Path) -> ty.Optional[Path]:
        project_root = self.project_root
        parent_dir = project_root.parent.joinpath(from_module.module_path.parent)
        while True:
            target_module_path = parent_dir.joinpath(rel_path)
            if target_module_path.exists() and target_module_path.relative_to(project_root.parent) in self.root_db.tree:
                return target_module_path
            if parent_dir.samefile(project_root.parent):
                break
            parent_dir = parent_dir.parent

        return None

    def in_root_db(self, path: Path) -> bool:
        project_root = self.project_root
        return path.exists() and path.relative_to(project_root.parent) in self.root_db.tree
