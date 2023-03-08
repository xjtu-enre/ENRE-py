import ast
import typing as ty
from dataclasses import dataclass
from pathlib import Path

from enre.analysis.analyze_expr import ExprAnalyzer, InstanceType, ConstructorType, ModuleType, \
    UseContext, CallContext
# Avaler stand for Abstract evaluation
from enre.analysis.analyze_manager import AnalyzeManager, RootDB, ModuleDB
from enre.analysis.analyze_method import MethodVisitor
from enre.analysis.assign_target import dummy_iter_store
from enre.analysis.env import EntEnv, ScopeEnv, ParallelSubEnv, ContinuousSubEnv, OptionalSubEnv, BasicSubEnv
from enre.analysis.value_info import ValueInfo, PackageType
from enre.cfg.module_tree import SummaryBuilder, ModuleSummary, FunctionSummary, FuncConst
from enre.ent.EntKind import RefKind
from enre.ent.ent_finder import get_file_level_ent
from enre.ent.entity import Function, Module, Location, UnknownVar, Parameter, Class, ModuleAlias, \
    Entity, Alias, UnknownModule, LambdaFunction, LambdaParameter, Span, get_syntactic_span, \
    Package, PackageAlias, get_syntactic_head
from enre.ref.Ref import Ref

if ty.TYPE_CHECKING:
    from enre.analysis.env import Binding, Bindings

DefaultDefHeadLen = 4
DefaultClassHeadLen = 6
DefaultAsyncDefHeadLen = 8


@dataclass
class AnalyzeContext:
    env: EntEnv  # visible entities
    manager: AnalyzeManager
    package_db: RootDB  # entity database of the package
    current_db: ModuleDB  # entity database of current package
    coordinate: ty.Tuple[int, int]
    is_generator_expr: bool


