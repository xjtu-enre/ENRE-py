import ast
import itertools
from abc import ABC
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence, Optional, Iterable
from typing import Tuple, List, TYPE_CHECKING

from enre.analysis.analyze_typeshed import NameInfoVisitor
from enre.analysis.analyze_manager import RootDB, ModuleDB, AnalyzeManager
from enre.analysis.assign_target import dummy_unpack
from enre.analysis.env import EntEnv, ScopeEnv

if TYPE_CHECKING:
    from enre.analysis.env import Bindings
from enre.analysis.value_info import ValueInfo, ConstructorType, InstanceType, ModuleType, AnyType, PackageType, \
    FunctionType, MethodType, UnionType, DictType, TupleType, CallType, ListType, \
    UnknownVarType, ReferencedAttrType
from enre.cfg.module_tree import SummaryBuilder, StoreAble, FuncConst, StoreAbles, get_named_store_able, \
    ModuleSummary
from enre.ent.EntKind import RefKind
from enre.ent.entity import AbstractValue, get_syntactic_head, ClassAttribute
from enre.ent.entity import Entity, UnknownVar, Module, ReferencedAttribute, Location, UnresolvedAttribute, \
    ModuleAlias, Class, LambdaFunction, Span, get_syntactic_span, get_anonymous_ent, NewlyCreated, SetContextValue, \
    Function
from enre.ref.Ref import Ref

from enre.util.logger import Logging

AnonymousFakeName = "$"

log = Logging().getLogger(__name__)


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


