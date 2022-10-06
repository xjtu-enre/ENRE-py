import ast
import typing
from abc import abstractmethod, ABC
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Dict, TypeAlias, Tuple, Callable

from enre.analysis.analyze_method import AbstractClassInfo, FunctionKind
from enre.analysis.value_info import ValueInfo, ModuleType, ConstructorType
from enre.ent.EntKind import EntKind, RefKind

if typing.TYPE_CHECKING:
    from enre.ref.Ref import Ref

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

    def __eq__(self, other: object) -> bool:
        if isinstance(other, EntLongname) and len(other._scope) == len(self._scope):
            for lhs, rhs in zip(self._scope, other._scope):
                if lhs != rhs:
                    return False
            return True
        return False

    def __hash__(self) -> int:
        return hash(self.longname)


@dataclass
class Span:
    start_line: int
    end_line: int
    start_col: int
    end_col: int

    @classmethod
    def get_nil(cls) -> "Span":
        return _Nil_Span

    def offset(self, offset: int) -> None:
        assert self.end_col == -1
        self.start_col += offset

    def __hash__(self) -> int:
        return hash((self.start_line, self.end_line, self.start_col, self.end_col))


def get_syntactic_span(tree: ast.AST) -> Span:
    start_line = tree.lineno
    end_line = tree.end_lineno if tree.end_lineno else -1
    # todo: fill correct location for compatibility before 3.8
    start_col = tree.col_offset
    end_col = tree.end_col_offset if tree.end_col_offset else -1
    return Span(start_line, end_line, start_col, end_col)


def get_syntactic_head(tree: ast.AST) -> Span:
    start_line = tree.lineno
    end_line = -1
    start_col = tree.col_offset
    end_col = -1
    return Span(start_line, end_line, start_col, end_col)


_Nil_Span = Span(-1, -1, -1, -1)

_Default_Empty_Path = Path()


class Location:
    def append(self, name: str, new_span: Span, new_path: Optional[Path]) -> "Location":
        if new_path is None:
            new_path = self._file_path
        return Location(new_path, new_span, self._scope + [name])

    def to_longname(self) -> EntLongname:
        return EntLongname(self._scope)

    def __init__(self, file_path: Path = _Default_Empty_Path, code_span: Span = _Nil_Span,
                 scope: Optional[List[str]] = None):
        if scope is None:
            scope = []
        self._scope: List[str] = scope
        self._span = code_span
        self._file_path = file_path

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Location) and len(other._scope) == len(self._scope):
            for lhs, rhs in zip(self._scope, other._scope):
                if lhs != rhs:
                    return False
            return True
        return False

    def __hash__(self) -> int:
        return hash((".".join(self._scope), self._file_path, self._span))

    @classmethod
    def global_name(cls, name: str) -> "Location":
        return Location(Path(), _Nil_Span, [name])

    @property
    def code_span(self) -> Span:
        return self._span

    @property
    def file_path(self) -> Path:
        return self._file_path


class Syntactic(ABC):
    @abstractmethod
    def node(self) -> ast.AST:
        ...


# Entity is the abstract domain of the Abstract Interpreter
class Entity(ABC):

    def __init__(self, longname: EntLongname, location: Location):
        global _EntityID
        self._id = _EntityID
        # make sure the id is unique
        _EntityID += 1
        self._refs: List["Ref"] = []
        self.longname = longname
        self.location = location

    def refs(self) -> List["Ref"]:
        return self._refs

    def set_refs(self, refs: List["Ref"]) -> None:
        self._refs = refs

    @property
    def id(self) -> int:
        return self._id

    @abstractmethod
    def kind(self) -> EntKind:
        ...

    def add_ref(self, ref: "Ref") -> None:
        # todo: should we remove reference with same representation?
        if ref not in self._refs:
            self._refs.append(ref)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, self.__class__):
            return other.longname == self.longname and other.location == self.location
        return False

    def direct_type(self) -> "ValueInfo":
        from enre.analysis.value_info import ValueInfo
        return ValueInfo.get_any()

    def __hash__(self) -> int:
        return hash((self.longname, self.location))


class NameSpaceEntity:
    @property
    @abstractmethod
    def names(self) -> "NamespaceType":
        ...


class ScopedEntity:
    @abstractmethod
    def get_scope(self) -> Entity:
        ...


