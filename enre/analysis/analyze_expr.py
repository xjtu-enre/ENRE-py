import ast
from typing import Sequence
from typing import Tuple, List
import time
from enre.ent.EntKind import RefKind
from enre.ent.ent_finder import get_class_attr, get_file_level_ent
from enre.ent.entity import Entity, UnknownVar, Module, ReferencedAttribute, Location, UnresolvedAttribute, \
    ModuleAlias, Class, LambdaFunction, Span, get_syntactic_span, get_anonymous_ent
from enre.analysis.value_info import ValueInfo, ConstructorType, InstanceType, ModuleType, AnyType, PackageType
from enre.analysis.env import EntEnv, ScopeEnv
# AValue stands for Abstract Value
from enre.analysis.analyze_manager import RootDB, ModuleDB, AnalyzeManager
from enre.ref.Ref import Ref
from enre.ent.entity import AbstractValue

AnonymousFakeName = "$"

class UseAvaler:

    def __init__(self, manager: AnalyzeManager, package_db: RootDB, current_db: ModuleDB):
        self.manager = manager
        self._package_db = package_db
        self._current_db = current_db

    def aval(self, expr: ast.expr, env: EntEnv) -> AbstractValue:
        """Visit a node."""
        method = 'aval_' + expr.__class__.__name__
        visitor = getattr(self, method, self.generic_aval)
        return visitor(expr, env)

    def generic_aval(self, expr: ast.expr, env: EntEnv) -> AbstractValue:
        """Called if no explicit visitor function exists for a node."""
        ret: ValueInfo = ValueInfo.get_any()
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

        return [(get_anonymous_ent(), ret)]

    def aval_Name(self, name_expr: ast.Name, env: EntEnv) -> AbstractValue:
        lookup_res = env[name_expr.id]
        ent_objs = lookup_res.found_entities
        ctx = env.get_ctx()
        for ent, ent_type in ent_objs:
            ctx.add_ref(Ref(RefKind.UseKind, ent, name_expr.lineno, name_expr.col_offset))
        if ent_objs != []:
            return ent_objs
        else:
            unknown_var = UnknownVar.get_unknown_var(name_expr.id)
            self._current_db.add_ent(unknown_var)
            ctx.add_ref(Ref(RefKind.UseKind, unknown_var, name_expr.lineno, name_expr.col_offset))
            return [(unknown_var, ValueInfo.get_any())]

    def aval_Attribute(self, attr_expr: ast.Attribute, env: EntEnv) -> AbstractValue:

        possible_ents = self.aval(attr_expr.value, env)
        attribute = attr_expr.attr
        ret: AbstractValue = []
        extend_possible_attribute(self.manager, attribute, possible_ents, ret, self._package_db, self._current_db)
        for ent, _ in ret:
            env.get_ctx().add_ref(Ref(RefKind.UseKind, ent, attr_expr.lineno, attr_expr.col_offset))
        return ret

    def aval_Call(self, call_expr: ast.Call, env: EntEnv) -> AbstractValue:
        call_avaler = CallAvaler(self.manager, self._package_db, self._current_db)
        possible_callers = call_avaler.aval(call_expr.func, env)
        ret: AbstractValue = []
        for caller, func_type in possible_callers:
            if isinstance(func_type, ConstructorType):
                ret.append((get_anonymous_ent(), func_type.to_class_type()))
            else:
                ret.append((get_anonymous_ent(), ValueInfo.get_any()))
            env.get_ctx().add_ref(Ref(RefKind.CallKind, caller, call_expr.lineno, call_expr.col_offset))
        for arg in call_expr.args:
            self.aval(arg, env)
        for key_word_arg in call_expr.keywords:
            self.aval(key_word_arg.value, env)
        return ret

    def aval_Lambda(self, lam_expr: ast.Lambda, env: EntEnv) -> AbstractValue:
        from enre.analysis.analyze_stmt import process_parameters
        in_class_env = isinstance(env.get_ctx(), Class)
        lam_span = get_syntactic_span(lam_expr)
        now_scope = env.get_scope().get_location()
        new_scope = now_scope.append(f"({lam_expr.lineno})", lam_span)
        func_ent = LambdaFunction(new_scope.to_longname(), new_scope)

        # add function entity to dependency database
        self._current_db.add_ent(func_ent)
        # add reference of current contest to the function entity
        env.get_ctx().add_ref(Ref(RefKind.DefineKind, func_ent, lam_expr.lineno, lam_expr.col_offset))

        # do not add lambda entity to the current environment
        # env.get_scope().add_continuous([(func_ent, EntType.get_bot())])
        # create the scope environment corresponding to the function
        body_env = ScopeEnv(ctx_ent=func_ent, location=new_scope)
        # do not add lambda entity to the scope environment corresponding to the function
        # body_env.add_continuous([(func_ent, EntType.get_bot())])
        # add parameters to the scope environment
        process_parameters(lam_expr.args, body_env, self._current_db, env.get_class_ctx())
        hook_scope = env.get_scope(1) if in_class_env else env.get_scope()
        # type error due to member in ast node is, but due to any member in our structure is only readable,
        # this type error is safety
        lam_body: List[ast.stmt] = [ast.Expr(lam_expr.body)]
        hook_scope.add_hook(lam_body, body_env)
        return [(func_ent, ValueInfo.get_any())]

    def aval_ListComp(self, list_comp: ast.ListComp, env: EntEnv) -> "AbstractValue":
        generators = list_comp.generators
        self.dummy_generator_exp(env, generators)
        self.aval(list_comp.elt, env)
        return [(get_anonymous_ent(), ValueInfo.get_any())]

    def aval_SetComp(self, set_comp: ast.SetComp, env: EntEnv) -> "AbstractValue":
        generators = set_comp.generators
        self.dummy_generator_exp(env, generators)
        self.aval(set_comp.elt, env)
        return [(get_anonymous_ent(), ValueInfo.get_any())]

    def aval_DictComp(self, dict_comp: ast.DictComp, env: EntEnv) -> "AbstractValue":
        generators = dict_comp.generators
        self.dummy_generator_exp(env, generators)
        self.aval(dict_comp.key, env)
        self.aval(dict_comp.value, env)
        return [(get_anonymous_ent(), ValueInfo.get_any())]

    def aval_GeneratorExp(self, gen_exp: ast.GeneratorExp, env: EntEnv) -> "AbstractValue":
        generators = gen_exp.generators
        self.dummy_generator_exp(env, generators)
        self.aval(gen_exp.elt, env)
        return [(get_anonymous_ent(), ValueInfo.get_any())]

    def dummy_generator_exp(self, env: EntEnv, generators: List[ast.comprehension]) -> None:
        from enre.analysis.assign_target import build_target, dummy_iter, unpack_semantic
        from enre.analysis.analyze_stmt import AnalyzeContext
        for comp in generators:
            target_lineno = comp.target.lineno
            target_col_offset = comp.target.col_offset
            iter_value = dummy_iter(self.aval(comp.iter, env))
            tar = build_target(comp.target)
            unpack_semantic(tar, iter_value,
                            AnalyzeContext(env,
                                           self.manager,
                                           self._package_db,
                                           self._current_db,
                                           (target_lineno, target_col_offset),
                                           True))
            for cond_expr in comp.ifs:
                self.aval(cond_expr, env)


