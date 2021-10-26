import ast
from typing import Sequence
from typing import Tuple, List

from dep.DepDB import DepDB
from ent.EntKind import RefKind
from ent.ent_finder import get_class_attr, get_module_level_ent
from ent.entity import Entity, UnknownVar, Module, ReferencedAttribute, Location, UnresolvedAttribute, \
    ModuleAlias
from interp.enttype import EntType, ConstructorType, ClassType, ModuleType, AnyType
from interp.env import EntEnv
# AValue stands for Abstract Value
from interp.manager_interp import PackageDB, ModuleDB
from ref.Ref import Ref


class UseAvaler:

    def __init__(self, package_db: PackageDB, current_db: ModuleDB):
        self._package_db = package_db
        self._current_db = current_db

    def aval(self, expr: ast.expr, env: EntEnv) -> List[Tuple[Entity, EntType]]:
        """Visit a node."""
        method = 'aval_' + expr.__class__.__name__
        visitor = getattr(self, method, self.generic_aval)
        return visitor(expr, env)

    def generic_aval(self, expr: ast.expr, env: EntEnv) -> List[Tuple[Entity, EntType]]:
        """Called if no explicit visitor function exists for a node."""
        ret: EntType = EntType.get_bot()
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
            ctx.add_ref(Ref(RefKind.UseKind, ent, name_expr.lineno, name_expr.col_offset))
        if ent_objs != []:
            return ent_objs
        else:
            return [(UnknownVar(name_expr.id, env.get_scope().get_location()), EntType.get_bot())]

    def aval_Attribute(self, attr_expr: ast.Attribute, env: EntEnv) -> List[Tuple[Entity, EntType]]:

        possible_ents = self.aval(attr_expr.value, env)
        attribute = attr_expr.attr
        ret: List[Tuple[Entity, EntType]] = []
        extend_possible_attribute(attribute, possible_ents, ret, self._package_db, self._current_db)
        for ent, _ in ret:
            env.get_ctx().add_ref(Ref(RefKind.UseKind, ent, attr_expr.lineno, attr_expr.col_offset))
        return ret

    def aval_Call(self, call_expr: ast.Call, env: EntEnv) -> List[Tuple[Entity, EntType]]:
        call_avaler = CallAvaler(self._package_db, self._current_db)
        possible_callers = call_avaler.aval(call_expr.func, env)
        ret: List[Tuple[Entity, EntType]] = []
        for caller, func_type in possible_callers:
            if isinstance(func_type, ConstructorType):
                ret.append((Entity.get_anonymous_ent(), func_type.to_class_type()))
            else:
                ret.append((Entity.get_anonymous_ent(), EntType.get_bot()))
            env.get_ctx().add_ref(Ref(RefKind.CallKind, caller, call_expr.lineno, call_expr.col_offset))
        return ret


def extend_possible_attribute(attribute: str, possible_ents: List[Tuple[Entity, EntType]], ret, package_db: PackageDB,
                              current_db: ModuleDB):
    for ent, ent_type in possible_ents:
        if isinstance(ent_type, ClassType):
            class_ent = ent_type.class_ent
            class_attrs = get_class_attr(class_ent, attribute)
            process_known_attr(class_attrs, attribute, ret, current_db, ent_type.class_ent, ent_type)
        elif isinstance(ent_type, ConstructorType):
            class_ent = ent_type.class_ent
            class_attrs = get_class_attr(class_ent, attribute)
            process_known_attr(class_attrs, attribute, ret, current_db, ent_type.class_ent, ent_type)
        elif isinstance(ent_type, ModuleType) and isinstance(ent, Module):
            module_level_ents = get_module_level_ent(ent, attribute)
            process_known_attr(module_level_ents, attribute, ret, current_db, ent, ent_type)
        elif isinstance(ent_type, ModuleType) and isinstance(ent, ModuleAlias):
            module_path = ent.module_path
            if module_path not in package_db.tree:
                continue
            module_ent = package_db[module_path].module_ent
            module_level_ents = get_module_level_ent(module_ent, attribute)
            process_known_attr(module_level_ents, attribute, ret, current_db, ent, ent_type)
        elif isinstance(ent_type, AnyType):
            location = Location.global_name(attribute)
            referenced_attr = ReferencedAttribute(location.to_longname(), location)
            current_db.add_ent(referenced_attr)
            ret.append((referenced_attr, EntType.get_bot()))
        else:
            raise NotImplementedError("attribute receiver entity matching not implemented")


