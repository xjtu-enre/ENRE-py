import ast
import typing as ty
from pathlib import Path

from dep.DepDB import DepDB
from ent.entity import Module, UnknownModule, Location
from interp.env import EntEnv, ScopeEnv


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


class InterpManager:
    def __init__(self, root_path: Path):
        self.project_root = root_path
        self.dep_db = DepDB()
        self.dir_structure_init()
        self.module_stack = ModuleStack()
        self.dir_structure_init()

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
                self.dep_db.add_ent(package_ent)
        elif file_path.name.endswith(".py"):
            in_package = True
            from ent.entity import Module
            module_ent = Module(file_path.relative_to(self.project_root))
            self.dep_db.add_ent(module_ent)

        return in_package

    def workflow(self, path: Path = None):
        if path is None:
            path = self.project_root

        from .checker import AInterp
        if path.is_dir():
            for sub_file in path.iterdir():
                self.workflow(sub_file)
        elif path.name.endswith(".py"):
            if self.module_stack.finished_module(path):
                return
            else:
                rel_path = path.relative_to(self.project_root)
                from ent.entity import Module
                module_ent = Module(rel_path)
                checker = AInterp(module_ent, self)
                self.module_stack.push(rel_path)
                absolute_path = self.project_root.joinpath(rel_path)
                with open(absolute_path, "r") as file:
                    checker.interp_top_stmts(ast.parse(file.read()).body,
                                             EntEnv(ScopeEnv(module_ent, module_ent.location)))
                self.module_stack.pop()

    def import_module(self, from_path: Path, module_alias: str) -> Module:

        from .checker import AInterp
        rel_path = self.from_alias(from_path, module_alias)
        if self.module_stack.in_process(rel_path) or self.module_stack.finished_module(rel_path):
            from ent.entity import Module
            return Module(rel_path)
        elif self.project_root.joinpath(rel_path).exists():
            # new module
            from ent.entity import Module
            module_ent = Module(rel_path)
            checker = AInterp(module_ent, self)
            self.module_stack.push(rel_path)
            absolute_path = self.project_root.joinpath(rel_path)
            with open(absolute_path, "r") as file:
                checker.interp_top_stmts(ast.parse(file.read()).body,
                                         EntEnv(ScopeEnv(module_ent, module_ent.location)))
            self.module_stack.pop()
            return module_ent
        else:
            raise NotImplementedError("")

    def from_alias(self, from_path: Path, alias: str) -> Path:
        path_elems = alias.split(".")
        rel_path = Path("/".join(path_elems) + ".py")
        project_path = from_path.parent.joinpath(rel_path)
        return project_path