def extend_possible_attribute(manager: AnalyzeManager, attribute: str, possible_ents: AbstractValue, ret: AbstractValue, package_db: RootDB,
                              current_db: ModuleDB) -> None:
    for ent, ent_type in possible_ents:
        if isinstance(ent_type, InstanceType):
            class_attrs = ent_type.lookup_attr(attribute)
            process_known_attr(class_attrs, attribute, ret, current_db, ent_type.class_ent, ent_type)
        elif isinstance(ent_type, ConstructorType):
            class_attrs = ent_type.lookup_attr(attribute)
            process_known_attr(class_attrs, attribute, ret, current_db, ent_type.class_ent, ent_type)
        elif isinstance(ent_type, ModuleType):
            if isinstance(ent, Module):
                manager.strict_analyze_module(ent)
            module_level_ents = ent_type.namespace[attribute]
            process_known_attr(module_level_ents, attribute, ret, current_db, ent, ent_type)
        elif isinstance(ent_type, PackageType):
            package_level_ents = ent_type.namespace[attribute]
            process_known_attr(package_level_ents, attribute, ret, current_db, ent, ent_type)
        elif isinstance(ent_type, AnyType):
            location = Location.global_name(attribute)
            referenced_attr = ReferencedAttribute(location.to_longname(), location)
            current_db.add_ent(referenced_attr)
            ret.append((referenced_attr, ValueInfo.get_any()))
        else:
            raise NotImplementedError("attribute receiver entity matching not implemented")


