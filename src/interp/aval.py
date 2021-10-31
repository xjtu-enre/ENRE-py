import ast
from typing import Sequence, Optional, TypeAlias, Callable
from typing import Tuple, List

from dep.DepDB import DepDB
from ent.EntKind import RefKind
from ent.ent_finder import get_class_attr, get_module_level_ent
from ent.entity import Entity, UnknownVar, Module, ReferencedAttribute, Location, UnresolvedAttribute, \
    ModuleAlias, UnknownModule, Function, Class, LambdaFunction
from interp.enttype import EntType, ConstructorType, ClassType, ModuleType, AnyType
from interp.env import EntEnv, ScopeEnv
# AValue stands for Abstract Value
from interp.manager_interp import PackageDB, ModuleDB
from ref.Ref import Ref

AbstractValue: TypeAlias = List[Tuple[Entity, EntType]]

MemberDistiller: TypeAlias = Callable[[int], AbstractValue]


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
            unknown_var = UnknownVar(name_expr.id, env.get_scope().get_location())
            self._current_db.add_ent(unknown_var)
            return [(unknown_var, EntType.get_bot())]

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
        for arg in call_expr.args:
            self.aval(arg, env)
        for key_word_arg in call_expr.keywords:
            self.aval(key_word_arg.value, env)
        return ret

    def aval_Lambda(self, lam_expr: ast.Lambda, env: EntEnv):
        from interp.checker import process_parameters
        in_class_env = isinstance(env.get_ctx(), Class)

        now_scope = env.get_scope().get_location()
        new_scope = now_scope.append(f"({lam_expr.lineno})")
        func_ent = LambdaFunction(new_scope.to_longname(), new_scope)

        # add function entity to dependency database
        self._current_db.add_ent(func_ent)
        # add reference of current contest to the function entity
        env.get_ctx().add_ref(Ref(RefKind.DefineKind, func_ent, lam_expr.lineno, lam_expr.col_offset))

        # add function entity to the current environment
        env.get_scope().add_continuous([(func_ent, EntType.get_bot())])
        # create the scope environment corresponding to the function
        body_env = ScopeEnv(ctx_ent=func_ent, location=new_scope)
        # add function entity to the scope environment corresponding to the function
        body_env.add_continuous([(func_ent, EntType.get_bot())])
        # add parameters to the scope environment
        process_parameters(lam_expr.args, body_env, self._current_db, env.get_class_ctx())
        hook_scope = env.get_scope(1) if in_class_env else env.get_scope()
        # type error due to member in ast node is, but due to any member in our structure is only readable,
        # this type error is safety
        hook_scope.add_hook([lam_expr.body], body_env)
        return [(func_ent, EntType.get_bot())]

    def aval_ListComp(self, list_comp: ast.ListComp, env: EntEnv) -> "AbstractValue":
        generators = list_comp.generators
        self.dummy_generator_exp(env, generators)
        self.aval(list_comp.elt, env)
        return [(Entity.get_anonymous_ent(), EntType.get_bot())]

    def aval_SetComp(self, set_comp: ast.SetComp, env: EntEnv) -> "AbstractValue":
        generators = set_comp.generators
        self.dummy_generator_exp(env, generators)
        self.aval(set_comp.elt, env)
        return [(Entity.get_anonymous_ent(), EntType.get_bot())]

    def aval_DictComp(self, dict_comp: ast.DictComp, env) -> "AbstractValue":
        generators = dict_comp.generators
        self.dummy_generator_exp(env, generators)
        self.aval(dict_comp.key, env)
        self.aval(dict_comp.value, env)
        return [(Entity.get_anonymous_ent(), EntType.get_bot())]

    def aval_GeneratorExp(self, gen_exp: ast.GeneratorExp, env: EntEnv) -> "AbstractValue":
        generators = gen_exp.generators
        self.dummy_generator_exp(env, generators)
        self.aval(gen_exp.elt, env)
        return [(Entity.get_anonymous_ent(), EntType.get_bot())]

    def dummy_generator_exp(self, env, generators: List[ast.comprehension]) -> None:
        from interp.assign_target import build_target, dummy_iter, unpack_semantic
        from interp.checker import InterpContext
        for comp in generators:
            target_lineno = comp.target.lineno
            target_col_offset = comp.target.col_offset
            iter_value = dummy_iter(self.aval(comp.iter, env))
            tar = build_target(comp.target)
            unpack_semantic(tar, iter_value,
                            InterpContext(env, self._package_db, self._current_db, (target_lineno, target_col_offset)))


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
            unknown_var = UnknownVar(name_expr.id, env.get_scope().get_location())
            self._current_db.add_ent(unknown_var)
            return [(unknown_var, EntType.get_bot())]

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
            unknown_var = UnknownVar(name_expr.id, env.get_scope().get_location())
            self._current_db.add_ent(unknown_var)
            return [(unknown_var, EntType.get_bot())]

    def aval_Attribute(self, attr_expr: ast.Attribute, env: EntEnv) -> List[Tuple[Entity, EntType]]:
        possible_receivers = self._avaler.aval(attr_expr.value, env)
        attribute = attr_expr.attr
        ret: List[Tuple[Entity, EntType]] = []
        extend_possible_attribute(attribute, possible_receivers, ret, self._package_db, self._current_db)
        return ret