@dataclass
class InvokeContext:
    possible_callees: AbstractValue
    args_info: dict
    manager: AnalyzeManager
    current_db: ModuleDB
    call_expr: Optional[ast.Call]


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
        self._current_db.set_env(env)

    def aval(self, expr: ast.expr) -> Tuple[StoreAbles, AbstractValue]:
        """Visit a node."""
        method = 'aval_' + expr.__class__.__name__
        visitor = getattr(self, method, self.generic_aval)
        stores, objs = visitor(expr)
        self.build_move_by_context(stores)
        resolve_overlays(self.manager, objs)
        return stores, objs

    def generic_aval(self, expr: ast.expr) -> Tuple[StoreAbles, AbstractValue]:
        """Called if no explicit visitor function exists for a node."""
        ret: ValueInfo = ValueInfo.get_any()
        all_store_ables: List[StoreAble] = []
        # all_abstract_values: AbstractValue = []
        use_avaler = ExprAnalyzer(self.manager, self._package_db, self._current_db, self._typing_entities, UseContext(),
                                  self._builder, self._env)
        if not expr:
            return all_store_ables, [(get_anonymous_ent(), ret)]
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

        lookup_res = self._env[name_expr.id]
        ent_objs = lookup_res.found_entities
        ctx = self._env.get_ctx()

        for ent, ent_type in ent_objs:
            ctx.add_ref(self.create_ref_by_ctx(ent, name_expr.lineno, name_expr.col_offset, self._typing_entities,
                                               self._exp_ctx, name_expr))

        if not isinstance(self._exp_ctx, SetContext):
            if ent_objs:
                store_ables: List[StoreAble] = []
                for ent, _ in ent_objs:
                    s = get_named_store_able(ent, name_expr)
                    if s:
                        store_ables.append(s)
                return store_ables, ent_objs
            else:
                # No builtins cache, create builtins cache.
                # var = NameInfoVisitor.is_builtins_continue(name_expr.id, self.manager, self._current_db)
                store_ables: List[StoreAble] = []
                unknown_var_name = name_expr.id

                # should add this unknown var to module db
                location = Location.global_name(unknown_var_name)
                unknown_var = UnknownVar(unknown_var_name, location)
                self._current_db.add_ent(unknown_var)
                new_binding: "Bindings" = [(unknown_var.longname.name, [(unknown_var, unknown_var.direct_type())])]
                self._current_db.top_scope.add_continuous_to_bottom(new_binding)
                # global_unknown_vars = self.manager.root_db.global_db.unknown_vars
                # if unknown_var_name in global_unknown_vars:
                #     unknown_var = global_unknown_vars[unknown_var_name]
                # else:
                #     location = Location.global_name(unknown_var_name)
                #     unknown_var = UnknownVar(unknown_var_name, location)
                #     global_unknown_vars[unknown_var_name] = unknown_var
                #     self.manager.root_db.global_db.add_ent(unknown_var)

                ent_objs = [(unknown_var, unknown_var.direct_type())]

                # lookup_res = self.manager.builtins_env[name_expr.id]
                # ent_objs = lookup_res.found_entities
                # if ent_objs:
                #     for ent, _ in ent_objs:
                #         s = get_named_store_able(ent, name_expr)
                #         if s:
                #             store_ables.append(s)

                ctx.add_ref(
                    self.create_ref_by_ctx(unknown_var, name_expr.lineno, name_expr.col_offset, self._typing_entities,
                                           self._exp_ctx, name_expr))
                return store_ables, ent_objs
        else:
            lhs_objs: SetContextValue = []
            if ent_objs:
                lhs_objs.extend(ent_objs)
            else:
                lhs_objs.extend([NewlyCreated(get_syntactic_span(name_expr), UnknownVar(name_expr.id))])
            lhs_store_ables, ents = abstract_assign(lhs_objs, self._exp_ctx.rhs_value, name_expr,
                                                    self._exp_ctx.rhs_store_ables,
                                                    self._builder,
                                                    AnalyzeContext(self._env, self.manager, self._package_db,
                                                                   self._current_db,
                                                                   (name_expr.lineno, name_expr.col_offset), False))
            ent_objs = ents
            return lhs_store_ables, ent_objs

    def aval_Attribute(self, attr_expr: ast.Attribute) -> Tuple[StoreAbles, AbstractValue]:
        use_avaler = ExprAnalyzer(self.manager, self._package_db, self._current_db,
                                  self._typing_entities, UseContext(), self._builder, self._env)
        possible_store_ables, possible_ents = use_avaler.aval(attr_expr.value)
        attribute = attr_expr.attr
        ret: AbstractValue = []

        extend_known_possible_attribute(self.manager, attribute, possible_ents, ret, self._exp_ctx, self._current_db,
                                        attr_expr)
        for ent, _ in ret:
            self._env.get_ctx().add_ref(
                self.create_ref_by_ctx(ent, attr_expr.lineno, attr_expr.col_offset,
                                       self._typing_entities, self._exp_ctx, attr_expr))
        field_accesses = self._builder.load_field(possible_store_ables, attribute, self._exp_ctx, attr_expr)
        return field_accesses, ret

    def aval_Call(self, call_expr: ast.Call) -> Tuple[StoreAbles, AbstractValue]:
        call_avaler = ExprAnalyzer(self.manager, self._package_db, self._current_db, self._typing_entities,
                                   CallContext(), self._builder, self._env)
        caller_stores, possible_callees = call_avaler.aval(call_expr.func)
        ret: AbstractValue = []
        args_info = []
        parameters = dict()
        args = []
        kwargs = dict()

        for arg in call_expr.args:
            a, _ = self.aval(arg)
            if isinstance(arg, ast.Starred):  # unpack tuple to elts
                if isinstance(arg.value, ast.Tuple):
                    elts = arg.value.elts
                    if elts:
                        call_expr.args.extend(elts)
                else:
                    call_expr.args.append(arg.value)
            else:
                args_info.append(a)
                args.append(_)
        for key_word_arg in call_expr.keywords:
            stores, values = self.aval(key_word_arg.value)
            if isinstance(key_word_arg.value, ast.Dict):  # unpack tuple to elts
                """likes **{"name": "Test", "age": 24} 
                unpack it to 'name' = 'Test', 'age' = 24
                """
                @dataclass
                class FakeKwArg:
                    arg: ast.AST
                    value: ast.AST

                keys = key_word_arg.value.keys
                values = key_word_arg.value.values
                if keys:
                    for i in range(len(keys)):
                        key = None
                        if isinstance(keys[i], ast.Name):
                            key = keys[i].id
                        elif isinstance(keys[i], ast.Constant):
                            key = keys[i].value
                        if key:
                            value = values[i]
                            farg = FakeKwArg(key, value)
                            call_expr.keywords.append(farg)
            else:
                kwargs[key_word_arg.arg] = values
        parameters["args"] = args
        parameters["kwargs"] = kwargs
        ret_stores = self._builder.add_invoke(caller_stores, args_info, call_expr)
        """visit function body in current parameter type
        """
        invoke_ctx = InvokeContext(possible_callees, parameters, self.manager, self._current_db, call_expr)
        ret = invoke(invoke_ctx)

        return ret_stores, ret

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
                           func_summary, self._env.get_class_ctx())

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
            iter_store = dummy_iter_store(store, self._builder, comp)
            tar = build_target(comp.target)
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
        stores: List[StoreAble] = []
        abstract_value: AbstractValue = []
        value_infos = []
        context = self._exp_ctx

        for index, elt in enumerate(tuple_exp.elts):
            avaler: ExprAnalyzer
            if isinstance(context, SetContext):
                rhs_store_ables = context.rhs_store_ables
                rhs_abstract_value = context.rhs_value
                avaler = ExprAnalyzer(self.manager, self._package_db, self._current_db, self._typing_entities,
                                      SetContext(False, dummy_unpack(rhs_abstract_value)(index), []), self._builder,
                                      self._env)
                # todo: add unpack operation to summary
            else:
                avaler = ExprAnalyzer(self.manager, self._package_db, self._current_db, self._typing_entities, context,
                                      self._builder, self._env)
            sub_stores, ent_objs = avaler.aval(elt)
            stores.extend(sub_stores)
            abstract_value.extend(ent_objs)
            if ent_objs:
                value_infos.append(ent_objs[0][1])
            else:
                value_infos.append(ValueInfo.get_any())
        # NameInfoVisitor.is_builtins_continue("tuple", self.manager, self._current_db)
        # lookup_res = self.manager.builtins_env["tuple"]
        # ent_objs = lookup_res.found_entities

        tuple_value = TupleType(ValueInfo.get_any())
        # tuple_value = TupleType(ent_objs[0][1])
        tuple_value.add(value_infos)
        return [], [(get_anonymous_ent(), tuple_value)]

    def aval_Subscript(self, subscript: ast.Subscript) -> Tuple[StoreAbles, AbstractValue]:
        # TODO: subscript res

        # t.paras
        subscript_paras = set()
        if isinstance(subscript.slice, ast.Subscript):
            _, elt_value = self.aval(subscript.slice)
            subscript_paras.add(elt_value[0][1])
        elif isinstance(subscript.slice, ast.Tuple):
            for elt in subscript.slice.elts:
                _, elt_value = self.aval(elt)
                subscript_paras.add(elt_value[0][1])
        elif isinstance(subscript.slice, ast.Name):
            _, elt_value = self.aval(subscript.slice)
            subscript_paras.add(elt_value[0][1])
        elif isinstance(subscript.slice, ast.Constant):
            # TODO: late annotation
            subscript_paras.add(ValueInfo.get_any())
        else:
            _, elt_value = self.aval(subscript.slice)
            subscript_paras.add(elt_value[0][1])

        _, value_values = self.aval(subscript.value)

        if not isinstance(value_values[0][1], AnyType):
            subscript_value = value_values[0][0].direct_type()
            subscript_value.paras.extend(list(subscript_paras))

            return [], [(get_anonymous_ent(), subscript_value)]
        else:
            return [], [(get_anonymous_ent(), ValueInfo.get_any())]

    def aval_Constant(self, cons_expr: ast.Constant) -> Tuple[StoreAbles, AbstractValue]:
        value = cons_expr.value
        store_ables: List[StoreAble] = []
        builtins_type: str
        if isinstance(value, int):
            builtins_type = "int"
        elif isinstance(value, str):
            builtins_type = "str"
        else:  # ellipsis
            return [], [(get_anonymous_ent(), ValueInfo.get_any())]

        # TODO: find in builtins.py ---> int or str
        # NameInfoVisitor.is_builtins_continue(builtins_type, self.manager, self._current_db)
        builtins_path = Path("builtins.py")
        if builtins_path not in self.manager.root_db.tree:
            return [], [(get_anonymous_ent(), ValueInfo.get_any())]
        builtins_env = self.manager.root_db.tree[builtins_path].env
        lookup_res = builtins_env[builtins_type]
        ent_objs = lookup_res.found_entities
        if ent_objs:
            for ent, _ in ent_objs:
                s = get_named_store_able(ent, cons_expr)
                if s:
                    store_ables.append(s)

        return store_ables, ent_objs

    def aval_List(self, list_expr: ast.List) -> Tuple[StoreAbles, AbstractValue]:
        all_store_ables: List[StoreAble] = []
        use_avaler = ExprAnalyzer(self.manager, self._package_db, self._current_db, self._typing_entities, UseContext(),
                                  self._builder, self._env)

        positional: List["ValueInfo"] = []
        for index, elt in enumerate(list_expr.elts):

            sub_stores, ent_objs = use_avaler.aval(elt)

            if ent_objs:
                positional_type = ent_objs[0][1]
            else:
                positional_type = ValueInfo.get_any()
            positional.append(positional_type)

        # NameInfoVisitor.is_builtins_continue("list", self.manager, self._current_db)
        # lookup_res = self.manager.builtins_env["list"]
        # ent_objs = lookup_res.found_entities
        # list_builtins_type = ent_objs[0][1]
        list_builtins_type = ValueInfo.get_any()

        list_type = ListType(positional, list_builtins_type)

        return all_store_ables, [(get_anonymous_ent(), list_type)]

    def aval_Dict(self, dict_expr: ast.Dict) -> Tuple[StoreAbles, AbstractValue]:
        all_store_ables: List[StoreAble] = []
        use_avaler = ExprAnalyzer(self.manager, self._package_db, self._current_db, self._typing_entities, UseContext(),
                                  self._builder, self._env)

        key_type: ValueInfo = ValueInfo.get_any()
        value_type: ValueInfo = ValueInfo.get_any()
        for key in dict_expr.keys:
            key_store_able, key_abstract_value = use_avaler.aval(key)
            key_type = UnionType.union(key_type, key_abstract_value[0][1])

        for value in dict_expr.values:
            value_store_able, value_abstract_value = use_avaler.aval(value)
            if value_abstract_value and isinstance(value_abstract_value[0], Tuple):
                value_type = UnionType.union(value_type, value_abstract_value[0][1])

        # NameInfoVisitor.is_builtins_continue("dict", self.manager, self._current_db)
        # lookup_res = self.manager.builtins_env["dict"]
        # ent_objs = lookup_res.found_entities

        dict_type = DictType(ValueInfo.get_any())
        # dict_type = DictType(ent_objs[0][1])
        dict_type.add(key_type, value_type)

        return all_store_ables, [(get_anonymous_ent(), dict_type)]

    def aval_Compare(self, compare_expr: ast.Compare) -> Tuple[StoreAbles, AbstractValue]:
        all_store_ables: List[StoreAble] = []
        use_avaler = ExprAnalyzer(self.manager, self._package_db, self._current_db, self._typing_entities, UseContext(),
                                  self._builder, self._env)
        use_avaler.aval(compare_expr.left)
        for expr in compare_expr.comparators:
            use_avaler.aval(expr)

        # NameInfoVisitor.is_builtins_continue("bool", self.manager, self._current_db)
        # lookup_res = self.manager.builtins_env["bool"]
        # ent_objs = lookup_res.found_entities
        # compare_type = ent_objs[0][1]
        compare_type = ValueInfo.get_any()

        return all_store_ables, [(get_anonymous_ent(), compare_type)]


