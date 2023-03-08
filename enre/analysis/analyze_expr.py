import ast
import itertools
from abc import ABC
from dataclasses import dataclass
from typing import Sequence, Optional, Iterable
from typing import Tuple, List

from enre.analysis.analyze_manager import RootDB, ModuleDB, AnalyzeManager
# AValue stands for Abstract Value
from enre.analysis.assign_target import dummy_unpack
from enre.analysis.env import EntEnv, ScopeEnv
from enre.analysis.value_info import ValueInfo, ConstructorType, InstanceType, ModuleType, AnyType, PackageType
from enre.cfg.module_tree import SummaryBuilder, StoreAble, FuncConst, StoreAbles, get_named_store_able, \
    ModuleSummary, Constant, IndexableKind, IndexableInfo, ConstantKind
from enre.ent.EntKind import RefKind
from enre.ent.entity import AbstractValue
from enre.ent.entity import Entity, UnknownVar, Module, ReferencedAttribute, Location, UnresolvedAttribute, \
    ModuleAlias, Class, LambdaFunction, Span, get_syntactic_span, get_anonymous_ent, NewlyCreated, SetContextValue, \
    Function
from enre.ref.Ref import Ref

AnonymousFakeName = "$"


class ExpressionContext(ABC):
    ...


@dataclass
class UseContext(ExpressionContext):
    ...


@dataclass
class SetContext(ExpressionContext):
    is_define: bool
    rhs_value: AbstractValue
    rhs_store_ables: StoreAbles


@dataclass
class CallContext(ExpressionContext):
    ...


