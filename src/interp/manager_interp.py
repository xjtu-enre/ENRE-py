import ast
import typing as ty
from pathlib import Path

from ent.EntKind import RefKind
from ent.entity import Module, UnknownModule
from interp.env import EntEnv, ScopeEnv
from ref.Ref import Ref


class ModuleStack:
    def __init__(self):
        self.finished_module_set: ty.Set[Path] = set()
        self.checking_stack: ty.List[Path] = []

    def pop(self) -> Path:
        finished = self.checking_stack.pop()
        self.finished_module_set.add(finished)
        return finished

    def push(self, path: Path):
        self.checking_stack.append(path)

    def finished_module(self, path: Path) -> bool:
        return path in self.finished_module_set

    def in_process(self, path: Path) -> bool:
        return path in self.checking_stack



class ModuleDB:
    def __init__(self, module_ent: Module):
        from dep.DepDB import DepDB
        self.module_path = module_ent.module_path
        self.module_ent = module_ent
        self.dep_db = DepDB()
        self.dep_db.add_ent(self.module_ent)

    def add_ent(self, ent: "Entity"):
        self.dep_db.add_ent(ent)


class PackageDB:
    def __init__(self, root_path: Path):
        from dep.DepDB import DepDB
        self.root_dir = root_path
        self.global_db = DepDB()
        self.tree: ty.Dict[Path, ModuleDB] = dict()
        self.initialize_tree(root_path)
        self.global_db.add_ent(Entity.get_anonymous_ent())

    def initialize_tree(self, path: Path):
        if path.is_file() and path.name.endswith(".py"):
            from dep.DepDB import DepDB
            module_ent = Module(path.relative_to(self.root_dir.parent))
            self.tree[path.relative_to(self.root_dir.parent)] = ModuleDB(module_ent)

        if path.is_dir():
            for file in path.iterdir():
                self.initialize_tree(file)

    def __getitem__(self, item: Path):
        return self.tree[item]

    def add_ent_global(self, ent: "Entity"):
        self.global_db.add_ent(ent)

    def add_ent_local(self, file_path: Path, ent: "Entity"):
        self.tree[file_path].add_ent(ent)


def merge_db(package_db) -> "DepDB":
    pass


class InterpManager:
    def __init__(self, root_path: Path):
        self.project_root = root_path
        self.package_db = PackageDB(root_path)
        self.dir_structure_init()
        self.module_stack = ModuleStack()

    def dir_structure_init(self, file_path=None) -> bool:
        in_package = False
        if file_path is None:
            file_path = self.project_root

        if file_path.is_dir():

            for sub_file_path in file_path.iterdir():
                if self.dir_structure_init(sub_file_path):
                    in_package = True
            if in_package:
                from ent.entity import Package
                package_ent = Package(file_path.relative_to(self.project_root.parent))
                # todo: create dependency tree per file
                self.package_db.add_ent_global(package_ent)

        elif file_path.name.endswith(".py"):
            in_package = True

        return in_package

    def work_flow(self):
        from passes.entity_pass import EntityPass
        self.iter_dir(self.project_root)
        entity_pass = EntityPass(self.package_db)
        entity_pass.resolve_referenced_attribute()

    def iter_dir(self, path):
        from .checker import AInterp
        print(path)
        if path.is_dir():
            for sub_file in path.iterdir():
                self.iter_dir(sub_file)
        elif path.lvalueexpr.endswith(".py"):
            if self.module_stack.finished_module(path):
                print(f"the module {path} already imported by some analyzed module")
                return
            else:
                rel_path = path.relative_to(self.project_root.parent)
                module_ent = self.package_db[rel_path].module_ent
                checker = AInterp(rel_path, self)
                self.module_stack.push(rel_path)
                absolute_path = self.project_root.parent.joinpath(rel_path)
                with open(absolute_path, "r", encoding="utf-8") as file:
                    checker.interp_top_stmts(ast.parse(file.read()).body,
                                             EntEnv(ScopeEnv(module_ent, module_ent.location)))
                self.module_stack.pop()

    def import_module(self, from_module_ent: Module, module_identifier: str, lineno: int, col_offset: int) -> Module:
        from .checker import AInterp
        rel_path = self.alias2path(from_module_ent.module_path, module_identifier)
        if self.module_stack.in_process(rel_path) or self.module_stack.finished_module(rel_path):

            return self.package_db[rel_path].module_ent
        elif self.project_root.joinpath(rel_path).exists():
            # new module
            module_ent = self.package_db[rel_path].module_ent
            checker = AInterp(rel_path, self)
            self.module_stack.push(rel_path)
            absolute_path = self.project_root.joinpath(rel_path)
            with open(absolute_path, "r") as file:
                checker.interp_top_stmts(ast.parse(file.read()).body,
                                         EntEnv(ScopeEnv(module_ent, module_ent.location)))
            self.module_stack.pop()
            return module_ent
        else:
            unknown_module_name = module_identifier.split(".")[-1]
            unknown_module_ent = UnknownModule(unknown_module_name)
            module_db = self.package_db[from_module_ent.module_path]
            module_db.add_ent(unknown_module_ent)
            from_module_ent.add_ref(Ref(RefKind.ImportKind, unknown_module_ent, lineno, col_offset))
            return unknown_module_ent
            # raise NotImplementedError("unknown module not implemented yet")

    def alias2path(self, from_path: Path, alias: str) -> Path:
        path_elems = alias.split(".")
        rel_path = Path("/".join(path_elems) + ".py")
        from_path = from_path.parent
        while from_path != Path():
            if self.project_root.parent.joinpath(from_path).joinpath(rel_path).exists():
                return from_path.joinpath(rel_path)
            from_path = from_path.parent
        return rel_path


from ent.entity import Entity
from dep.DepDB import DepDB
import ent.entity as entity

E = ty.TypeVar('E',
               entity.Entity,
               entity.Anonymous,
               entity.Variable,
               entity.Module,
               entity.UnknownModule,
               entity.UnknownVar,
               entity.UnresolvedAttribute,
               entity.Function,
               entity.Class,
               entity.ClassAttribute)  # Must be str or bytes