def process_known_attr(attr_ents: Sequence[Entity], attribute: str, ret: List[Tuple[Entity, EntType]], dep_db: ModuleDB,
                       container: Entity, receiver_type: EntType) -> None:
    if attr_ents != []:
        # when get attribute of another entity, presume

        ret.extend([(ent_x, ent_x.direct_type()) for ent_x in attr_ents])
    else:
        # unresolved shouldn't be global
        location = container.location.append(attribute)
        unresolved = UnresolvedAttribute(location.to_longname(), location, receiver_type)
        dep_db.add_ent(unresolved)
        # dep_db.add_ref(container, Ref(RefKind.DefineKind, unresolved, 0, 0))
        # till now can't add `Define` reference to unresolved reference. If we do so, we could have duplicate  `Define`
        # relation in the class entity, while in a self set context.
        ret.append((unresolved, EntType.get_bot()))


class SetAvaler:
    def __init__(self, package_db: PackageDB, current_db: ModuleDB):
        self._package_db = package_db
        self._current_db = current_db
        self._avaler = UseAvaler(package_db, current_db)

    def aval(self, expr: ast.expr, env: EntEnv) -> List[Tuple[Entity, EntType]]:
        """Visit a node."""
        method = 'aval_' + expr.__class__.__name__
        visitor = getattr(self, method, self._avaler.aval)
        return visitor(expr, env)

    def aval_Name(self, name_expr: ast.Name, env: EntEnv) -> List[Tuple[Entity, EntType]]:
        # while in a set context, only entity in the current scope visible
        ent_objs = env.get_scope()[name_expr.id]
        if ent_objs != []:
            return ent_objs
        else:
            return [(UnknownVar(name_expr.id, env.get_scope().get_location()), EntType.get_bot())]

    def aval_Attribute(self, attr_expr: ast.Attribute, env: EntEnv) -> List[Tuple[Entity, EntType]]:
        possible_receivers = self._avaler.aval(attr_expr.value, env)
        attribute = attr_expr.attr
        ret: List[Tuple[Entity, EntType]] = []
        extend_possible_attribute(attribute, possible_receivers, ret, self._package_db, self._current_db)
        return ret


class CallAvaler:
    def __init__(self, package_db: PackageDB, current_db: ModuleDB):
        self._package_db = package_db
        self._current_db = current_db
        self._avaler = UseAvaler(package_db, current_db)

    def aval(self, expr: ast.expr, env: EntEnv) -> List[Tuple[Entity, EntType]]:
        """Visit a node."""
        method = 'aval_' + expr.__class__.__name__
        visitor = getattr(self, method, self._avaler.aval)
        return visitor(expr, env)

    def aval_Name(self, name_expr: ast.Name, env: EntEnv) -> List[Tuple[Entity, EntType]]:
        ent_objs = env[name_expr.id]
        if ent_objs:
            return ent_objs
        else:
            return [(UnknownVar(name_expr.id, env.get_scope().get_location()), EntType.get_bot())]

    def aval_Attribute(self, attr_expr: ast.Attribute, env: EntEnv) -> List[Tuple[Entity, EntType]]:
        possible_receivers = self._avaler.aval(attr_expr.value, env)
        attribute = attr_expr.attr
        ret: List[Tuple[Entity, EntType]] = []
        extend_possible_attribute(attribute, possible_receivers, ret, self._package_db, self._current_db)
        return ret
