import ast
import typing
from abc import abstractmethod, ABC
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Dict, TypeAlias, Tuple, Callable


from enre.analysis.analyze_method import AbstractClassInfo, FunctionKind
from enre.analysis.value_info import ValueInfo, ModuleType, UnionType, AnyType, ListType, UnknownVarType, \
    ReferencedAttrType, ConstructorType
from enre.ent.EntKind import EntKind, RefKind

if typing.TYPE_CHECKING:
    from enre.ref.Ref import Ref
    from enre.analysis.env import ScopeEnv, EntEnv

_EntityID = 0


class EntLongname:
    @property
    def longname(self) -> str:
        return '.'.join(self._scope)

    @property
    def name(self) -> str:
        return self._scope[-1]

    @property
    def module_name(self) -> str:
        return self._scope[0]

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

    def __str__(self):
        return self.longname


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

    def span_offset(self, offset: int) -> None:
        self.start_col = self.end_col
        self.end_col += offset

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

    def __str__(self):
        return self._file_path.__str__() + " " + self._span.__str__()

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
        self.exported = False
        self.type: "ValueInfo" = ValueInfo.get_any()
        self.children = set()

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
            if ref.ref_kind == RefKind.ChildOfKind:
                ref.target_ent.children.add(self)

    def __str__(self):
        return self.longname.longname

    def __eq__(self, other: object) -> bool:
        if isinstance(other, self.__class__):
            return other.longname == self.longname and other.location == self.location
        return False

    def direct_type(self) -> "ValueInfo":
        return self.type

    def __hash__(self) -> int:
        return hash((self.longname, self.location))

    def add_type(self, target: "ValueInfo") -> None:
        self.type = UnionType.union(self.type, target)

    def set_type(self, target: "ValueInfo") -> None:
        self.type = target


class NameSpaceEntity(ABC):
    @property
    @abstractmethod
    def names(self) -> "NamespaceType":
        ...


# AbstractValue instance contains all possible result of a an expression
# A possible result is a tuple of entity and entity's type.
# If some entity, to which an expression evaluate, maybe bound to several types,
# the abstract value will contain the tuple of the entity to those types.
AbstractValue: TypeAlias = List[Tuple[Entity, ValueInfo]]
MemberDistiller: TypeAlias = Callable[[int], AbstractValue]
NamespaceType: TypeAlias = Dict[str, List[Entity]]


class Variable(Entity):
    def __init__(self, longname: EntLongname, location: Location):
        super().__init__(longname, location)

    def kind(self) -> EntKind:
        return EntKind.Variable


class Parameter(Entity):
    def __init__(self, longname: EntLongname, location: Location):
        super(Parameter, self).__init__(longname, location)
        self.has_default = False
        self.default = ValueInfo.get_any()

    def kind(self) -> EntKind:
        return EntKind.Parameter


class LambdaParameter(Parameter):
    def __init__(self, longname: EntLongname, location: Location):
        super(LambdaParameter, self).__init__(longname, location)

    def kind(self) -> EntKind:
        return EntKind.LambdaParameter


