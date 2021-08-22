import ast
from abc import ABC, abstractmethod
from typing import Tuple, List

from dep.DepDB import DepDB
from ent.EntKind import RefKind
from ent.entity import Entity, Class, UnknownVar, Module, ReferencedAttribute, Location, UnresolvedAttribute, \
    ModuleAlias
from interp.env import EntEnv
# AValue stands for Abstract Value
from ref.Ref import Ref


class EntType(ABC):

    @classmethod
    def get_bot(cls) -> "AnyType":
        return _any_type

    @abstractmethod
    def join(self, rhs: "EntType") -> "EntType":
        pass


class ClassType(EntType):
    def __init__(self, class_ent: Class):
        self.class_ent = class_ent

    def join(self, rhs: "EntType") -> "EntType":
        ...


class ConstructorType(EntType):
    def __init__(self, class_ent: Class):
        self.class_ent = class_ent

    def to_class_type(self) -> ClassType:
        return ClassType(self.class_ent)

    def join(self, rhs: "EntType") -> "EntType":
        if isinstance(rhs, ConstructorType) and rhs.class_ent == self.class_ent:
            return self
        else:
            return EntType.get_bot()


# Every Module Entity is Module Type
class ModuleType(EntType):
    @classmethod
    def get_module_type(cls) -> "ModuleType":
        return _module_type

    def join(self, rhs: "EntType") -> "EntType":
        return EntType.get_bot()


class AnyType(EntType):
    def join(self, rhs: "EntType") -> "EntType":
        return _any_type


_any_type = AnyType()
_module_type = ModuleType()


class Avaler:

    def __init__(self, dep_db: DepDB):
        self._dep_db = dep_db

    def aval(self, expr: ast.expr, env: EntEnv) -> List[Tuple[Entity, EntType]]:
        """Visit a node."""
        method = 'aval_' + expr.__class__.__name__
        visitor = getattr(self, method, self.generic_aval)
        return visitor(expr, env)

    def generic_aval(self, expr: ast.expr, env: EntEnv) -> List[Tuple[Entity, EntType]]:
        """Called if no explicit visitor function exists for a node."""
        ret = EntType.get_bot()
        for field, value in ast.iter_fields(expr):
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, ast.expr):
                        avalue = self.aval(item, env)
                        for _, ent_type in avalue:
                            ret = ret.join(ent_type)
            elif isinstance(value, ast.expr):
                avalue = self.aval(value, env)
                for _, ent_type in avalue:
                    ret = ret.join(ent_type)

        return [(Entity.get_anonymous_ent(), ret)]

    def aval_Name(self, name_expr: ast.Name, env: EntEnv) -> List[Tuple[Entity, EntType]]:
        ent_objs = env[name_expr.id]
        ctx = env.get_ctx()
        for ent, ent_type in ent_objs:
            self._dep_db.add_ref(ctx, Ref(RefKind.UseKind, ent))
        if ent_objs != []:
            return ent_objs
        else:
            return [(UnknownVar(name_expr.id, env.get_scope().get_location()), EntType.get_bot())]

    def aval_Attribute(self, attr_expr: ast.Attribute, env: EntEnv) -> List[Tuple[Entity, EntType]]:
        possible_ents = self.aval(attr_expr.value, env)
        attribute = attr_expr.attr
        ret: List[Tuple[Entity, EntType]] = []
        for ent, ent_type in possible_ents:
            if isinstance(ent_type, ClassType):
                class_ent = ent_type.class_ent
                attr_ents = self._dep_db.get_class_attributes(class_ent, attribute)
                process_known_attr(attr_ents, attribute, ret, self._dep_db)
            elif isinstance(ent_type, ConstructorType):
                class_ent = ent_type.class_ent
                attr_ents = self._dep_db.get_class_attributes(class_ent, attribute)
                process_known_attr(attr_ents, attribute, ret, self._dep_db)
            elif isinstance(ent_type, ModuleType) and (isinstance(ent, Module) or isinstance(ent, ModuleAlias)):
                attr_ents = self._dep_db.get_module_attributes(ent, attribute)
                process_known_attr(attr_ents, attribute, ret, self._dep_db)
            elif isinstance(ent_type, AnyType):
                location = Location.global_name(attribute)
                referenced_attr = ReferencedAttribute(location.to_longname(), location)
                self._dep_db.add_ent(referenced_attr)
                ret.append((referenced_attr, EntType.get_bot()))
            else:
                raise NotImplementedError("attribute receiver entity matching not implemented")
        for ent, _ in ret:
            self._dep_db.add_ref(env.get_ctx(), Ref(RefKind.UseKind, ent))
        return ret

    def aval_Call(self, call_expr: ast.Call, env: EntEnv) -> List[Tuple[Entity, EntType]]:
        possible_callers = self.aval(call_expr.func, env)
        ret: List[Tuple[Entity, EntType]] = []
        for caller, func_type in possible_callers:
            if isinstance(func_type, ConstructorType):
                ret.append((Entity.get_anonymous_ent(), func_type.to_class_type()))
            else:
                ret.append((Entity.get_anonymous_ent(), EntType.get_bot()))
            self._dep_db.add_ref(env.get_ctx(), Ref(RefKind.CallKind, caller))
        return ret


def process_known_attr(attr_ents, attribute, ret, dep_db) -> None:
    if attr_ents != []:
        ret.extend([(ent_x, EntType.get_bot()) for ent_x in attr_ents])
    else:
        location = Location.global_name(attribute)
        unresolved = UnresolvedAttribute(location.to_longname(), location)
        dep_db.add_ent(unresolved)
        ret.append((unresolved, EntType.get_bot()))


class SetAvaler:
    def __init__(self, dep_db: DepDB):
        self._dep_db = dep_db
        self._avaler = Avaler(dep_db)

    def aval(self, expr: ast.expr, env: EntEnv) -> List[Tuple[Entity, EntType]]:
        """Visit a node."""
        method = 'aval_' + expr.__class__.__name__
        visitor = getattr(self, method, self._avaler.aval)
        return visitor(expr, env)

    def aval_Name(self, name_expr: ast.Name, env: EntEnv) -> List[Tuple[Entity, EntType]]:
        ent_objs = env[name_expr.id]
        ctx = env.get_ctx()
        for ent, ent_type in ent_objs:
            self._dep_db.add_ref(ctx, Ref(RefKind.SetKind, ent))
        if ent_objs != []:
            return ent_objs
        else:
            return [(UnknownVar(name_expr.id, env.get_scope().get_location()), EntType.get_bot())]

    def aval_Attribute(self, attr_expr: ast.Attribute, env: EntEnv) -> List[Tuple[Entity, EntType]]:
        possible_ents = self.aval(attr_expr.value, env)