def extend_known_possible_attribute(manager: AnalyzeManager,
                                    attribute: str,
                                    possible_ents: AbstractValue,
                                    ret: AbstractValue,
                                    ctx: ExpressionContext,
                                    current_db: ModuleDB, attr_expr: ast.Attribute) -> None:
    for ent, ent_type in possible_ents:
        if isinstance(ent_type, UnionType):
            ent_types = ent_type.types
            ty_res = []
            for ty in ent_types:
                ents = try_to_extend(attribute, ty)
                if ents:
                    ty_res.append(ty)
            if ty_res:
                ent_types = ty_res
            for ty in ent_types:
                extend_by_value_info(manager, attribute, ret, current_db, attr_expr, ty, ent, ctx)
        else:
            extend_by_value_info(manager, attribute, ret, current_db, attr_expr, ent_type, ent, ctx)


def try_to_extend(attribute: str, ent_type: "ValueInfo") -> List[Entity]:
    ents: List[Entity] = []
    if isinstance(ent_type, InstanceType):
        ents = ent_type.lookup_attr(attribute)
    elif isinstance(ent_type, ConstructorType):
        ents = ent_type.lookup_attr(attribute)
    elif isinstance(ent_type, ModuleType):
        ents = ent_type.namespace[attribute]
    elif isinstance(ent_type, PackageType):
        ents = ent_type.namespace[attribute]
    elif isinstance(ent_type, ReferencedAttrType):
        ents = ent_type.lookup_attr(attribute)
    elif isinstance(ent_type, AnyType):
        ...
    elif isinstance(ent_type, UnionType):
        ...
    elif isinstance(ent_type, ListType):
        ...
    elif isinstance(ent_type, DictType):
        ...
    elif isinstance(ent_type, TupleType):
        ...
    elif isinstance(ent_type, FunctionType) or isinstance(ent_type, MethodType):
        ...
    else:
        # print(ent_type)
        log.error(f"Attribute[{ent_type}] receiver entity matching not implemented")
    return ents