# AbstractValue instance contains all possible result of a an expression
# A possible result is a tuple of entity and entity's type.
# If some entity, to which an expression evaluate, maybe bound to several types,
# the abstract value will contain the tuple of the entity to those types.
AbstractValue: TypeAlias = List[Tuple[Entity, ValueInfo]]
MemberDistiller: TypeAlias = Callable[[int], AbstractValue]
NamespaceType: TypeAlias = Dict[str, List[Entity]]


class Variable(Entity, ScopedEntity):
    def __init__(self, scope: Entity, longname: EntLongname, location: Location):
        self.scope = scope
        super().__init__(longname, location)

    def kind(self) -> EntKind:
        return EntKind.Variable

    def get_scope(self) -> Entity:
        return self.scope


class Function(Entity):
    def __init__(self, longname: EntLongname, location: Location):
        super(Function, self).__init__(longname, location)
        self.abstract_kind: Optional[FunctionKind] = None
        self.static_kind: Optional[FunctionKind] = None
        self.readonly_property_name: Optional[str] = None

    def kind(self) -> EntKind:
        return EntKind.Function


class LambdaFunction(Function):
    def __init__(self, longname: EntLongname, location: Location):
        super(LambdaFunction, self).__init__(longname, location)

    def kind(self) -> EntKind:
        return EntKind.AnonymousFunction


class Package(Entity, NameSpaceEntity):
    def __init__(self, file_path: Path):
        import os
        path = os.path.normpath(str(file_path))
        path_list = path.split(os.sep)
        longname = EntLongname(path_list)
        location = Location(file_path, Span.get_nil(), path_list)
        super(Package, self).__init__(longname, location)
        self._names: "NamespaceType" = defaultdict(list)
        self.package_path = file_path

    @property
    def names(self) -> "NamespaceType":
        return self._names

    def kind(self) -> EntKind:
        return EntKind.Package

    def add_ref(self, ref: "Ref") -> None:
        if ref.ref_kind == RefKind.ContainKind:
            self._names[ref.target_ent.longname.name].append(ref.target_ent)
        super(Package, self).add_ref(ref)


class Module(Entity, NameSpaceEntity):
    def __init__(self, file_path: Path, hard_longname: Optional[List[str]] = None):
        # file_path: relative path to root directory's parent
        import os
        path = os.path.normpath(str(file_path).removesuffix(".py"))
        path_list = path.split(os.sep) if hard_longname is None else hard_longname
        longname = EntLongname(path_list)
        location = Location(file_path, Span.get_nil(), path_list)
        self.module_path = file_path
        self._names: "NamespaceType" = defaultdict(list)
        super(Module, self).__init__(longname, location)

    def kind(self) -> EntKind:
        return EntKind.Module

    @property
    def names(self) -> "NamespaceType":
        return self._names

    def add_ref(self, ref: "Ref") -> None:
        if ref.ref_kind == RefKind.DefineKind:
            self._names[ref.target_ent.longname.name].append(ref.target_ent)
        super(Module, self).add_ref(ref)

    @property
    def module_longname(self) -> EntLongname:
        return self.longname

    def direct_type(self) -> "ModuleType":
        return ModuleType(self.names)


class BuiltinModule(Entity, NameSpaceEntity):
    def __init__(self, file_path: Path):
        # file_path: relative path to root directory's parent
        path_list = ["builtins"]
        longname = EntLongname(path_list)
        location = Location(file_path, Span.get_nil(), path_list)
        self.module_path = file_path
        self._names: "NamespaceType" = defaultdict(list)
        super(BuiltinModule, self).__init__(longname, location)

    def kind(self) -> EntKind:
        return EntKind.Module

    @property
    def names(self) -> "NamespaceType":
        return self._names

    def add_ref(self, ref: "Ref") -> None:
        if ref.ref_kind == RefKind.DefineKind:
            self._names[ref.target_ent.longname.name].append(ref.target_ent)
        super(BuiltinModule, self).add_ref(ref)

    @property
    def module_longname(self) -> EntLongname:
        return self.longname

    def direct_type(self) -> "ModuleType":
        return ModuleType(self.names)

    @staticmethod
    def get_BuiltinModule(builtin_path: Path) -> "BuiltinModule":
        return BuiltinModule(builtin_path)


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
        return EntKind.Alias