@dataclass
class Signature:
    identifier: str
    posonlyargs: List["Parameter"]
    kwonlyargs: Dict[str, "Parameter"]
    stararg: Optional["Parameter"]
    starstararg: Optional["Parameter"]
    return_type: Optional["ValueInfo"]
    is_func: bool  # function is true, class is false
    is_overload: bool
    has_stararg: bool
    has_starstararg: bool
    """Function signature likes this:
    def foo(x: int) -> Any
    def method(self, y: str) -> int
    """

    def __init__(self, ident, is_func, func_ent: Optional["Function"] = None):
        self.identifier = ident
        self.posonlyargs = []
        self.kwonlyargs = dict()
        self.stararg = None
        self.starstararg = None
        self.return_type = ValueInfo.get_any()
        self.is_func = is_func
        self.is_overload = False
        self.func_ent = func_ent
        self.has_stararg = False
        self.has_starstararg = False

    def append_posonlyargs(self, para: Parameter):
        self.posonlyargs.append(para)

    def append_kwonlyargs(self, kw: str, para: Parameter):
        self.kwonlyargs[kw] = para

    def get_posonlyargs(self, index: int) -> Parameter:
        return self.posonlyargs[index]

    def get_kwonlyargs(self, kw: str) -> Parameter:
        return self.kwonlyargs.get(kw)

    def get_stararg(self) -> Parameter:
        return self.stararg

    def get_starstararg(self) -> Parameter:
        return self.starstararg

    def set_return_type(self, return_type: "ValueInfo") -> None:
        self.return_type = UnionType.union(self.return_type, return_type)

    def get_return_type(self) -> "ValueInfo":
        return self.return_type

    def function_call_least_posonlyargs_length(self) -> int:
        counter = 0
        for arg in self.posonlyargs:
            if not arg.has_default:
                counter = counter + 1
        return counter

    def function_call_least_kwonlyargs_length(self) -> int:
        counter = 0
        for kw, arg in self.kwonlyargs.items():
            assert isinstance(arg, Parameter)
            if not arg.has_default:
                counter = counter + 1
        return counter

    def __str__(self):
        res = "def " if self.is_func else "class "
        res += self.identifier
        if self.posonlyargs or self.kwonlyargs or self.is_func:
            res += "("
        for index, arg in enumerate(self.posonlyargs):
            temp = ""
            if index != 0:
                temp += ", "
            if self.is_func:
                temp += arg.longname.name
                temp += ": "
            # if not isinstance(arg.type, AnyType):
            temp += arg.type.__str__()
            res += temp

        # stararg
        if self.is_func and self.func_ent and self.has_stararg:
            if res[-1] != "(":
                res += ", "
            res += "*" + self.stararg.longname.name
            res += ": " + self.stararg.type.__str__()

        if self.kwonlyargs:
            res += ", *, "
        count = 0
        for k, v in self.kwonlyargs.items():
            temp = ""
            if count != 0:
                temp += ", "
            temp += k
            if not isinstance(v.type, AnyType):
                temp += ": " + v.type.__str__()
            res += temp
            count += 1
        # starstararg
        if self.is_func and self.func_ent and self.has_starstararg:
            if res[-1] != "(":
                res += ", "
            res += "**" + self.starstararg.longname.name
            res += ": " + self.starstararg.type.__str__()

        if self.posonlyargs or self.kwonlyargs or self.is_func:
            res += ")"
        if self.is_func:
            res += " -> " + self.return_type.__str__()
        return res


class Function(Entity):
    def __init__(self, longname: EntLongname, location: Location):
        super(Function, self).__init__(longname, location)
        self.abstract_kind: Optional[FunctionKind] = None
        self.static_kind: Optional[FunctionKind] = None
        self.readonly_property_name: Optional[str] = None
        self._function: bool = True
        self._env = None
        self._scope_env = None
        self._body = None
        self._rel_path = None
        # self._type = None
        self._arrows = dict()
        self.current_db = None
        self.calling_stack = []

        self.summary = None

        # self.signature = Signature(longname.name, True, self)
        self.signatures = []
        self.callable_signature = None
        self.typeshed_func = False

        self.decorators = []

        # from type is a tuple type
        # to type is a Union type?
        # but they are all type

    def kind(self) -> EntKind:
        return EntKind.Function if self._function else EntKind.Method

    def set_body_env(self, env: "EntEnv", scope: "ScopeEnv", rel_path: Path):
        self._env = env
        self._scope_env = scope
        self._rel_path = rel_path

    def get_body_env(self) -> ("EntEnv", "ScopeEnv", Path):
        return self._env, self._scope_env, self._rel_path

    def get_scope_env(self):
        return self._scope_env

    def set_body(self, body):
        self._body = body

    def get_body(self):
        return self._body

    def set_method(self):
        self._function = False

    def set_direct_type(self, direct_type: "ValueInfo"):
        self.type = direct_type

    def direct_type(self) -> "ValueInfo":
        return self.type

    def set_mapping(self, from_type: "ListType", to_type: "UnionType" = ValueInfo.get_any()):
        self._arrows[from_type] = to_type

    def get_mapping(self, from_type: "ListType"):
        return self._arrows.get(from_type)

    def has_mapping(self, from_type: "ListType"):
        return from_type in self._arrows

    def append_signature(self, signature: Signature):
        self.signatures.append(signature)


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
        self.exported = True

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
    def __init__(self, file_path: Path, hard_longname: Optional[List[str]] = None, is_stub: bool = False):
        # file_path: relative path to root directory's parent
        import os
        path = os.path.normpath(str(file_path)[:-len(".py")])
        path_list = path.split(os.sep) if hard_longname is None else hard_longname
        longname = EntLongname(path_list)
        location = Location(file_path, Span.get_nil(), path_list)
        super(Module, self).__init__(longname, location)
        self.module_path = file_path
        self._names: "NamespaceType" = defaultdict(list)
        self._is_stub = is_stub
        self.absolute_path = None
        self.exported = True

    def kind(self) -> EntKind:
        return EntKind.Module

    @property
    def names(self) -> "NamespaceType":
        return self._names

    def add_ref(self, ref: "Ref") -> None:
        if ref.ref_kind == RefKind.DefineKind:
            self._names[ref.target_ent.longname.name].append(ref.target_ent)
        elif ref.ref_kind == RefKind.ImportKind:
            self._names[ref.target_ent.longname.name].append(ref.target_ent)
        super(Module, self).add_ref(ref)

    @property
    def module_longname(self) -> EntLongname:
        return self.longname

    def direct_type(self) -> "ModuleType":
        return ModuleType(self.names)

    def is_stub(self):
        return self._is_stub


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
        self.is_exception_alias = False
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
        self._body_env = None
        self.bases = []
        self.signatures = []
        self.signature = Signature(longname.name, is_func=False)

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

    def set_body_env(self, body_env):
        self._body_env = body_env

    def get_body_env(self):
        assert self._body_env
        return self._body_env