def extend_by_value_info(manager: AnalyzeManager,
                         attribute: str,
                         ret: AbstractValue,
                         current_db: ModuleDB,
                         attr_expr: ast.Attribute, ent_type: "ValueInfo", ent: Entity, ctx: ExpressionContext) -> None:
    if isinstance(ent_type, InstanceType):
        class_attrs = ent_type.lookup_attr(attribute)
        process_known_attr(class_attrs, attribute, ret, current_db, ent_type.class_ent, ent_type, attr_expr, ctx,
                           manager)

    elif isinstance(ent_type, ConstructorType):
        class_attrs = ent_type.lookup_attr(attribute)
        process_known_attr(class_attrs, attribute, ret, current_db, ent_type.class_ent, ent_type, attr_expr, ctx,
                           manager)

    elif isinstance(ent_type, ModuleType):
        if isinstance(ent, Module):
            manager.strict_analyze_module(ent)
        module_level_ents = ent_type.namespace[attribute]
        process_known_attr(module_level_ents, attribute, ret, current_db, ent, ent_type, attr_expr, ctx, manager)

    elif isinstance(ent_type, PackageType):
        package_level_ents = ent_type.namespace[attribute]
        process_known_attr(package_level_ents, attribute, ret, current_db, ent, ent_type, attr_expr, ctx, manager)

    elif isinstance(ent_type, ReferencedAttrType):
        class_attrs = ent_type.lookup_attr(attribute)
        process_known_attr(class_attrs, attribute, ret, current_db, ent_type.referenced_attr_ent, ent_type, attr_expr, ctx,
                           manager)

    elif isinstance(ent_type, UnknownVarType):
        unknown_var_attrs = ent_type.lookup_attr(attribute)
        process_known_attr(unknown_var_attrs, attribute, ret, current_db, ent_type.unknown_var_ent, ent_type, attr_expr, ctx,
                           manager)

    elif isinstance(ent_type, DictType):
        extend_by_value_info(manager, attribute, ret, current_db, attr_expr, ent_type.dict_type, ent, ctx)

    elif isinstance(ent_type, TupleType):
        extend_by_value_info(manager, attribute, ret, current_db, attr_expr, ent_type.tuple_type, ent, ctx)

    elif isinstance(ent_type, ListType):
        extend_by_value_info(manager, attribute, ret, current_db, attr_expr, ent_type.list_type, ent, ctx)

    elif isinstance(ent_type, AnyType):

        global_referenced_attrs = manager.root_db.global_db.referenced_attrs
        if attribute in global_referenced_attrs:
            referenced_attr = global_referenced_attrs[attribute]
        else:
            location = Location.global_name(attribute)
            referenced_attr = ReferencedAttribute(location.to_longname(), location)
            global_referenced_attrs[attribute] = referenced_attr
            manager.root_db.global_db.add_ent(referenced_attr)

        ret.append((referenced_attr, ValueInfo.get_any()))

    elif isinstance(ent_type, UnionType):
        # TODO: unpack union type to access attributes
        ...
    else:
        # isinstance(ent_type, MethodType) or isinstance(ent_type, FunctionType)
        log.error(f"Attribute[{ent_type}] receiver entity matching not implemented")
        ret.append((get_anonymous_ent(), ValueInfo.get_any()))