def process_known_attr(attr_ents: Sequence[Entity], attribute: str, ret: AbstractValue, dep_db: ModuleDB,
                       container: Entity, receiver_type: ValueInfo) -> None:
    if attr_ents != []:
        # when get attribute of another entity, presume

        ret.extend([(ent_x, ent_x.direct_type()) for ent_x in attr_ents])
    else:
        # unresolved shouldn't be global
        location = container.location.append(attribute, Span.get_nil())
        unresolved = UnresolvedAttribute(location.to_longname(), location, receiver_type)
        dep_db.add_ent(unresolved)
        # dep_db.add_ref(container, Ref(RefKind.DefineKind, unresolved, 0, 0))
        # till now can't add `Define` reference to unresolved reference. If we do so, we could have duplicate  `Define`
        # relation in the class entity, while in a self set context.
        ret.append((unresolved, ValueInfo.get_any()))


class SetAvaler:
    def __init__(self, manager: AnalyzeManager, package_db: RootDB, current_db: ModuleDB):
        self.manager = manager
        self._package_db = package_db
        self._current_db = current_db
        self._avaler = UseAvaler(manager, package_db, current_db)

    def aval(self, expr: ast.expr, env: EntEnv) -> AbstractValue:
        """Visit a node."""
        method = 'aval_' + expr.__class__.__name__
        visitor = getattr(self, method, self._avaler.aval)
        return visitor(expr, env)

    def aval_Name(self, name_expr: ast.Name, env: EntEnv) -> AbstractValue:
        # while in a set context, only entity in the current scope visible
        lookup_res = env.get_scope()[name_expr.id]
        ent_objs = lookup_res.found_entities
        if ent_objs != []:
            return ent_objs
        else:
            unknown_var = UnknownVar.get_unknown_var(name_expr.id)
            self._current_db.add_ent(unknown_var)
            return [(unknown_var, ValueInfo.get_any())]

    def aval_Attribute(self, attr_expr: ast.Attribute, env: EntEnv) -> AbstractValue:
        possible_receivers = self._avaler.aval(attr_expr.value, env)
        attribute = attr_expr.attr
        ret: AbstractValue = []
        extend_possible_attribute(self.manager, attribute, possible_receivers, ret, self._package_db, self._current_db)
        return ret


class CallAvaler:
    def __init__(self, manager: AnalyzeManager, package_db: RootDB, current_db: ModuleDB):
        self.manager = manager
        self._package_db = package_db
        self._current_db = current_db
        self._avaler = UseAvaler(manager, package_db, current_db)

    def aval(self, expr: ast.expr, env: EntEnv) -> AbstractValue:
        """Visit a node."""
        method = 'aval_' + expr.__class__.__name__
        visitor = getattr(self, method, self._avaler.aval)
        return visitor(expr, env)

    def aval_Name(self, name_expr: ast.Name, env: EntEnv) -> AbstractValue:
        lookup_res = env[name_expr.id]
        ent_objs = lookup_res.found_entities
        if ent_objs:
            return ent_objs
        else:
            unknown_var = UnknownVar.get_unknown_var(name_expr.id)
            self._current_db.add_ent(unknown_var)
            return [(unknown_var, ValueInfo.get_any())]

    def aval_Attribute(self, attr_expr: ast.Attribute, env: EntEnv) -> AbstractValue:
        possible_receivers = self._avaler.aval(attr_expr.value, env)
        attribute = attr_expr.attr
        ret: AbstractValue = []
        extend_possible_attribute(self.manager, attribute, possible_receivers, ret, self._package_db, self._current_db)
        return ret
