import ast
from abc import abstractmethod, ABC
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Set, Dict
from ent.EntKind import EntKind, RefKind
from ref.Ref import Ref

_EntityID = 0


class EntLongname:
    @property
    def longname(self) -> str:
        return '.'.join(self._scope)

    @property
    def name(self) -> str:
        return self._scope[-1]

    def __init__(self, scope: List[str]):
        self._scope = scope

    def __eq__(self, other: object):
        if isinstance(other, EntLongname) and len(other._scope) == len(self._scope):
            for lhs, rhs in zip(self._scope, other._scope):
                if lhs != rhs:
                    return False
            return True
        return False

    def __hash__(self):
        return hash(tuple(self._scope))


@dataclass
class Span:
    @classmethod
    def get_nil(cls) -> "Span":
        return _Nil_Span

    start_line: int
    end_line: int
    start_col: int
    end_col: int


def get_syntactic_span(tree: ast.AST) -> Span:
    start_line = tree.lineno
    end_line = tree.end_lineno if tree.end_lineno else -1
    # todo: fill correct location for compatibility before 3.8
    start_col = tree.col_offset
    end_col = tree.end_col_offset if tree.end_col_offset else -1
    return Span(start_line, end_line, start_col, end_col)


_Nil_Span = Span(-1, -1, -1, -1)


class Location:
    def append(self, name: str, new_span: Span, new_path: Path = None) -> "Location":
        if new_path == None:
            new_path = self._file_path
        return Location(new_path, new_span, self._scope + [name])

    def to_longname(self) -> EntLongname:
        return EntLongname(self._scope)

    def __init__(self, file_path: Path = None, code_span: Span = None, scope: Optional[List[str]] = None):
        if scope is None:
            scope = []
        if file_path == None:
            file_path = Path()
        if code_span == None:
            code_span = _Nil_Span
        self._scope: List[str] = scope
        self._span = code_span
        self._file_path = file_path

    def __eq__(self, other: object):
        if isinstance(other, Location) and len(other._scope) == len(self._scope):
            for lhs, rhs in zip(self._scope, other._scope):
                if lhs != rhs:
                    return False
            return True
        return False

    def __hash__(self):
        return hash(tuple(self._scope))

    @classmethod
    def global_name(cls, name: str) -> "Location":
        return Location(Path(), _Nil_Span, [name])


# Entity is the abstract domain of the Abstract Interpreter
class Entity(ABC):
    @classmethod
    def get_anonymous_ent(cls) -> "Entity":
        return _anonymous_ent

    def __init__(self, longname: EntLongname, location: Location):
        global _EntityID
        self._id = _EntityID
        # make sure the id is unique
        _EntityID += 1
        self._refs: List[Ref] = []
        self.longname = longname
        self.location = location

    def refs(self) -> List[Ref]:
        return self._refs

    def set_refs(self, refs: List[Ref]):
        self._refs = refs

    @property
    def id(self) -> int:
        return self._id

    @abstractmethod
    def kind(self) -> EntKind:
        ...

    def add_ref(self, ref: Ref):
        # todo: should we remove reference with same representation?
        for ref_1 in self._refs:
            if ref_1 == ref:
                return
        self._refs.append(ref)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, self.__class__):
            return other.longname == self.longname and other.location == self.location
        return False

    def direct_type(self) -> "EntType":
        from interp.enttype import EntType
        return EntType.get_bot()

    def __hash__(self):
        return hash((self.longname, self.location))


class Variable(Entity):
    def __init__(self, longname: EntLongname, location: Location):
        super().__init__(longname, location)

    def kind(self) -> EntKind:
        return EntKind.Variable


class Function(Entity):
    def __init__(self, longname: EntLongname, location: Location):
        super(Function, self).__init__(longname, location)

    def kind(self) -> EntKind:
        return EntKind.Function


class LambdaFunction(Function):
    def __init__(self, longname: EntLongname, location: Location):
        super(LambdaFunction, self).__init__(longname, location)

    def kind(self) -> EntKind:
        return EntKind.AnonymousFunction


class Module(Entity):
    def __init__(self, file_path: Path):
        # file_path: relative path to root directory's parent
        import os
        self.module_path = file_path
        path = os.path.normpath(str(file_path)[:-len(".py")])
        path_list = path.split(os.sep)
        longname = EntLongname(path_list)
        location = Location(file_path, Span.get_nil(), path_list)
        super(Module, self).__init__(longname, location)

    def kind(self) -> EntKind:
        return EntKind.Module

    @property
    def module_longname(self) -> EntLongname:
        return self.longname

    def direct_type(self) -> "ModuleType":
        return ModuleType.get_module_type()