def process_known_attr(attr_ents: Sequence[Entity], attribute: str, ret: AbstractValue, module_db: ModuleDB,
                       container: Entity, receiver_type: ValueInfo, attr_expr: ast.Attribute, ctx: ExpressionContext,
                       manager=None) -> None:
    if attr_ents:
        temp = []
        for ent_x in attr_ents:
            temp.append((ent_x, ent_x.direct_type()))
        ret.extend(temp)
    else:
        # if manager:
        #     stub_path = Path(container.longname.name + '.py')
        #     stub_db = manager.root_db.tree[stub_path] if stub_path in manager.root_db.tree else None
        #     if stub_db:
        #         env = stub_db._env
        #         get_stub = stub_db._get_stub
        #         stub_file = stub_db._stub_file
        #         bv = NameInfoVisitor(attribute, get_stub, manager, module_db,
        #                              env, stub_file)
        #         attr_info = get_stub.get(attribute) if get_stub else None
        #         ent = bv.generic_analyze(attribute, attr_info)
        #         ret.append((ent, ent.direct_type()))
        #         return None

        span = get_syntactic_head(attr_expr)
        if isinstance(receiver_type, InstanceType):  # Class Attribute
            span.offset(5)  # self len, or need to extend container name length
            location = container.location.append(attribute, span, None)
            class_ent = receiver_type.class_ent
            class_attr_ent = ClassAttribute(class_ent, location.to_longname(), location)
            class_attr_ent.is_class_attr = True
            class_attr_ent.exported = False if class_attr_ent.longname.name.startswith("__") else class_ent.exported
            if isinstance(ctx, SetContext):
                class_attr_ent.type = ctx.rhs_value[0][1]

            ret.append((class_attr_ent, class_attr_ent.direct_type()))
            module_db.add_ent(class_attr_ent)
            container.add_ref(Ref(RefKind.DefineKind, class_attr_ent, span.start_line, span.start_col, False, None))
            class_attr_ent.add_ref(Ref(RefKind.ChildOfKind, container, -1, -1, False, None))
        else:
            if isinstance(container, ModuleAlias):
                container = container.module_ent

            # TODO: it's a unknown attribute from module
            # container type is not ValueInfo.get_any() and we should
            # add Referenced Attribute at here
            location = container.location.append(attribute, span, None)
            referenced_attr = ReferencedAttribute(location.to_longname(), location)
            referenced_attr.exported = container.exported

            # attr = Attribute(location.to_longname(), location)
            # attr.exported = container.exported

            module_db.add_ent(referenced_attr)
            container.add_ref(Ref(RefKind.DefineKind, referenced_attr, attr_expr.lineno, attr_expr.col_offset, False, None))
            referenced_attr.add_ref(Ref(RefKind.ChildOfKind, container, -1, -1, False, None))

            ret.append((referenced_attr, referenced_attr.direct_type()))


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
        location = container.location.append(attribute, Span.get_nil(), None)
        unresolved = UnresolvedAttribute(location.to_longname(), location, receiver_type)

        ret.append(NewlyCreated(Span.get_nil(), unresolved))


