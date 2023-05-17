import ast
import itertools
from abc import ABC
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence, Optional, Iterable
from typing import Tuple, List, TYPE_CHECKING

from enre.analysis.analyze_manager import RootDB, ModuleDB, AnalyzeManager
from enre.analysis.assign_target import dummy_unpack, unpack_semantic, assign2target
from enre.analysis.env import EntEnv, ScopeEnv, SubEnvLookupResult
from enre.pyi.visitor import NameInfoVisitor

if TYPE_CHECKING:
    from enre.analysis.env import Bindings
from enre.analysis.value_info import ValueInfo, ConstructorType, InstanceType, ModuleType, AnyType, PackageType, \
    FunctionType, MethodType, UnionType, DictType, TupleType, CallType, ListType, \
    UnknownVarType, ReferencedAttrType, NoneType, SetType, ConstantType
from enre.cfg.module_tree import SummaryBuilder, StoreAble, FuncConst, StoreAbles, get_named_store_able, \
    ModuleSummary
from enre.ent.EntKind import RefKind
from enre.ent.entity import AbstractValue, get_syntactic_head, ClassAttribute, Signature, _Nil_Span, Parameter
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
                typeshed_ent = NameInfoVisitor.analyze_wrapper(self.manager, self._current_db.module_dummy_path,
                                                               self._env, self._current_db.typeshed_stub_names,
                                                               name_expr.id)
                if typeshed_ent:
                    lookup_res = self._env[name_expr.id]
                    ent_objs = lookup_res.found_entities
                    if ent_objs:
                        for ent, _ in ent_objs:
                            s = get_named_store_able(ent, name_expr)
                            if s:
                                store_ables.append(s)
                    res_ent = typeshed_ent
                else:
                    unknown_var_name = name_expr.id

                    if self.manager.analyzing_typing_builtins:
                        # should add this unknown var to module db
                        location = Location.global_name(unknown_var_name)
                        unknown_var = UnknownVar(unknown_var_name, location)
                        self._current_db.add_ent(unknown_var)
                        new_binding: "Bindings" = [(unknown_var.longname.name, [(unknown_var, unknown_var.direct_type())])]
                        self._current_db.top_scope.add_continuous_to_bottom(new_binding)
                    else:
                        global_unknown_vars = self.manager.root_db.global_db.unknown_vars
                        if unknown_var_name in global_unknown_vars:
                            unknown_var = global_unknown_vars[unknown_var_name]
                        else:
                            location = Location.global_name(unknown_var_name)
                            unknown_var = UnknownVar(unknown_var_name, location)
                            global_unknown_vars[unknown_var_name] = unknown_var
                            self.manager.root_db.global_db.add_ent(unknown_var)

                    ent_objs = [(unknown_var, unknown_var.direct_type())]
                    res_ent = unknown_var

                ctx.add_ref(
                    self.create_ref_by_ctx(res_ent, name_expr.lineno, name_expr.col_offset, self._typing_entities,
                                           self._exp_ctx, name_expr))
                return store_ables, ent_objs
        else:
            lhs_objs: SetContextValue = []
            need_to_create = False
            if isinstance(ctx, Function) and ent_objs:
                found_ent = ent_objs[0][0]
                if found_ent not in ctx.children:
                    need_to_create = True

            if ent_objs and not need_to_create:
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

        attr_expr_span = get_syntactic_span(attr_expr.value)
        attr_expr_start_line = attr_expr_span.end_line
        attr_expr_start_col = attr_expr_span.end_col + 1
        new_ret: AbstractValue = []

        # remove duplicate ent, value
        ret_dic = dict()
        for ent, value in ret:
            ret_dic[ent] = value
        ret = []
        for ent, value in ret_dic.items():
            ret.append((ent, value))

        for ent, value in ret:
            self._env.get_ctx().add_ref(
                self.create_ref_by_ctx(ent, attr_expr_start_line, attr_expr_start_col,
                                       self._typing_entities, self._exp_ctx, attr_expr))
            if isinstance(ent, Function) and ent.property:
                signature = ent.callable_signature
                return_type = resolve_typeshed_return(signature.return_type,
                                                      ent.get_scope_env(), ent,
                                                      signature)
                new_ret.append((ent, return_type))
            else:
                new_ret.append((ent, value))
        ret = new_ret
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
        lambda_dummy_name = f"({lam_expr.lineno})"

        lookup_res = self._env[lambda_dummy_name]
        if lookup_res.must_found:
            ent = lookup_res.found_entities[0][0]
            return [], [(ent, ValueInfo.get_any())]

        lam_span = get_syntactic_span(lam_expr)
        now_scope = self._env.get_scope().get_location()
        new_scope = now_scope.append(lambda_dummy_name, lam_span, None)
        func_ent = LambdaFunction(new_scope.to_longname(), new_scope)

        # add function entity to dependency database
        self._current_db.add_ent(func_ent)
        # add reference of current context to the function entity
        self._env.get_ctx().add_ref(
            self.create_ref_by_ctx(func_ent, lam_expr.lineno, lam_expr.col_offset, self._typing_entities, self._exp_ctx,
                                   lam_expr))
        self._env.get_ctx().add_ref(
            Ref(RefKind.DefineKind, func_ent, lam_expr.lineno, lam_expr.col_offset, False, None))
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

        # hook_scope = self._env.get_scope(1) if in_class_env else self._env.get_scope()
        # # type error due to member in ast node is, but due to any member in our structure is only readable,
        # # this type error is safety
        # lam_body: List[ast.stmt] = [ast.Expr(lam_expr.body)]
        # hook_scope.add_hook(lam_body, body_env)
        func_ent.set_body_env(self._env.get_env(), body_env, self._current_db.module_path)
        func_ent.set_body([ast.Expr(lam_expr.body)])
        func_ent.callable_signature = func_ent.signatures[-1]

        new_binding: "Bindings" = [(lambda_dummy_name, [(func_ent, func_ent.direct_type())])]
        func_ent.set_direct_type(FunctionType(func_ent))
        self._env.get_scope().add_continuous(new_binding)

        if not self.manager.analyzing_typing_builtins:
            self.manager.func_uncalled_dic[func_ent] = True

        return [], [(func_ent, ValueInfo.get_any())]

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

        r_value = []
        if isinstance(context, SetContext):
            rhs_abstract_value = context.rhs_value
            if rhs_abstract_value:
                temp_r = rhs_abstract_value[0][1]
                if isinstance(temp_r, ConstructorType) and temp_r.class_ent.longname.longname == "builtins.dict_items":
                    r_value = temp_r.paras
                elif isinstance(temp_r, TupleType):
                    r_value = temp_r.positional
                else:
                    r_value.append(temp_r)

        for index, elt in enumerate(tuple_exp.elts):
            avaler: ExprAnalyzer
            if isinstance(context, SetContext):
                avaler = ExprAnalyzer(self.manager, self._package_db, self._current_db, self._typing_entities,
                                      SetContext(False, dummy_unpack(r_value, index), []), self._builder,
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

        tuple_type = get_builtins_class_info("tuple", self.manager)
        assert isinstance(tuple_type, ConstructorType)
        tuple_value = TupleType(tuple_type.class_ent)
        tuple_value.add(value_infos)

        return [], [(get_anonymous_ent(), tuple_value)]

    def aval_Subscript(self, subscript: ast.Subscript) -> Tuple[StoreAbles, AbstractValue]:
        # TODO: li = []

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
        # TODO: special for Generic

        if not isinstance(value_values[0][1], AnyType):
            subscript_value = value_values[0][0].direct_type()
            subscript_value.paras.extend(list(subscript_paras))

            return [], [(get_anonymous_ent(), subscript_value)]
        else:
            return [], [(get_anonymous_ent(), ValueInfo.get_any())]

    def aval_Constant(self, cons_expr: ast.Constant) -> Tuple[StoreAbles, AbstractValue]:
        value = cons_expr.value
        builtins_type: str
        if isinstance(value, bool):
            builtins_type = "bool"
        elif isinstance(value, int):
            builtins_type = "int"
        elif isinstance(value, str):
            builtins_type = "str"
        else:  # ellipsis
            return [], [(get_anonymous_ent(), ValueInfo.get_any())]

        # TODO: find in builtins.py ---> int or str
        # NameInfoVisitor.is_builtins_continue(builtins_type, self.manager, self._current_db)

        builtins_name = ast.Name(builtins_type, None)
        builtins_name.lineno = cons_expr.lineno
        builtins_name.col_offset = cons_expr.col_offset
        use_avaler = ExprAnalyzer(self.manager, self._package_db, self._current_db,
                                  self._typing_entities, UseContext(), self._builder, self._env)

        cons_type = ConstantType(value)
        store_ables, ent_objs = use_avaler.aval(builtins_name)
        ent = ent_objs[0][0]
        builtins_type: ValueInfo = ent.direct_type()
        builtins_type.paras.append(cons_type)
        return store_ables, [(ent, builtins_type)]

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

        list_type = ValueInfo.get_any()
        list_instance_type = get_builtins_class_info("list", self.manager)
        if isinstance(list_instance_type, ConstructorType):
            list_type = ListType(positional, list_instance_type.class_ent)

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

        dict_instance_type = get_builtins_class_info("dict", self.manager)
        dict_type = ValueInfo.get_any()
        if isinstance(dict_instance_type, ConstructorType):
            dict_type = DictType(dict_instance_type.class_ent)
            # dict_type.class_ent.alias_map['typing.Mapping']
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

    def aval_NamedExpr(self, named_expr: ast.NamedExpr) -> Tuple[StoreAbles, AbstractValue]:
        from enre.analysis.analyze_stmt import AnalyzeContext
        target_expr = named_expr.target
        rvalue_expr = named_expr.value
        target_lineno = target_expr.lineno
        target_col_offset = target_expr.col_offset
        assign2target(target_expr, rvalue_expr, self._env.get_scope().get_builder(),
                      AnalyzeContext(self._env,
                                     self.manager,
                                     self._package_db,
                                     self._current_db,
                                     (target_lineno, target_col_offset),
                                     False))
        return [], [(get_anonymous_ent(), ValueInfo.get_any())]



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
                ents = try_to_extend(attribute, ty, manager)
                if ents:
                    exists = False
                    for t in ty_res:
                        if ty.type_equals(t):
                            exists = True
                    if not exists:
                        ty_res.append(ty)
            if ty_res:
                ent_types = ty_res
            for ty in ent_types:
                extend_by_value_info(manager, attribute, ret, current_db, attr_expr, ty, ent, ctx)
        else:
            extend_by_value_info(manager, attribute, ret, current_db, attr_expr, ent_type, ent, ctx)


def try_to_extend(attribute: str, ent_type: "ValueInfo", manager) -> List[Entity]:
    ents: List[Entity] = []
    if isinstance(ent_type, InstanceType):
        ents = ent_type.lookup_attr(attribute, manager)
    elif isinstance(ent_type, ConstructorType):
        ents = ent_type.lookup_attr(attribute, manager)
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
    elif isinstance(ent_type, SetType):
        ...
    elif isinstance(ent_type, FunctionType) or isinstance(ent_type, MethodType):
        ...
    elif isinstance(ent_type, UnknownVarType) or isinstance(ent_type, NoneType):
        ...
    else:
        print(ent_type.__str__())
        print(type(ent_type))

        log.error(f"Attribute[{ent_type}] receiver entity matching not implemented")
        print("----------------")
    return ents


def extend_by_value_info(manager: AnalyzeManager,
                         attribute: str,
                         ret: AbstractValue,
                         current_db: ModuleDB,
                         attr_expr: ast.Attribute, ent_type: "ValueInfo", ent: Entity, ctx: ExpressionContext) -> None:
    if isinstance(ent_type, InstanceType):
        class_attrs = ent_type.lookup_attr(attribute, manager)
        # resolve typeshed builtins alias
        # resolve_builtins_generic(class_attrs, ent_type)
        process_known_attr(class_attrs, attribute, ret, current_db, ent_type.class_ent, ent_type, attr_expr, ctx,
                           manager)

    elif isinstance(ent_type, ConstructorType):
        class_attrs = ent_type.lookup_attr(attribute, manager)
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
        process_known_attr(class_attrs, attribute, ret, current_db, ent_type.referenced_attr_ent, ent_type, attr_expr,
                           ctx,
                           manager)

    elif isinstance(ent_type, UnknownVarType):
        unknown_var_attrs = ent_type.lookup_attr(attribute)
        process_known_attr(unknown_var_attrs, attribute, ret, current_db, ent_type.unknown_var_ent, ent_type, attr_expr,
                           ctx,
                           manager)

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
    elif isinstance(ent_type, NoneType) or isinstance(ent_type, UnknownVarType):
        ...
    elif isinstance(ent_type, MethodType):
        ...
    else:
        print(type(ent_type))
        # isinstance(ent_type, MethodType) or isinstance(ent_type, FunctionType)
        log.error(f"Attribute[{ent_type}] receiver entity matching not implemented")
        ret.append((get_anonymous_ent(), ValueInfo.get_any()))


def process_known_attr(attr_ents: Sequence[Entity], attribute: str, ret: AbstractValue, module_db: ModuleDB,
                       container: Entity, receiver_type: ValueInfo, attr_expr: ast.Attribute, ctx: ExpressionContext,
                       manager=None) -> None:
    resolve_builtins_generic(attr_ents, receiver_type)
    if attr_ents:
        temp = []
        for ent_x in attr_ents:
            temp.append((ent_x, ent_x.direct_type()))
        ret.extend(temp)
    else:
        span = get_syntactic_head(attr_expr)
        if isinstance(receiver_type, InstanceType):
            # TODO: if it is a typeshed Class, we should find in its stub names
            assert isinstance(container, Class)
            if container.typeshed_class:
                typeshed_module_dummy_path = container.typeshed_module_dummy_path
                typeshed_module_db = manager.root_db.tree[typeshed_module_dummy_path]
                env: EntEnv = typeshed_module_db.env
                env.add_scope(container.get_body_env())
                ent = NameInfoVisitor.analyze_wrapper(manager, typeshed_module_dummy_path, env,
                                                      container.typeshed_children, attribute)
                env.pop_scope()
                if ent:
                    ret.append((ent, ent.direct_type()))
                    return

            # Class Attribute
            span.offset(5)  # self len, or need to extend container name length
            location = container.location.append(attribute, span, None)
            class_ent = receiver_type.class_ent
            class_attr_ent = ClassAttribute(class_ent, location.to_longname(), location)
            class_attr_ent.is_class_attr = True
            class_attr_ent.exported = False if class_attr_ent.longname.name.startswith("__") else class_ent.exported
            if isinstance(ctx, SetContext):
                if not ctx.rhs_value:
                    class_attr_ent.type = ValueInfo.get_any()
                else:
                    class_attr_ent.type = ctx.rhs_value[0][1]

            ret.append((class_attr_ent, class_attr_ent.direct_type()))
            module_db.add_ent(class_attr_ent)
            # if module_db.env:
            #     env = module_db.env
            #     assert isinstance(env, EntEnv)
            #     env.get_ctx().add_ref(Ref(RefKind.DefineKind, class_attr_ent, span.start_line, span.start_col, False, None))
            # else:
            container.add_ref(Ref(RefKind.DefineKind, class_attr_ent, span.start_line, span.start_col, False, None))
            class_attr_ent.add_ref(Ref(RefKind.ChildOfKind, container, -1, -1, False, None))
        else:
            if isinstance(container, ModuleAlias):
                container = container.module_ent
            # TODO: if it is a typeshed module, we should find in its stub names

            if isinstance(container, Module) and container.typeshed_module:
                typeshed_module_dummy_path = Path(container.longname.name + '.py')
                typeshed_module_db = manager.root_db.tree[typeshed_module_dummy_path]
                ent = NameInfoVisitor.analyze_wrapper(manager, typeshed_module_dummy_path, typeshed_module_db.env,
                                                      typeshed_module_db.typeshed_stub_names, attribute)
                if ent:
                    ret.append((ent, ent.direct_type()))
                    return

            # TODO: it's a unknown attribute from module
            # container type is not ValueInfo.get_any() and we should
            # add Referenced Attribute at here
            location = container.location.append(attribute, span, None)
            referenced_attr = ReferencedAttribute(location.to_longname(), location)
            # print(referenced_attr.longname.longname)
            referenced_attr.exported = container.exported

            # attr = Attribute(location.to_longname(), location)
            # attr.exported = container.exported

            module_db.add_ent(referenced_attr)
            container.add_ref(
                Ref(RefKind.DefineKind, referenced_attr, attr_expr.lineno, attr_expr.col_offset, False, None))
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


def get_builtins_class_info(cls_name, manager):
    builtins_path = Path("builtins.py")
    if builtins_path not in manager.root_db.tree:
        return ValueInfo.get_any()
    builtins_env: EntEnv = manager.root_db.tree[builtins_path].env
    lookup_res = builtins_env[cls_name]
    if lookup_res.must_found:
        ent_objs = lookup_res.found_entities
        return ent_objs[0][1]
    else:
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
            # print(callee.longname.longname)
            invoke_match(func_type, invoke_ctx, return_type)

            if len(return_type) == 1:
                ret.append((callee, return_type[0]))
            else:
                ret.append((callee, return_type))
        except AssertionError as ae:
            print(callee.longname.longname)
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
        # if callee.longname.longname == "builtins.dict":
        #     print("dict")
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

    # 1. Get function call environment
    body = callee.get_body()
    env, body_env, rel_path = callee.get_body_env()
    builder = body_env.get_builder()
    # body_env_ori = body_env.get_scope_env()
    assert isinstance(body_env, ScopeEnv)

    # if callee.longname.longname == 'ENRE-py.enre.analysis.analyze_manager.ModuleDB.parse_a_module':
    #     print(callee)

    # 2. Parameters match
    signature = None
    if callee.typeshed_func:
        if len(callee.signatures) > 1:  # overload
            for sig in callee.signatures:
                try:
                    try_res = bind_parameter(body_env, callee, invoke_ctx, func_type, sig, try_mode=True)
                    if try_res:
                        signature = sig
                        break
                except AssertionError:
                    ...  # params not match
        else:
            signature = callee.signatures[0]

        return resolve_typeshed_return(signature.return_type, body_env, callee, signature)
    else:
        signature = callee.callable_signature
    if not signature:
        if callee in invoke_ctx.manager.func_invoking_set:
            invoke_ctx.manager.func_invoking_set.remove(callee)
        if callee in invoke_ctx.manager.func_uncalled_dic:
            invoke_ctx.manager.func_uncalled_dic.pop(callee)
        return ValueInfo.get_any()

    args_type = bind_parameter(body_env, callee, invoke_ctx, func_type, signature)

    if not args_type:  # wrong case, not to call this function
        return ValueInfo.get_any()

    args_type_key = str(args_type)

    if callee.has_mapping(args_type_key):
        return callee.get_mapping(args_type_key)

    callee.set_mapping(args_type_key)
    callee.calling_stack.append(CallType(args_type))

    env.add_scope(body_env)
    # 3. Invoke
    analyzer = analyze_stmt.Analyzer(rel_path, invoke_ctx.manager)
    analyzer.current_db.set_env(env)
    invoke_ctx.manager.func_invoking_set.add(callee)
    analyzer.analyze_top_stmts(body, builder, env)
    # callee.set_scope_env(body_env_ori)
    if callee in invoke_ctx.manager.func_invoking_set:
        invoke_ctx.manager.func_invoking_set.remove(callee)
    # if callee in invoke_ctx.manager.func_uncalled_set:
    #     # invoke_ctx.manager.func_uncalled_set.remove(callee) #
    #     invoke_ctx.manager.func_uncalled_dic.pop(callee)
    if callee in invoke_ctx.manager.func_uncalled_dic:
        # invoke_ctx.manager.func_uncalled_set.remove(callee) #
        invoke_ctx.manager.func_uncalled_dic.pop(callee)
    return_type = callee.calling_stack.pop().return_type
    callee.set_mapping(args_type_key, return_type)
    env.pop_scope()

    return return_type


def bind_parameter(body_env: ScopeEnv, callee: Function, invoke_ctx: InvokeContext,
                   func_type: ValueInfo, signature, try_mode=False) \
        -> Optional["ListType"]:
    assert isinstance(body_env, ScopeEnv)
    assert isinstance(signature, Signature)
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

    """process positional only args"""
    calling_posonlyargs_length = len(args)
    calling_kwonlyargs_length = len(kwagrs)
    least_posonlyargs_length = signature.function_call_least_posonlyargs_length()
    least_kwonlyargs_length = signature.function_call_least_kwonlyargs_length()
    if calling_posonlyargs_length < least_posonlyargs_length and \
            not calling_kwonlyargs_length >= least_posonlyargs_length - calling_posonlyargs_length + least_kwonlyargs_length:
        # wrong
        if not try_mode:
            log.warning(
                f"Calling function [{callee.longname.longname}] wrong, parameters pass less than the least length."
                f' Location "{invoke_ctx.current_db.module_ent.absolute_path}:{invoke_ctx.call_expr.lineno}".')
        return None
    if calling_posonlyargs_length + para_index > len(signature.posonlyargs):
        if not try_mode:
            lineno = invoke_ctx.call_expr.lineno if invoke_ctx.call_expr else -1
            log.warning(
                f"Calling function [{callee.longname.longname}] wrong, parameters more than required length."
                f' Location "{invoke_ctx.current_db.module_ent.absolute_path}:{lineno}".')
        return None
    # TODO: compare kwonlyargs
    args_info = []
    while p < calling_posonlyargs_length and least_posonlyargs_length > 0:
        if args[p] and isinstance(args[p][0], tuple):
            ent, info = args[p][0]
            args_info.append(info)
            if not isinstance(info, AnyType):
                pos_param = signature.get_posonlyargs(q)
                name = pos_param.longname.name

                body_env.reset_binding_value(name, info)  # set current parameters pass value
                signature.get_posonlyargs(q).add_type(info)  # replenish function parameter type

                # add type to env[alias_name]
                bindings: Bindings = []
                for alias_name in pos_param.alias_set:
                    bindings.append((alias_name, [(get_anonymous_ent(), info)]))
                if bindings:
                    body_env.add_continuous(bindings)

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

                    # add type to env[alias_name]
                    bindings: Bindings = []
                    for alias_name in pos_arg.alias_set:
                        bindings.append((alias_name, [(get_anonymous_ent(), info)]))
                    if bindings:
                        body_env.add_continuous(bindings)

                del kwagrs[pos_name]
                least_posonlyargs_length = least_posonlyargs_length - 1
            else:
                # wrong
                if not try_mode:
                    log.warning(
                        f"Calling function [{callee.longname.longname}] wrong, positional parameters pass less than the least length."
                        f' Location "{invoke_ctx.current_db.module_ent.absolute_path}:{invoke_ctx.call_expr.lineno}".')
                return None
            q = q + 1
    if least_posonlyargs_length > 0:
        # wrong
        if not try_mode:
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
                    if not try_mode:
                        log.warning(
                            f"Calling Function[{callee.longname.longname}] wrong, not provide Parameter[{kw_name}] value."
                            f' Location "{invoke_ctx.current_db.module_ent.absolute_path}:{invoke_ctx.call_expr.lineno}".')
                    return None

    """process starstarargargs"""
    if signature.has_starstararg:

        str_value = get_builtins_class_info("str", invoke_ctx.manager)
        dict_instance_type = get_builtins_class_info("dict", invoke_ctx.manager)
        assert isinstance(dict_instance_type, ConstructorType)
        dict_value = DictType(dict_instance_type.class_ent)
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
        tuple_type = get_builtins_class_info("tuple", invoke_ctx.manager)
        assert isinstance(tuple_type, ConstructorType)
        tuple_value = TupleType(tuple_type.class_ent)
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

    list_type = get_builtins_class_info("list", invoke_ctx.manager)
    assert isinstance(list_type, ConstructorType)
    args_type = ListType(args_info, list_type.class_ent)
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


# TODO: Pack arguments
def resolve_typeshed_return(return_type: ValueInfo, body_env: ScopeEnv, callee: Function, signature: Signature):
    if isinstance(return_type, InstanceType):
        if return_type.class_ent.longname.longname == "typing.TypeVar":
            tv_name = return_type.paras[0].paras[0]
            assert isinstance(tv_name, ConstantType)
            generic_name = tv_name.value
            # TODO: find in callee seen generic names
            alias_seen = signature.alias_seen
            for alias_name in alias_seen:
                assert isinstance(alias_name, str)
                alias_name_split = alias_name.split(".")
                if alias_name_split[-1] == generic_name:
                    # good match
                    lookup_res: SubEnvLookupResult = body_env[alias_name]
                    if lookup_res.must_found:
                        return lookup_res.found_entities[0][1]
        return return_type
    elif isinstance(return_type, ConstructorType):
        paras_type = []
        if return_type.class_ent.longname.longname == "typing.Self":
            return InstanceType(callee.parent_class)
        new_type = return_type.class_ent.direct_type()  # Union, Optional
        for t in return_type.paras:
            paras_type.append(resolve_typeshed_return(t, body_env, callee, signature))
        new_type.paras = paras_type
        return new_type
    else:
        return return_type


def resolve_builtins_generic(class_attrs, ent_type):
    before = class_attrs
    class_attrs = class_attrs[0] if len(class_attrs) == 1 else class_attrs
    if isinstance(class_attrs, Function):
        func = class_attrs

        if isinstance(ent_type, InstanceType) and ent_type.class_ent.longname.longname == "builtins.dict":
            assert isinstance(ent_type, DictType)
            body_env = func.get_scope_env()
            bindings: Bindings = []
            parent_class: Class = func.parent_class
            for alias_name in parent_class.alias_set:  # typing.Mapping
                if alias_name == "typing.Mapping._K":
                    bindings.append((alias_name, [(get_anonymous_ent(), ent_type.key)]))
                elif alias_name == "typing.Mapping._V":
                    bindings.append((alias_name, [(get_anonymous_ent(), ent_type.value)]))
            body_env.add_continuous(bindings)

        if isinstance(func, Function) and isinstance(func.type, MethodType):
            for signature in func.signatures:
                self_param = signature.get_posonlyargs(0)  # self
                assert isinstance(self_param, Parameter)
                for alias in self_param.alias_set:
                    body_env = func.get_scope_env()
                    bindings: Bindings = []
                    bindings.append((alias, [(get_anonymous_ent(), ent_type)]))
                    body_env.add_continuous(bindings)

    class_attrs = before