class ExprAnalyzer:

    def __init__(self, manager: AnalyzeManager, package_db: RootDB, current_db: ModuleDB,
                 typing_entities: Optional[Iterable[Entity]],
                 exp_ctx: ExpressionContext, builder: SummaryBuilder, env: EntEnv):
        self.manager = manager
        self._package_db = package_db
        self._current_db = current_db
        self._exp_ctx = exp_ctx
        self._builder: SummaryBuilder = builder
        self._env = env
        self._new_builders: List[ModuleSummary] = []
        self._typing_entities = typing_entities

    def aval(self, expr: ast.expr) -> Tuple[StoreAbles, AbstractValue]:
        """Visit a node."""
        method = 'aval_' + expr.__class__.__name__
        visitor = getattr(self, method, self.generic_aval)
        stores, objs = visitor(expr)
        self.build_move_by_context(stores)
        return stores, objs

    def generic_aval(self, expr: ast.expr) -> Tuple[StoreAbles, AbstractValue]:
        """Called if no explicit visitor function exists for a node."""
        ret: ValueInfo = ValueInfo.get_any()
        all_store_ables: List[StoreAble] = []
        use_avaler = ExprAnalyzer(self.manager, self._package_db, self._current_db, self._typing_entities, UseContext(),
                                  self._builder, self._env)
        for field, value in ast.iter_fields(expr):
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, ast.expr):

                        store_ables, avalue = use_avaler.aval(item)
                        all_store_ables.extend(store_ables)
                        for _, ent_type in avalue:
                            ret = ret.join(ent_type)
            elif isinstance(value, ast.expr):
                store_ables, avalue = use_avaler.aval(value)
                all_store_ables.extend(store_ables)
                for _, ent_type in avalue:
                    ret = ret.join(ent_type)

        return all_store_ables, [(get_anonymous_ent(), ret)]

    def aval_Name(self, name_expr: ast.Name) -> Tuple[StoreAbles, AbstractValue]:
        from enre.analysis.analyze_stmt import AnalyzeContext
        from enre.analysis.assign_target import abstract_assign

        lookup_res = self._env.get(name_expr.id)
        ent_objs = lookup_res.found_entities
        ctx = self._env.get_ctx()
        for ent, ent_type in ent_objs:
            ctx.add_ref(self.create_ref_by_ctx(ent, name_expr.lineno, name_expr.col_offset, self._typing_entities,
                                               self._exp_ctx, name_expr))

        if not isinstance(self._exp_ctx, SetContext):
            if ent_objs:
                store_ables: List[StoreAble] = []
                for ent, _ in ent_objs:
                    s = get_named_store_able(self._env.get_ctx(), ent, name_expr)
                    if s:
                        store_ables.append(s)
                return store_ables, ent_objs
            else:
                unknown_var = UnknownVar.get_unknown_var(name_expr.id)
                self._current_db.add_ent(unknown_var)
                ctx.add_ref(
                    self.create_ref_by_ctx(unknown_var, name_expr.lineno, name_expr.col_offset, self._typing_entities,
                                           self._exp_ctx, name_expr))
                return [], [(unknown_var, ValueInfo.get_any())]
        else:
            lhs_objs: SetContextValue = []
            if ent_objs:
                lhs_objs.extend(ent_objs)
            else:
                lhs_objs.extend([NewlyCreated(get_syntactic_span(name_expr), UnknownVar(name_expr.id))])
            lhs_store_ables = abstract_assign(lhs_objs, self._exp_ctx.rhs_value, name_expr,
                                              self._exp_ctx.rhs_store_ables,
                                              self._builder,
                                              AnalyzeContext(self._env, self.manager, self._package_db,
                                                             self._current_db,
                                                             (name_expr.lineno, name_expr.col_offset), False))
            return lhs_store_ables, ent_objs

    def aval_Attribute(self, attr_expr: ast.Attribute) -> Tuple[StoreAbles, AbstractValue]:
        use_avaler = ExprAnalyzer(self.manager, self._package_db, self._current_db,
                                  self._typing_entities, UseContext(), self._builder, self._env)
        possible_store_ables, possible_ents = use_avaler.aval(attr_expr.value)
        attribute = attr_expr.attr
        ret: AbstractValue = []
        extend_known_possible_attribute(self.manager, attribute, possible_ents, ret, self._package_db, self._current_db)
        for ent, _ in ret:
            self._env.get_ctx().add_ref(
                self.create_ref_by_ctx(ent, attr_expr.lineno, attr_expr.col_offset,
                                       self._typing_entities, self._exp_ctx, attr_expr))
        field_accesses = self._builder.load_field(possible_store_ables, attribute, self._exp_ctx, attr_expr)
        return field_accesses, ret

    def aval_Call(self, call_expr: ast.Call) -> Tuple[StoreAbles, AbstractValue]:
        call_avaler = ExprAnalyzer(self.manager, self._package_db, self._current_db, self._typing_entities,
                                   CallContext(), self._builder, self._env)
        callee_stores, possible_callees = call_avaler.aval(call_expr.func)
        ret: AbstractValue = []
        for callee, func_type in possible_callees:
            if isinstance(func_type, ConstructorType):
                ret.append((get_anonymous_ent(), func_type.to_class_type()))
            else:
                ret.append((get_anonymous_ent(), ValueInfo.get_any()))
            # self._env.get_ctx().add_ref(
            #     create_ref_by_ctx(callee, call_expr.lineno, call_expr.col_offset, CallContext(), call_expr))
            # we don't need create call dependency here, because we will create dependencies by context in the
        args = []
        for arg in call_expr.args:
            use_avaler = self.get_use_avaler()
            a, _ = use_avaler.aval(arg)
            args.append(a)
        kwargs = []
        for key_word_arg in call_expr.keywords:
            key = key_word_arg.arg
            a, _ = self.aval(key_word_arg.value)
            if key is not None:
                kwargs.append((key, a))
        ret_stores = self._builder.add_invoke(callee_stores, args, kwargs, call_expr)
        return ret_stores, ret

    def aval_Str(self, str_constant: ast.Str) -> Tuple[StoreAbles, AbstractValue]:
        str_cls = self.get_class_from_builtins(ConstantKind.string.value)
        s = self._builder.add_move_temp(Constant(str_constant, str_cls), str_constant)
        return [s], []

    def aval_Constant(self, constant: ast.Constant) -> Tuple[StoreAbles, AbstractValue]:
        constant_cls: Optional[Class] = None
        if isinstance(constant.value, str):
            constant_cls = self.get_class_from_builtins(ConstantKind.string.value)
        s = self._builder.add_move_temp(Constant(constant, constant_cls), constant)
        return [s], []

    def aval_Lambda(self, lam_expr: ast.Lambda) -> Tuple[StoreAbles, AbstractValue]:
        from enre.analysis.analyze_stmt import process_parameters
        in_class_env = isinstance(self._env.get_ctx(), Class)
        lam_span = get_syntactic_span(lam_expr)
        now_scope = self._env.get_scope().get_location()
        new_scope = now_scope.append(f"({lam_expr.lineno})", lam_span, None)
        func_ent = LambdaFunction(new_scope.to_longname(), new_scope)

        # add function entity to dependency database
        self._current_db.add_ent(func_ent)
        # add reference of current context to the function entity
        self._env.get_ctx().add_ref(
            self.create_ref_by_ctx(func_ent, lam_expr.lineno, lam_expr.col_offset, self._typing_entities, self._exp_ctx,
                                   lam_expr))

        # do not add lambda entity to the current environment
        # env.get_scope().add_continuous([(func_ent, EntType.get_bot())])
        # create the scope environment corresponding to the function
        func_summary = self.manager.create_function_summary(func_ent)
        self._new_builders.append(func_summary)
        body_env = ScopeEnv(ctx_ent=func_ent, location=new_scope, builder=SummaryBuilder(func_summary))
        # do not add lambda entity to the scope environment corresponding to the function
        # body_env.add_continuous([(func_ent, EntType.get_bot())])
        # add parameters to the scope environment
        process_parameters(lam_expr.args, body_env, self._env, self.manager, self._package_db, self._current_db,
                           func_ent, func_summary, self._env.get_class_ctx())
        hook_scope = self._env.get_scope(1) if in_class_env else self._env.get_scope()
        # type error due to member in ast node is, but due to any member in our structure is only readable,
        # this type error is safety
        lam_body: List[ast.stmt] = [ast.Expr(lam_expr.body)]
        hook_scope.add_hook(lam_body, body_env)
        func_store_able = FuncConst(func_ent)
        return [func_store_able], [(func_ent, ValueInfo.get_any())]

    def aval_ListComp(self, list_comp: ast.ListComp) -> Tuple[StoreAbles, AbstractValue]:
        generators = list_comp.generators
        self.dummy_generator_exp(generators)
        self.aval(list_comp.elt)
        return [], [(get_anonymous_ent(), ValueInfo.get_any())]

    def aval_SetComp(self, set_comp: ast.SetComp) -> Tuple[StoreAbles, AbstractValue]:
        generators = set_comp.generators
        self.dummy_generator_exp(generators)
        self.aval(set_comp.elt)
        return [], [(get_anonymous_ent(), ValueInfo.get_any())]

    def aval_DictComp(self, dict_comp: ast.DictComp) -> Tuple[StoreAbles, AbstractValue]:
        generators = dict_comp.generators
        self.dummy_generator_exp(generators)
        self.aval(dict_comp.key)
        self.aval(dict_comp.value)
        return [], [(get_anonymous_ent(), ValueInfo.get_any())]

    def aval_GeneratorExp(self, gen_exp: ast.GeneratorExp) -> Tuple[StoreAbles, AbstractValue]:
        generators = gen_exp.generators
        self.dummy_generator_exp(generators)
        self.aval(gen_exp.elt)
        return [], [(get_anonymous_ent(), ValueInfo.get_any())]

    def aval_BinOp(self, bin_exp: ast.BinOp) -> Tuple[StoreAbles, AbstractValue]:
        use_avaler = ExprAnalyzer(self.manager, self._package_db, self._current_db, None, UseContext(), self._builder,
                                  self._env)
        left_store_ables, _ = use_avaler.aval(bin_exp.left)
        right_store_ables, _ = use_avaler.aval(bin_exp.right)
        return [], [(get_anonymous_ent(), ValueInfo.get_any())]

    def dummy_generator_exp(self, generators: List[ast.comprehension]) -> None:
        from enre.analysis.assign_target import build_target, dummy_iter, unpack_semantic, dummy_iter_store
        from enre.analysis.analyze_stmt import AnalyzeContext

        for comp in generators:
            target_lineno = comp.target.lineno
            target_col_offset = comp.target.col_offset
            store, iterable = self.aval(comp.iter)
            iter_value = dummy_iter(iterable)
            iter_store = dummy_iter_store(store, self._builder, comp.iter)
            unpack_semantic(comp.target, iter_value, iter_store, self._builder,
                            AnalyzeContext(self._env,
                                           self.manager,
                                           self._package_db,
                                           self._current_db,
                                           (target_lineno, target_col_offset),
                                           True))
            for cond_expr in comp.ifs:
                self.aval(cond_expr)

    def build_move_by_context(self, stores: StoreAbles) -> None:
        match self._exp_ctx:
            case SetContext() as ctx:
                for lhs, rhs in itertools.product(stores, ctx.rhs_store_ables):
                    self._builder.add_move(lhs, rhs)

    def create_ref_by_ctx(self, target_ent: Entity, lineno: int, col_offset: int,
                          typing_entities: Optional[Iterable[Entity]],
                          ctx: ExpressionContext, expr: ast.expr) -> Ref:
        """
        Create a reference to the given entity by the expression's context.
        """
        ref_kind: RefKind
        match ctx:
            case UseContext():
                ref_kind = RefKind.UseKind
            case CallContext():
                ref_kind = RefKind.CallKind
            case SetContext():
                ref_kind = RefKind.SetKind
            case _:
                assert False, "unexpected context"
        if typing_entities is not None:
            for ent in typing_entities:
                ent.add_ref(Ref(RefKind.Annotate, target_ent, lineno, col_offset, True, expr))
        return Ref(ref_kind, target_ent, lineno, col_offset, typing_entities is not None, expr)

    def aval_Tuple(self, tuple_exp: ast.Tuple) -> Tuple[StoreAbles, AbstractValue]:
        return self.aval_iterable_expr(tuple_exp.elts, IndexableKind.tpl, tuple_exp)

    def aval_List(self, list_exp: ast.List) -> Tuple[StoreAbles, AbstractValue]:
        return self.aval_iterable_expr(list_exp.elts, IndexableKind.lst, list_exp)

    def aval_Dict(self, dict_exp: ast.Dict) -> Tuple[StoreAbles, AbstractValue]:
        return self.aval_iterable_expr(dict_exp.values, IndexableKind.dct, dict_exp)

    def aval_iterable_expr(self,
                           iterable_elts: Iterable[ast.expr],
                           kind: IndexableKind,
                           expr: ast.expr) -> Tuple[StoreAbles, AbstractValue]:
        class_in_builtins: Optional[Class] = self.get_class_from_builtins(kind.value)
        kind_info = IndexableInfo(kind, class_in_builtins)
        iterable_store = self._builder.create_list(kind_info, expr)
        stores: List[StoreAble] = []
        abstract_value: AbstractValue = []
        context = self._exp_ctx
        for index, elt in enumerate(iterable_elts):
            avaler: ExprAnalyzer
            if isinstance(context, SetContext):
                rhs_store_ables = context.rhs_store_ables
                index_accesses = self._builder.load_index_rvalues(rhs_store_ables, elt)
                rhs_abstract_value = context.rhs_value
                avaler = ExprAnalyzer(self.manager, self._package_db, self._current_db, self._typing_entities,
                                      SetContext(context.is_define, dummy_unpack(rhs_abstract_value)(index),
                                                 index_accesses), self._builder,
                                      self._env)
                # todo: add unpack operation to summary
            else:
                avaler = ExprAnalyzer(self.manager, self._package_db, self._current_db, self._typing_entities, context,
                                      self._builder, self._env)
            sub_stores, ent_objs = avaler.aval(elt)
            stores.extend(sub_stores)
            abstract_value.extend(ent_objs)
        for store in stores:
            index_access = self._builder.load_index_lvalue(iterable_store, expr)
            self._builder.add_move(index_access, store)
        return [iterable_store], [(get_anonymous_ent(), ValueInfo.get_any())]

    def aval_Subscript(self, subscript: ast.Subscript) -> Tuple[StoreAbles, AbstractValue]:
        _, _ = self.aval(subscript.slice)
        base_stores, abstract_value = self.aval(subscript.value)
        if isinstance(subscript.slice, ast.Slice):
            index_accesses = base_stores
        else:
            index_accesses = self._builder.load_index(base_stores, self._exp_ctx, subscript)
        return index_accesses, abstract_value

    def get_use_avaler(self) -> "ExprAnalyzer":
        return ExprAnalyzer(self.manager, self._package_db, self._current_db, None,
                            UseContext(), self._builder, self._env)

    def get_from_builtins(self, name: str) -> "Optional[AbstractValue]":
        return self.manager.get_from_builtins(name)

    def get_class_from_builtins(self, name: str) -> "Optional[Class]":
        if entities := self.get_from_builtins(name):
            first_result = entities[0][0]
            if isinstance(first_result, Class):
                return first_result
        return None