def filter_not_setable_entities(ent_objs: AbstractValue) -> AbstractValue:
    ret = []
    for e, v in ent_objs:
        if not isinstance(e, (Class, Function, Module, ModuleAlias)):
            ret.append((e, v))
    return ret


def get_builtins_class_info(cls_name, invoke_ctx):
    # NameInfoVisitor.is_builtins_continue(cls_name, invoke_ctx.manager, invoke_ctx.current_db)
    # lookup_res = invoke_ctx.manager.builtins_env[cls_name]
    # ent_objs = lookup_res.found_entities
    # return ent_objs[0][1]
    return ValueInfo.get_any()


def invoke(invoke_ctx: InvokeContext):
    ret = []

    for callee, func_type in invoke_ctx.possible_callees:
        return_type = []
        try:
            # print(len(invoke_ctx.manager.func_invoking_set))
            if callee in invoke_ctx.manager.func_invoking_set or len(invoke_ctx.manager.func_invoking_set) > 10:
                ret.append((callee, ValueInfo.get_any()))
                continue

            # invoke function entry
            invoke_match(func_type, invoke_ctx, return_type)

            if len(return_type) == 1:
                ret.append((callee, return_type[0]))
            else:
                ret.append((callee, return_type))
        except AssertionError as ae:
            log.warning(f'Calling Function[{callee.longname.longname}] assertion wrong.'
                        f' Location "{invoke_ctx.current_db.module_ent.absolute_path}:{invoke_ctx.call_expr.lineno}".')
            return [(get_anonymous_ent(), ValueInfo.get_any())]
    if not ret:
        return [(get_anonymous_ent(), ValueInfo.get_any())]
    return ret


def invoke_match(func_type, invoke_ctx, return_type):
    if isinstance(func_type, ConstructorType):  # invoke class constructor
        invoke_constructor(invoke_ctx, func_type)
        instance_type = func_type.to_class_type()
        args = invoke_ctx.args_info['args']
        for arg in args:
            if arg and isinstance(arg[0], tuple):
                instance_type.paras.append(arg[0][1])
        return_type.append(instance_type)
    elif isinstance(func_type, FunctionType):  # invoke function
        return_type.append(invoke_function(invoke_ctx, func_type))
    elif isinstance(func_type, MethodType):  # invoke method
        return_type.append(invoke_method(invoke_ctx, func_type))
    elif isinstance(func_type, ListType):  # invoke method
        for f_ty in func_type.positional:
            invoke_match(f_ty, invoke_ctx, return_type)
    elif isinstance(func_type, UnknownVarType):
        return_type.append(func_type)
    elif isinstance(func_type, ReferencedAttrType):
        return_type.append(ValueInfo.get_any())
    else:
        return_type.append(ValueInfo.get_any())