class PackageAlias(Entity):
    def __init__(self, package_ent: Package, alias_location: Location):
        super(PackageAlias, self).__init__(alias_location.to_longname(), alias_location)
        self.package_ent = package_ent
        self.module_path = package_ent.package_path
        self.alias_name = alias_location.to_longname().name

    @property
    def module_longname(self) -> EntLongname:
        import os
        module_path = self.module_path
        path = os.path.normpath(str(module_path))
        path_list = path.split(os.sep)
        longname = EntLongname(path_list)
        return longname

    def kind(self) -> EntKind:
        return EntKind.Alias


class Alias(Entity):
    def __init__(self, longname: EntLongname, location: Location, ents: List[Entity]) -> None:
        super(Alias, self).__init__(longname, location)
        self.possible_target_ent = ents
        self._build_alias_deps()

    def kind(self) -> EntKind:
        return EntKind.Alias

    def direct_type(self) -> "ValueInfo":
        if len(self.possible_target_ent) == 1:
            return self.possible_target_ent[0].direct_type()
        else:
            return ValueInfo.get_any()

    def _build_alias_deps(self) -> None:
        from enre.ref.Ref import Ref
        for ent in self.possible_target_ent:
            alias_span = self.location.code_span
            self.add_ref(Ref(RefKind.AliasTo, ent, alias_span.start_line, alias_span.end_line, False, None))


class Class(Entity, NameSpaceEntity):
    def __init__(self, longname: EntLongname, location: Location):
        super(Class, self).__init__(longname, location)
        self._names: Dict[str, List[Entity]] = defaultdict(list)
        self._inherits: List["Class"] = []
        self.abstract_info: Optional[AbstractClassInfo] = None
        self.readonly_attribute: NamespaceType = defaultdict(list)
        self.private_attribute: NamespaceType = defaultdict(list)

    def kind(self) -> EntKind:
        return EntKind.Class

    @property
    def names(self) -> "NamespaceType":
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
            inherited_attrs = cls_ent.get_attribute(attr)
            if inherited_attrs:
                return inherited_attrs
        return []

    def add_ref(self, ref: "Ref") -> None:
        if ref.ref_kind == RefKind.DefineKind:
            self._names[ref.target_ent.longname.name].append(ref.target_ent)
        elif ref.ref_kind == RefKind.InheritKind:
            if isinstance(ref.target_ent, Class):
                self._inherits.append(ref.target_ent)
        super(Class, self).add_ref(ref)

    def direct_type(self) -> "ValueInfo":
        return ConstructorType(self)

    def implement_method(self, longname: EntLongname) -> bool:
        method_name = longname.name
        for name, ents in self._names.items():
            if name == method_name:
                for entity in ents:
                    if isinstance(entity, Function):
                        if entity.abstract_kind:
                            return False
                        else:
                            return True
        return False


class UnknownVar(Entity):
    _unknown_pool: Dict[str, "UnknownVar"] = dict()

    def __init__(self, name: str, loc: Optional[Location] = None):
        if loc is None:
            loc = Location()
        super(UnknownVar, self).__init__(EntLongname([name]), loc)

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


class Parameter(Entity, ScopedEntity):
    def __init__(self, scope: Entity, longname: EntLongname, location: Location):
        self.scope = scope
        super(Parameter, self).__init__(longname, location)

    def kind(self) -> EntKind:
        return EntKind.Parameter

    def get_scope(self) -> Entity:
        return self.scope


class LambdaParameter(Parameter):
    def __init__(self, scope: Entity, longname: EntLongname, location: Location):
        super(LambdaParameter, self).__init__(scope, longname, location)

    def kind(self) -> EntKind:
        return EntKind.LambdaParameter


class Anonymous(Entity):
    def __init__(self) -> None:
        super(Anonymous, self).__init__(EntLongname([""]), Location())

    def kind(self) -> EntKind:
        return EntKind.Anonymous


class ClassAttribute(Entity):
    def __init__(self, class_ent: Class, longname: EntLongname, location: Location):
        self.class_ent: Class = class_ent
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
    def __init__(self, longname: EntLongname, location: Location, receiver_type: "ValueInfo") -> None:
        self.receiver_type = receiver_type
        super(UnresolvedAttribute, self).__init__(longname, location)

    def kind(self) -> EntKind:
        return EntKind.UnresolvedAttr


@dataclass(frozen=True)
class NewlyCreated:
    span: Span
    unknown_ent: typing.Union[UnknownVar, UnresolvedAttribute]


SetContextValue: TypeAlias = List[Tuple[Entity, ValueInfo] | NewlyCreated]


def get_anonymous_ent() -> "Entity":
    return _anonymous_ent


_anonymous_ent: Anonymous = Anonymous()