class Analyzer:
    def __init__(self, rel_path: Path, manager: AnalyzeManager):
        module_ent = manager.root_db.get_module_db_of_path(rel_path).module_ent
        self.manager = manager
        self.module = module_ent
        self.global_env: ty.List  # type: ignore
        # placeholder for builtin function bindings
        self.package_db: "RootDB" = manager.root_db
        self.current_db: "ModuleDB" = manager \
            .root_db \
            .get_module_db_of_path(rel_path)
        self.all_summary: ty.List[ModuleSummary] = []

    def analyze(self, stmt: ast.AST, env: EntEnv) -> None:
        """Visit a node."""
        method = 'analyze_' + stmt.__class__.__name__
        default_avaler = self.get_default_avaler(env)
        if isinstance(stmt, ast.expr):
            default_avaler.aval(stmt)
            return
        if stmt in self.current_db.analyzed_set:
            return
        visitor = getattr(self, method, self.generic_analyze)
        visitor(stmt, env)
        self.current_db.analyzed_set.add(stmt)

    def generic_analyze(self, stmt: ast.AST, env: EntEnv) -> None:
        """Called if no explicit visitor function exists for a node."""
        default_avaler = self.get_default_avaler(env)
        for field, value in ast.iter_fields(stmt):
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, ast.expr):
                        default_avaler.aval(item)
                    elif isinstance(item, ast.AST):
                        self.analyze(item, env)
            elif isinstance(value, ast.AST):
                self.analyze(value, env)

    def analyze_function(self, name: str, args: ast.arguments, body: ty.List[ast.stmt], span: Span,
                         decorators: ty.List[ast.expr], env: EntEnv) -> Function:
        in_class_env = isinstance(env.get_ctx(), Class)
        fun_code_span = span
        now_scope = env.get_scope().get_location()
        new_scope = now_scope.append(name, fun_code_span, None)
        func_ent = Function(new_scope.to_longname(), new_scope)
        func_name = name
        parent_builder = env.get_scope().get_builder()
        # add function entity to dependency database
        self.current_db.add_ent(func_ent)
        # add reference of current contest to the function entity
        current_ctx = env.get_ctx()
        current_ctx.add_ref(Ref(RefKind.DefineKind, func_ent, span.start_line, span.start_col, False, None))
        # create a function summary
        fun_summary = self.manager.create_function_summary(func_ent)
        env.get_scope().get_builder().add_child(fun_summary)
        # and corresponding summary builder
        builder = SummaryBuilder(fun_summary)
        # add function entity to the current environment
        new_binding: "Bindings" = [(func_name, [(func_ent, ValueInfo.get_any())])]
        env.get_scope().add_continuous(new_binding)
        # create the scope environment corresponding to the function
        body_env = ScopeEnv(ctx_ent=func_ent, location=new_scope, builder=builder)
        # add function entity to the scope environment corresponding to the function while it's not a class method
        if not isinstance(current_ctx, Class):
            body_env.add_continuous(new_binding)
        # add parameters to the scope environment
        process_parameters(args, body_env, env, self.manager, self.package_db, self.current_db, func_ent, fun_summary,
                           env.get_class_ctx())
        for decorator in decorators:
            avaler = ExprAnalyzer(self.manager, self.package_db, self.current_db, None, CallContext(),
                                  env.get_scope().get_builder(), env)
            decorator_stores, _ = avaler.aval(decorator)
            parent_builder.add_invoke(decorator_stores, [[FuncConst(func_ent)]], [], decorator)
        hook_scope = env.get_scope(1) if in_class_env else env.get_scope()
        hook_scope.add_hook(body, body_env)
        return func_ent

    def analyze_FunctionDef(self, def_stmt: ast.FunctionDef, env: EntEnv) -> None:
        func_span = get_syntactic_head(def_stmt)
        func_span.offset(DefaultDefHeadLen)
        func_ent = self.analyze_function(def_stmt.name, def_stmt.args, def_stmt.body, func_span,
                                         def_stmt.decorator_list, env)

        if def_stmt.returns is not None:
            process_annotation(func_ent, self.manager, self.package_db, self.current_db, def_stmt.returns, env)
        self.set_method_info(def_stmt, func_ent)

    def analyze_AsyncFunctionDef(self, def_stmt: ast.AsyncFunctionDef, env: EntEnv) -> None:
        func_span = get_syntactic_head(def_stmt)
        func_span.offset(DefaultAsyncDefHeadLen)
        func_ent = self.analyze_function(def_stmt.name, def_stmt.args, def_stmt.body, func_span,
                                         def_stmt.decorator_list, env)
        if def_stmt.returns is not None:
            process_annotation(func_ent, self.manager, self.package_db, self.current_db, def_stmt.returns, env)

    def set_method_info(self, def_stmt: ast.FunctionDef, func_ent: Function) -> None:
        method_visitor = MethodVisitor()
        method_visitor.visit(def_stmt)
        func_ent.abstract_kind = method_visitor.abstract_kind
        func_ent.static_kind = method_visitor.static_kind
        func_ent.readonly_property_name = method_visitor.readonly_property_name

    def analyze_ClassDef(self, class_stmt: ast.ClassDef, env: EntEnv) -> None:
        avaler = self.get_default_avaler(env)
        now_location = env.get_scope().get_location()
        class_code_span = get_syntactic_head(class_stmt)
        class_code_span.offset(DefaultClassHeadLen)
        new_scope = now_location.append(class_stmt.name, class_code_span, None)
        class_ent = Class(new_scope.to_longname(), new_scope)
        class_name = class_stmt.name
        self.current_db.add_ent(class_ent)
        env.get_ctx().add_ref(Ref(RefKind.DefineKind, class_ent, class_stmt.lineno, class_stmt.col_offset, False, None))
        bases = []
        for base_expr in class_stmt.bases:
            store_ables, avalue = avaler.aval(base_expr)
            bases.append(store_ables)
            for base_ent, ent_type in avalue:
                if isinstance(ent_type, ConstructorType):
                    class_ent.add_ref(Ref(RefKind.InheritKind, base_ent, class_stmt.lineno,
                                          class_stmt.col_offset, False, base_expr))
                else:
                    class_ent.add_ref(Ref(RefKind.InheritKind, base_ent, class_stmt.lineno,
                                          class_stmt.col_offset, False, base_expr))
                    # todo: handle unknown class
        parent_builder = env.get_scope().get_builder()
        parent_builder.add_inherit(class_ent, bases)
        # add class to current environment
        new_binding: Bindings = [(class_name, [(class_ent, ConstructorType(class_ent))])]
        env.get_scope().add_continuous(new_binding)
        class_summary = self.manager.create_class_summary(class_ent)
        parent_builder.add_child(class_summary)
        builder = SummaryBuilder(class_summary)
        body_env = ScopeEnv(ctx_ent=class_ent, location=new_scope, class_ctx=class_ent, builder=builder)
        body_env.add_continuous(new_binding)
        # todo: bugfix, the environment should be same as the environment of class
        env.add_scope(body_env)

        self.analyze_top_stmts(class_stmt.body, builder, env)
        env.pop_scope()
        # env.get_scope().add_hook(class_stmt.body, body_env)
        # we can't use this solution because after class definition, the stmts after class definition should be able to
        # known the class's attribute

    def analyze_If(self, if_stmt: ast.If, env: EntEnv) -> None:
        in_len = len(env.get_scope())
        avaler = self.get_default_avaler(env)
        avaler.aval(if_stmt.test)
        before = len(env.get_scope())
        env.add_sub_env(BasicSubEnv())
        self.analyze_stmts(if_stmt.body, env)
        body_env = env.pop_sub_env()
        after = len(env.get_scope())
        assert before == after
        for stmt in if_stmt.orelse:
            env.add_sub_env(BasicSubEnv())
            self.analyze(stmt, env)
            branch_env = env.pop_sub_env()
            body_env = ParallelSubEnv(body_env, branch_env)
        if not if_stmt.orelse:
            body_env = ParallelSubEnv(body_env, BasicSubEnv())
        forward_env = env.pop_sub_env()
        env.add_sub_env(ContinuousSubEnv(forward_env, body_env))
        out_len = len(env.get_scope())
        # print(f"in length: {in_len} out length: {out_len}")
        assert (in_len == out_len)

    def analyze_For(self, for_stmt: ast.For, env: EntEnv) -> None:
        from enre.analysis.assign_target import unpack_semantic, dummy_iter
        iterable_store, iterable = self.get_default_avaler(env).aval(for_stmt.iter)
        iter_value = dummy_iter(iterable)
        target_expr = for_stmt.target
        iter_store = dummy_iter_store(iterable_store, env.get_scope().get_builder(), for_stmt.iter)
        target_lineno = target_expr.lineno
        target_col_offset = target_expr.col_offset
        unpack_semantic(target_expr, iter_value, iter_store, env.get_scope().get_builder(),
                        AnalyzeContext(env, self.manager, self.package_db, self.current_db,
                                       (target_lineno, target_col_offset), True))

        # self._avaler.aval(for_stmt.target, env)
        # self._avaler.aval(for_stmt.iter, env)
        # todo: verify it's two re evaluation
        env.add_sub_env(BasicSubEnv())
        self.analyze_stmts(for_stmt.body, env)
        sub_env = env.pop_sub_env()
        optional_sub_env = OptionalSubEnv(sub_env)
        continuous_sub_env = ContinuousSubEnv(env.pop_sub_env(), optional_sub_env)
        env.add_sub_env(continuous_sub_env)

    def analyze_Assign(self, assign_stmt: ast.Assign, env: EntEnv) -> None:
        target_exprs: ty.List[ast.expr] = assign_stmt.targets
        rvalue_expr = assign_stmt.value
        self.process_assign_helper(rvalue_expr, target_exprs, env, None)

    def analyze_AugAssign(self, aug_stmt: ast.AugAssign, env: EntEnv) -> None:
        target_expr = aug_stmt.target
        rvalue_expr = aug_stmt.value
        if rvalue_expr is not None:
            self.process_assign_helper(rvalue_expr, [target_expr], env, None)
        else:
            self.declare_semantic(target_expr, env)

    def analyze_AnnAssign(self, ann_stmt: ast.AnnAssign, env: EntEnv) -> None:
        target_expr = ann_stmt.target
        rvalue_expr = ann_stmt.value
        self.process_assign_helper(rvalue_expr, [target_expr], env, ann_stmt.annotation)

    def analyze_Expr(self, expr_stmt: ast.Expr, env: EntEnv) -> None:
        avaler = self.get_default_avaler(env)
        avaler.aval(expr_stmt.value)

    def process_assign_helper(self, rvalue_expr: ty.Optional[ast.expr], target_exprs: ty.List[ast.expr],
                              env: EntEnv, annotation: ty.Optional[ast.expr]) -> None:
        from enre.analysis.assign_target import assign2target
        frame_entities: ty.List[ty.Tuple[Entity, ValueInfo]]
        lhs_ents: ty.Set[Entity] = set()
        for target_expr in target_exprs:
            target_lineno = target_expr.lineno
            target_col_offset = target_expr.col_offset
            sub_lhs_ents = assign2target(target_expr, rvalue_expr, env.get_scope().get_builder(),
                                         AnalyzeContext(env,
                                                        self.manager,
                                                        self.package_db,
                                                        self.current_db,
                                                        (target_lineno, target_col_offset),
                                                        False))
            lhs_ents.update(sub_lhs_ents)
        if annotation is not None:
            annotation_avaler = ExprAnalyzer(self.manager, self.package_db, self.current_db, lhs_ents,
                                             UseContext(), env.get_scope().get_builder(), env)
            annotation_avaler.aval(annotation)

    def analyze_Import(self, import_stmt: ast.Import, env: EntEnv) -> None:
        def create_proper_alias(file_ent: ty.Union[Module, Package], location: Location) -> Entity:
            if isinstance(file_ent, Module):
                return ModuleAlias(file_ent, location)
            else:
                return PackageAlias(file_ent, location)

        for module_alias in import_stmt.names:
            path_ent, bound_ent = self.manager.import_module(self.module, module_alias.name, import_stmt.lineno,
                                                             import_stmt.col_offset, False)
            bound_name = bound_ent.longname.name
            if module_alias.asname is None:
                module_binding: Bindings = [(bound_name, [(bound_ent, PackageType(bound_ent.names))])]
                env.get_scope().add_continuous(module_binding)
            else:
                alias_location = env.get_ctx().location.append(module_alias.asname, Span.get_nil(), None)
                alias_ent = create_proper_alias(path_ent, alias_location)
                self.current_db.add_ent(alias_ent)
                alias_binding: Bindings = [(module_alias.asname, [(alias_ent, ModuleType(path_ent.names))])]
                env.get_scope().add_continuous(alias_binding)
            env.get_ctx().add_ref(Ref(RefKind.ImportKind, path_ent, import_stmt.lineno,
                                      import_stmt.col_offset, False, None))

    def analyze_ImportFrom(self, import_stmt: ast.ImportFrom, env: EntEnv) -> None:
        module_identifier = import_stmt.module
        if module_identifier is None:
            print("implicit import not implemented yet")
            return
        file_ent, bound_ent = self.manager.import_module(self.module, module_identifier, import_stmt.lineno,
                                                         import_stmt.col_offset, True)
        current_ctx = env.get_ctx()
        new_bindings: "Bindings"
        if not isinstance(file_ent, UnknownModule):
            # if the imported module can found in package
            frame_entities: ty.List[ty.Tuple[Entity, ValueInfo]]
            new_bindings = []
            for alias in import_stmt.names:
                name = alias.name
                as_name = alias.asname
                imported_ents = get_file_level_ent(file_ent, name)
                import_binding: Binding
                for e in imported_ents:
                    current_ctx.add_ref(
                        Ref(RefKind.ImportKind, e, import_stmt.lineno, import_stmt.col_offset, False, None))
                if name == "*":
                    for ent in imported_ents:
                        new_bindings.append((ent.longname.name, [(ent, ent.direct_type())]))
                else:
                    if as_name is not None:
                        location = env.get_scope().get_location().append(as_name, Span.get_nil(), None)
                        alias_ent = Alias(location.to_longname(), location, imported_ents)
                        env.get_ctx().add_ref(Ref(RefKind.DefineKind, alias_ent, import_stmt.lineno,
                                                  import_stmt.col_offset, False, None))
                        self.current_db.add_ent(alias_ent)
                        import_binding = as_name, [(alias_ent, alias_ent.direct_type())]
                    else:
                        for ent in imported_ents:
                            env.get_ctx().add_ref(Ref(RefKind.ContainKind, ent, import_stmt.lineno,
                                                      import_stmt.col_offset, False, None))
                        import_binding = name, [(ent, ent.direct_type()) for ent in imported_ents]
                    new_bindings.append(import_binding)
            env.get_scope().add_continuous(new_bindings)
        else:
            # importing entities belong to a unknown module
            self.package_db.add_ent_global(file_ent)
            frame_entities = []
            new_bindings = []
            for alias in import_stmt.names:
                alias_code_span = get_syntactic_span(alias)
                location = file_ent.location.append(alias.name, alias_code_span, None)
                unknown_var = UnknownVar.get_unknown_var(location.to_longname().name)
                self.package_db.add_ent_global(unknown_var)
                file_ent.add_ref(Ref(RefKind.DefineKind, unknown_var, 0, 0, False, None))
                if alias.asname is not None:
                    as_location = env.get_scope().get_location().append(alias.asname, alias_code_span, None)
                    alias_ent = Alias(as_location.to_longname(), location, [unknown_var])
                    self.current_db.add_ent(alias_ent)
                    new_bindings.append((alias.asname, [(alias_ent, alias_ent.direct_type())]))
                else:
                    new_bindings.append((alias.name, [(unknown_var, ValueInfo.get_any())]))
            env.get_scope().add_continuous(new_bindings)

    def analyze_With(self, with_stmt: ast.With, env: EntEnv) -> None:
        from enre.analysis.assign_target import unpack_semantic
        for with_item in with_stmt.items:
            context_expr = with_item.context_expr
            optional_var = with_item.optional_vars
            avaler = ExprAnalyzer(self.manager, self.package_db, self.current_db, None, UseContext(),
                                  env.get_scope().get_builder(), env)
            with_store_ables, with_value = avaler.aval(context_expr)
            if optional_var is not None:
                target_lineno = optional_var.lineno
                target_col_offset = optional_var.col_offset
                unpack_semantic(optional_var, with_value, with_store_ables,
                                env.get_scope().get_builder(),
                                AnalyzeContext(env, self.manager, self.package_db, self.current_db,
                                               (target_lineno, target_col_offset), False))
        self.analyze_stmts(with_stmt.body, env)

    def analyze_Try(self, try_stmt: ast.Try, env: EntEnv) -> None:
        from enre.analysis.error_handler import handler_semantic
        env.add_sub_env(BasicSubEnv())
        self.analyze_stmts(try_stmt.body, env)
        try_body_env = env.pop_sub_env()

        for handler in try_stmt.handlers:
            env.add_sub_env(BasicSubEnv())
            err_constructor = handler.type

            if err_constructor is not None:
                target_lineno = handler.lineno
                target_col_offset = handler.col_offset
                handler_semantic(handler.name, ast.Expr(err_constructor),
                                 AnalyzeContext(env, self.manager, self.package_db, self.current_db,
                                                (target_lineno, target_col_offset), False))
            self.analyze_stmts(handler.body, env)
            handler_env = env.pop_sub_env()
            try_body_env = ParallelSubEnv(try_body_env, handler_env)

        env.add_sub_env(BasicSubEnv())
        self.analyze_stmts(try_stmt.orelse, env)
        orelse_body_env = env.pop_sub_env()

        env.add_sub_env(BasicSubEnv())
        self.analyze_stmts(try_stmt.finalbody, env)
        finally_body_env = env.pop_sub_env()

        try_env = ParallelSubEnv(try_body_env, ParallelSubEnv(orelse_body_env, finally_body_env))
        forward_env = env.pop_sub_env()
        env.add_sub_env(ContinuousSubEnv(forward_env, try_env))

    # entry of analysis of a module
    def analyze_top_stmts(self, stmts: ty.List[ast.stmt], builder: SummaryBuilder,
                          env: ty.Optional[EntEnv]) -> None:
        if env is None:
            env = EntEnv(ScopeEnv(ctx_ent=self.module, location=Location(), builder=builder))

        for stmt in stmts:
            self.analyze(stmt, env)

        for hook in env.get_scope().get_hooks():
            stmts = hook.stmts
            scope_env = hook.scope_env
            before = len(env.get_scope())
            env.add_scope(scope_env)
            self.analyze_top_stmts(stmts, scope_env.get_builder(), env)
            env.pop_scope()
            after = len(env.get_scope())
            assert (before == after)

    def analyze_Return(self, return_stmt: ast.Return, env: EntEnv) -> None:
        avaler = self.get_default_avaler(env)
        builder = env.get_scope().get_builder()
        value = return_stmt.value
        if value is not None:
            return_store_ables, _ = avaler.aval(value)
            builder.add_return(return_store_ables, value)

    def analyze_stmts(self, stmts: ty.List[ast.stmt], env: EntEnv) -> None:
        for stmt in stmts:
            self.analyze(stmt, env)

    def declare_semantic(self, target_expr: ast.expr, env: EntEnv) -> None:
        raise NotImplementedError("not implemented yet")

    def get_default_avaler(self, env: EntEnv) -> ExprAnalyzer:
        return ExprAnalyzer(self.manager, self.package_db, self.current_db, None, UseContext(),
                            env.get_scope().get_builder(), env)