def invoke_constructor(invoke_ctx: InvokeContext, func_type: ConstructorType) -> "ValueInfo":
    try:
        callee = func_type.class_ent
        assert isinstance(callee, Class)
        body_env = callee.get_body_env()
        constructor = body_env["__init__"].found_entities
        assert constructor
        callee = constructor[0][0]
        func_type = callee.direct_type()
        return invoke_invoke(invoke_ctx, func_type)
    except AssertionError as e:
        ...


def invoke_function(invoke_ctx: InvokeContext, func_type: FunctionType) -> "ValueInfo":
    return invoke_invoke(invoke_ctx, func_type)


def invoke_method(invoke_ctx: InvokeContext, func_type: MethodType) -> "ValueInfo":
    return invoke_invoke(invoke_ctx, func_type)


def invoke_invoke(invoke_ctx: InvokeContext, func_type: MethodType | FunctionType) -> "ValueInfo":
    import enre.analysis.analyze_stmt as analyze_stmt
    callee = func_type.func_ent

    assert isinstance(callee, Function)
    # if callee is a typeshed function, we don't need call it,
    # and we should return it immediately.
    # TODO: typeshed function overload parameter match
    if callee.typeshed_func:
        return callee.signatures[0].return_type

    # 1. Get function call environment
    body = callee.get_body()
    env, body_env, rel_path = callee.get_body_env()
    builder = body_env.get_builder()
    analyzer = analyze_stmt.Analyzer(rel_path, invoke_ctx.manager)
    analyzer.current_db.set_env(env)
    assert isinstance(body_env, ScopeEnv)

    # if callee.longname.longname == "ENRE-py.enre.analysis.env.ScopeEnv.__init__":
    #     invoke_ctx.manager.counter += 1
    #     if invoke_ctx.manager.counter == 2:
    #         print(callee)

    # 2. Parameters match
    args_type = bind_parameter(body_env, callee, invoke_ctx, func_type)
    if not args_type:  # wrong case, not to call this function
        return ValueInfo.get_any()

    if callee.has_mapping(args_type):
        return callee.get_mapping(args_type)

    callee.set_mapping(args_type)
    callee.calling_stack.append(CallType(args_type))

    env.add_scope(body_env)
    # 3. Invoke
    invoke_ctx.manager.func_invoking_set.add(callee)
    analyzer.analyze_top_stmts(body, builder, env)
    if callee in invoke_ctx.manager.func_invoking_set:
        invoke_ctx.manager.func_invoking_set.remove(callee)
    if callee in invoke_ctx.manager.func_uncalled_set:
        invoke_ctx.manager.func_uncalled_set.remove(callee)
    return_type = callee.calling_stack.pop().return_type
    callee.set_mapping(args_type, return_type)
    env.pop_scope()

    return return_type