class UnknownVar(Entity):

    def __init__(self, name: str, loc: Optional[Location] = None):
        loc = Location() if loc is None else loc
        self.names: Dict[str, List[Entity]] = defaultdict(list)
        super(UnknownVar, self).__init__(EntLongname([name]), loc)

    def direct_type(self) -> "ValueInfo":
        return UnknownVarType(self)

    def kind(self) -> EntKind:
        return EntKind.UnknownVar

    def add_ref(self, ref: "Ref") -> None:
        name = ref.target_ent.longname.name
        if ref.ref_kind == RefKind.DefineKind:
            self.names[name].append(ref.target_ent)

        super(UnknownVar, self).add_ref(ref)

    def get_attribute(self, attr: str) -> List["Entity"]:
        current_attrs = self.names[attr]
        if current_attrs:
            return current_attrs
        return []


class UnknownModule(Module):
    def __init__(self, name: str):
        super(UnknownModule, self).__init__(Path(f"{name}.py"))

    def kind(self) -> EntKind:
        return EntKind.UnknownModule


# class SubscriptEntity(Entity):
#     def __init__(self, longname: EntLongname, location: Location):
#         self.value = None
#         self.paras = []
#         super().__init__(longname, location)
#
#     def kind(self) -> EntKind:
#         return EntKind.Subscript
#
#     def __str__(self):
#         temp = self.value.__str__()
#         temp += "["
#         for i in range(len(self.paras)):
#             if i != 0:
#                 temp += ", "
#             temp += self.paras[i].__str__()
#         temp += "]"
#         return temp


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
        return EntKind.ClassAttribute

    def direct_type(self) -> "ValueInfo":
        return self.type


class ReferencedAttribute(Entity):
    def __init__(self, longname: EntLongname, location: Location):
        super(ReferencedAttribute, self).__init__(longname, location)
        self.names: Dict[str, List[Entity]] = defaultdict(list)

    def kind(self) -> EntKind:
        return EntKind.ReferencedAttr

    def direct_type(self) -> "ValueInfo":
        return ReferencedAttrType(self)

    def add_ref(self, ref: "Ref") -> None:
        name = ref.target_ent.longname.name
        if ref.ref_kind == RefKind.DefineKind:
            self.names[name].append(ref.target_ent)

        super(ReferencedAttribute, self).add_ref(ref)

    def get_attribute(self, attr: str) -> List["Entity"]:
        current_attrs = self.names[attr]
        if current_attrs:
            return current_attrs
        return []


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