class ModuleAlias(Entity):
    def __init__(self, module_ent: Module, alias_location: Location):
        self.module_ent = module_ent
        self.module_path = module_ent.module_path
        self.alias_name = alias_location.to_longname().name
        super(ModuleAlias, self).__init__(alias_location.to_longname(), alias_location)

    @property
    def module_longname(self) -> EntLongname:
        import os
        module_path = self.module_path
        path = os.path.normpath(str(module_path))
        path_list = path.split(os.sep)
        longname = EntLongname(path_list)
        return longname

    def kind(self) -> EntKind:
        return EntKind.ModuleAlias


class Alias(Entity):
    def __init__(self, longname: EntLongname, location: Location, ent: Entity):
        super(Alias, self).__init__(longname, location)
        self.target_ent = ent

    def kind(self) -> EntKind:
        return EntKind.Alias


class Package(Entity):
    def __init__(self, file_path: Path):
        import os
        path = os.path.normpath(str(file_path))
        path_list = path.split(os.sep)
        longname = EntLongname(path_list)
        location = Location(file_path, Span.get_nil(), path_list)
        super(Package, self).__init__(longname, location)

    def kind(self) -> EntKind:
        return EntKind.Package


class Class(Entity):
    def __init__(self, longname: EntLongname, location: Location):
        super(Class, self).__init__(longname, location)
        self._names: Dict[str, List[Entity]] = defaultdict(list)
        self._inherits: List["Class"] = []

    def kind(self) -> EntKind:
        return EntKind.Class

    @property
    def names(self) -> Dict[str, List[Entity]]:
        # class scope, name to possible bound entities
        return self._names

    @property
    def inherits(self) -> List["Class"]:
        return self._inherits

    def get_attribute(self, attr: str) -> List[Entity]:
        current_class_attrs = self.names[attr]
        if current_class_attrs:
            return current_class_attrs
        for cls_ent in self.inherits:
            inherited_attrs = cls_ent.names[attr]
            if inherited_attrs:
                return inherited_attrs
        return []

    def add_ref(self, ref: Ref):
        if ref.ref_kind == RefKind.DefineKind:
            self._names[ref.target_ent.longname.name].append(ref.target_ent)
        super(Class, self).add_ref(ref)

    def direct_type(self) -> "EntType":
        return ConstructorType(self)


class UnknownVar(Entity):
    _unknown_pool: Dict[str, "UnknownVar"] = dict()

    def __init__(self, name: str):
        super(UnknownVar, self).__init__(EntLongname([name]), Location())

    def kind(self) -> EntKind:
        return EntKind.UnknownVar

    @classmethod
    def get_unknown_var(cls, name: str) -> "UnknownVar":
        if name in cls._unknown_pool.keys():
            return cls._unknown_pool[name]
        else:
            unknown_var = UnknownVar(name)
            cls._unknown_pool[name] = unknown_var
            return unknown_var


class UnknownModule(Module):
    def __init__(self, name: str):
        super(UnknownModule, self).__init__(Path(f"{name}.py"))

    def kind(self) -> EntKind:
        return EntKind.UnknownModule


class Parameter(Entity):
    def __init__(self, longname: EntLongname, location: Location):
        super(Parameter, self).__init__(longname, location)

    def kind(self) -> EntKind:
        return EntKind.Parameter


class LambdaParameter(Parameter):
    def __init__(self, longname: EntLongname, location: Location):
        super(LambdaParameter, self).__init__(longname, location)

    def kind(self) -> EntKind:
        return EntKind.LambdaParameter


class Anonymous(Entity):
    def __init__(self):
        super(Anonymous, self).__init__(EntLongname([""]), Location([""]))

    def kind(self) -> EntKind:
        return EntKind.Anonymous


class ClassAttribute(Entity):
    def __init__(self, longname: EntLongname, location: Location):
        super(ClassAttribute, self).__init__(longname, location)

    def kind(self) -> EntKind:
        return EntKind.ClassAttr


class ReferencedAttribute(Entity):
    def __init__(self, longname: EntLongname, location: Location):
        super(ReferencedAttribute, self).__init__(longname, location)

    def kind(self) -> EntKind:
        return EntKind.ReferencedAttr


class AmbiguousAttribute(Entity):
    def __init__(self, name: str):
        super(AmbiguousAttribute, self).__init__(EntLongname([name]), Location())

    def kind(self) -> EntKind:
        return EntKind.AmbiguousAttr


class UnresolvedAttribute(Entity):
    def __init__(self, longname: EntLongname, location: Location, receiver_type):
        self.receiver_type = receiver_type
        super(UnresolvedAttribute, self).__init__(longname, location)

    def kind(self) -> EntKind:
        return EntKind.UnresolvedAttr


_anonymous_ent: Anonymous = Anonymous()

from interp.enttype import EntType, ModuleType, ConstructorType