def process_annotation(typing_ent: Entity, manager: AnalyzeManager, package_db: RootDB, current_db: ModuleDB,
                       annotation: ty.Optional[ast.expr], env: EntEnv) -> None:
    if annotation is not None:
        avaler = ExprAnalyzer(manager, package_db, current_db, [typing_ent],
                              UseContext(), env.get_scope().get_builder(), env)
        avaler.aval(annotation)


ArgKind = int
PArg = 0
VarArg = 1
KWArg = 2


def process_parameters(args: ast.arguments, scope: ScopeEnv, env: EntEnv, manager: AnalyzeManager, package_db: RootDB,
                       current_db: ModuleDB, func_ent: Entity, summary: FunctionSummary,
                       class_ctx: ty.Optional[Class] = None) -> None:
    location_base = scope.get_location()
    ctx_fun = scope.get_ctx()
    para_constructor = LambdaParameter if isinstance(scope.get_ctx(), LambdaFunction) else Parameter

    def process_helper(a: ast.arg, ent_type: ValueInfo, bindings: "Bindings", arg_kind: ArgKind) -> None:
        para_code_span = get_syntactic_span(a)
        parameter_loc = location_base.append(a.arg, para_code_span, current_db.module_path)
        parameter_ent = para_constructor(func_ent, parameter_loc.to_longname(), parameter_loc)
        current_db.add_ent(parameter_ent)
        new_coming_ent: Entity = parameter_ent
        bindings.append((a.arg, [(new_coming_ent, ent_type)]))
        if arg_kind == PArg:
            summary.positional_para_list.append(a.arg)
        elif arg_kind == VarArg:
            summary.var_para = a.arg
        elif arg_kind == KWArg:
            summary.kwarg = a.arg
        else:
            assert False, "never reach"
        ctx_fun.add_ref(
            Ref(RefKind.DefineKind, parameter_ent, a.lineno, a.col_offset, a.annotation is not None, None))
        process_annotation(parameter_ent, manager, package_db, current_db, a.annotation, env)

    args_binding: "Bindings" = []

    for arg in args.posonlyargs:
        process_helper(arg, ValueInfo.get_any(), args_binding, PArg)

    if len(args.args) >= 1:
        first_arg = args.args[0].arg
        if first_arg == "self":
            if class_ctx is not None:
                class_type: ValueInfo = InstanceType(class_ctx)
            else:
                class_type = ValueInfo.get_any()
            process_helper(args.args[0], class_type, args_binding, PArg)
        elif first_arg == "cls":
            if class_ctx is not None:
                constructor_type: ValueInfo = ConstructorType(class_ctx)
            else:
                constructor_type = ValueInfo.get_any()
            process_helper(args.args[0], constructor_type, args_binding, PArg)
        else:
            process_helper(args.args[0], ValueInfo.get_any(), args_binding, PArg)

    for arg in args.args[1:]:
        process_helper(arg, ValueInfo.get_any(), args_binding, PArg)
    if args.vararg is not None:
        process_helper(args.vararg, ValueInfo.get_any(), args_binding, VarArg)
    for arg in args.kwonlyargs:
        process_helper(arg, ValueInfo.get_any(), args_binding, KWArg)
    if args.kwarg is not None:
        process_helper(args.kwarg, ValueInfo.get_any(), args_binding, KWArg)

    scope.add_continuous(args_binding)