def extend_known_possible_attribute(manager: AnalyzeManager,
                                    attribute: str,
                                    possible_ents: AbstractValue,
                                    ret: AbstractValue,
                                    package_db: RootDB,
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


def extend_known_or_new_possible_attribute(manager: AnalyzeManager,
                                           attribute: str,
                                           possible_ents: AbstractValue,
                                           ret: SetContextValue,
                                           package_db: RootDB,
                                           current_db: ModuleDB) -> None:
    for ent, ent_type in possible_ents:
        if isinstance(ent_type, InstanceType):
            class_attrs = ent_type.lookup_attr(attribute)
            process_known_or_newly_created_attr(class_attrs, attribute, ret, current_db, ent_type.class_ent, ent_type)
        elif isinstance(ent_type, ConstructorType):
            class_attrs = ent_type.lookup_attr(attribute)
            process_known_or_newly_created_attr(class_attrs, attribute, ret, current_db, ent_type.class_ent, ent_type)
        elif isinstance(ent_type, ModuleType):
            if isinstance(ent, Module):
                manager.strict_analyze_module(ent)
            module_level_ents = ent_type.namespace[attribute]
            process_known_or_newly_created_attr(module_level_ents, attribute, ret, current_db, ent, ent_type)
        elif isinstance(ent_type, PackageType):
            package_level_ents = ent_type.namespace[attribute]
            process_known_or_newly_created_attr(package_level_ents, attribute, ret, current_db, ent, ent_type)
        elif isinstance(ent_type, AnyType):
            location = Location.global_name(attribute)
            referenced_attr = ReferencedAttribute(location.to_longname(), location)
            current_db.add_ent(referenced_attr)
            ret.append((referenced_attr, ValueInfo.get_any()))
        else:
            raise NotImplementedError("attribute receiver entity matching not implemented")


def process_known_attr(attr_ents: Sequence[Entity], attribute: str, ret: AbstractValue, dep_db: ModuleDB,
                       container: Entity, receiver_type: ValueInfo) -> None:
    if attr_ents:
        # when get attribute of another entity, presume

        ret.extend([(ent_x, ent_x.direct_type()) for ent_x in attr_ents])
    else:
        # unresolved shouldn't be global
        location = container.location.append(attribute, Span.get_nil(), None)
        unresolved = UnresolvedAttribute(location.to_longname(), location, receiver_type)
        dep_db.add_ent(unresolved)
        # dep_db.add_ref(container, Ref(RefKind.DefineKind, unresolved, 0, 0))
        # till now can't add `Define` reference to unresolved reference. If we do so, we could have duplicate  `Define`
        # relation in the class entity, while in a self set context.
        ret.append((unresolved, ValueInfo.get_any()))


def process_known_or_newly_created_attr(attr_ents: Sequence[Entity],
                                        attribute: str,
                                        ret: SetContextValue,
                                        dep_db: ModuleDB,
                                        container: Entity,
                                        receiver_type: ValueInfo) -> None:
    if attr_ents:
        # when get attribute of another entity, presume

        ret.extend([(ent_x, ent_x.direct_type()) for ent_x in attr_ents])
    else:
        # unresolved shouldn't be global
        location = container.location.append(attribute, Span.get_nil(), None)
        unresolved = UnresolvedAttribute(location.to_longname(), location, receiver_type)
        # till now can't add `Define` reference to unresolved reference. If we do so, we could have duplicate  `Define`
        # relation in the class entity, while in a self set context.
        ret.append(NewlyCreated(Span.get_nil(), unresolved))


def filter_not_setable_entities(ent_objs: AbstractValue) -> AbstractValue:
    ret = []
    for e, v in ent_objs:
        if not isinstance(e, (Class, Function, Module, ModuleAlias)):
            ret.append((e, v))
    return ret