def bind_parameter(body_env: ScopeEnv, callee: Function, invoke_ctx: InvokeContext, func_type: ValueInfo) \
        -> Optional["ListType"]:
    assert isinstance(body_env, ScopeEnv)
    signature = callee.callable_signature
    # if function overload and do not have an implementation
    # we shouldn't call it
    assert signature
    args_index = 0
    para_index = 0
    args = invoke_ctx.args_info['args']
    kwagrs = invoke_ctx.args_info['kwargs']

    if isinstance(func_type, ConstructorType):  # class __init__
        para_index = para_index + 1  # offset "self"
    elif isinstance(func_type, FunctionType):  # function
        ...
    elif isinstance(func_type, MethodType):  # method
        if signature.function_call_least_posonlyargs_length() > 0:
            first_para_name = signature.get_posonlyargs(0).longname.name
            if first_para_name == "cls" or first_para_name == "self":  # class method
                para_index = para_index + 1
            else:  # class static method
                ...

    p = args_index
    q = para_index

    """process position only args"""
    calling_posonlyargs_length = len(args)
    calling_kwonlyargs_length = len(kwagrs)
    least_posonlyargs_length = signature.function_call_least_posonlyargs_length()
    least_kwonlyargs_length = signature.function_call_least_kwonlyargs_length()
    if calling_posonlyargs_length < least_posonlyargs_length and \
            not calling_kwonlyargs_length >= least_posonlyargs_length - calling_posonlyargs_length + least_kwonlyargs_length:
        # wrong
        log.warning(f"Calling function [{callee.longname.longname}] wrong, parameters pass less than the least length."
                    f' Location "{invoke_ctx.current_db.module_ent.absolute_path}:{invoke_ctx.call_expr.lineno}".')
        return None
    args_info = []
    while p < calling_posonlyargs_length and least_posonlyargs_length > 0:
        if args[p] and isinstance(args[p][0], tuple):
            ent, info = args[p][0]
            args_info.append(info)
            if not isinstance(info, AnyType):
                name = signature.get_posonlyargs(q).longname.name
                body_env.reset_binding_value(name, info)  # set current parameters pass value
                signature.get_posonlyargs(q).add_type(info)  # replenish function parameter type

        p = p + 1
        q = q + 1
        least_posonlyargs_length = least_posonlyargs_length - 1

    if least_posonlyargs_length > 0:
        # use kw arg to fulfill positional only args
        while least_posonlyargs_length > 0 and q < len(signature.posonlyargs):
            pos_arg = signature.get_posonlyargs(q)
            pos_name = pos_arg.longname.name
            if pos_name in kwagrs:
                kw_info = kwagrs[pos_name]
                if kw_info and isinstance(kw_info[0], tuple):
                    ent, info = kw_info[0]
                    args_info.append(info)

                    if not isinstance(info, AnyType):
                        body_env.reset_binding_value(pos_name, info)  # set current parameters pass value
                        pos_arg.add_type(info)  # replenish function parameter type
                del kwagrs[pos_name]
                least_posonlyargs_length = least_posonlyargs_length - 1
            else:
                # wrong
                log.warning(
                    f"Calling function [{callee.longname.longname}] wrong, positional parameters pass less than the least length."
                    f' Location "{invoke_ctx.current_db.module_ent.absolute_path}:{invoke_ctx.call_expr.lineno}".')
                return None
            q = q + 1
    if least_posonlyargs_length > 0:
        # wrong
        log.warning(
            f"Calling function [{callee.longname.longname}] wrong, positional parameters pass less than the least length."
            f' Location "{invoke_ctx.current_db.module_ent.absolute_path}:{invoke_ctx.call_expr.lineno}".')
        return None
    """process keyword only args"""
    assert isinstance(kwagrs, dict)
    if signature.kwonlyargs:
        for kw_name, kw_arg in signature.kwonlyargs.items():
            if kw_name in kwagrs:
                kw_info = kwagrs[kw_name]
                if kw_info and isinstance(kw_info[0], tuple):
                    ent, info = kw_info[0]
                    args_info.append(info)

                    if not isinstance(info, AnyType):
                        body_env.reset_binding_value(kw_name, info)  # set current parameters pass value
                        signature.get_kwonlyargs(kw_name).add_type(info)  # replenish function parameter type
                del kwagrs[kw_name]
            else:  # default
                if kw_arg.has_default:
                    ...  # uses defining binding
                else:
                    # wrong
                    log.warning(
                        f"Calling Function[{callee.longname.longname}] wrong, not provide Parameter[{kw_name}] value."
                        f' Location "{invoke_ctx.current_db.module_ent.absolute_path}:{invoke_ctx.call_expr.lineno}".')
                    return None

    """process starstarargargs"""
    if signature.has_starstararg:

        str_value = get_builtins_class_info("str", invoke_ctx)
        dict_value = DictType(get_builtins_class_info("dict", invoke_ctx))
        for res_kw_name, res_kw_info in kwagrs.items():
            if res_kw_info and isinstance(res_kw_info[0], tuple):
                ent, info = res_kw_info[0]
                dict_value.add(str_value, info)
                dict_value.dict_dict[res_kw_name] = info

        starstararg_ent = signature.get_starstararg()
        name = starstararg_ent.longname.name
        starstararg_ent.add_type(dict_value)
        body_env.reset_binding_value(name, dict_value)
        args_info.append(dict_value)

    """process stararg"""
    if signature.has_stararg:
        tuple_value = TupleType(get_builtins_class_info("tuple", invoke_ctx))
        args_length = len(args)
        while p < args_length:
            if args[p] and isinstance(args[p][0], tuple):
                ent, info = args[p][0]
                tuple_value.add_single(info)
            p = p + 1
        args_info.append(tuple_value)
        stararg_ent = signature.get_stararg()
        name = stararg_ent.longname.name
        stararg_ent.add_type(tuple_value)
        body_env.reset_binding_value(name, tuple_value)

    args_type = ListType(args_info, get_builtins_class_info("list", invoke_ctx))
    return args_type


def resolve_overlays(manager, objs):
    if objs and isinstance(objs[0], tuple) and not manager.analyzing_typing_builtins:
        ent = objs[0][0]
        typ = objs[0][1]
        if isinstance(typ, InstanceType):
            typ = manager.overlays_dispatcher.handle_instance_or_constructor_type(typ)
        elif isinstance(typ, ConstructorType):
            typ = manager.overlays_dispatcher.handle_instance_or_constructor_type(typ)
        objs[0] = (ent, typ)
