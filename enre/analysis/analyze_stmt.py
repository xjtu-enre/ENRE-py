import ast
import typing as ty
from dataclasses import dataclass
from pathlib import Path

from enre.analysis.analyze_expr import ExprAnalyzer, InstanceType, ConstructorType, ModuleType, \
    UseContext, CallContext, resolve_typeshed_return
from enre.analysis.analyze_manager import AnalyzeManager, RootDB, ModuleDB
from enre.analysis.analyze_method import MethodVisitor
from enre.analysis.assign_target import dummy_iter_store
from enre.analysis.env import EntEnv, ScopeEnv, ContinuousSubEnv, BasicSubEnv
from enre.analysis.value_info import ValueInfo, FunctionType, AnyType, MethodType, UnknownVarType
from enre.cfg.module_tree import SummaryBuilder, ModuleSummary, FunctionSummary
from enre.ent.EntKind import RefKind
from enre.ent.ent_finder import get_file_level_ent
from enre.ent.entity import Function, Module, Location, Parameter, Class, ModuleAlias, \
    Entity, Alias, LambdaFunction, LambdaParameter, Span, get_syntactic_span, \
    Package, PackageAlias, get_syntactic_head, Anonymous, Signature, _Nil_Span
from enre.ref.Ref import Ref

from enre.util.logger import Logging

if ty.TYPE_CHECKING:
    from enre.analysis.env import Binding, Bindings

DefaultAsHeadLen = 4
DefaultSelfHeadLen = 4
DefaultDefHeadLen = 4
DefaultClassHeadLen = 6
DefaultAsyncDefHeadLen = 8

log = Logging().getLogger(__name__)


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
        module_ent = manager.root_db[rel_path].module_ent
        self.manager = manager
        self.module = module_ent
        self.global_env: ty.List  # type: ignore
        # placeholder for builtin function bindings
        self.package_db: "RootDB" = manager.root_db
        self.current_db: "ModuleDB" = manager.root_db[rel_path]
        self.all_summary: ty.List[ModuleSummary] = []
        self.analyzing_typeshed = False

    def analyze(self, stmt: ast.AST, env: EntEnv) -> None:
        """Visit a node."""
        method = 'analyze_' + stmt.__class__.__name__
        default_avaler = self.get_default_avaler(env)
        if isinstance(stmt, ast.expr):
            default_avaler.aval(stmt)
            return
        # if stmt in self.current_db.analyzed_set:
        #     return
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
        # find function name in env if @overload cases
        lookup_res = env[name]
        func_ent = None
        current_ctx = env.get_ctx()
        if lookup_res.must_found:
            entities = lookup_res.found_entities
            for ent in entities:
                if isinstance(ent[0], Function):
                    # function overload
                    func_ent = ent[0]
                    break
        if not func_ent:  # new to function
            in_class_env = isinstance(env.get_ctx(), Class)
            fun_code_span = span
            now_scope = env.get_scope().get_location()
            new_scope = now_scope.append(name, fun_code_span, None)
            func_ent = Function(new_scope.to_longname(), new_scope)

            # if func_ent.longname.longname == "typing.Mapping.get":
            #     print("here")

            if self.manager.analyzing_typing_builtins:
                func_ent.typeshed_func = True

            func_ent.current_db = self.current_db
            func_name = name

            # add function entity to dependency database
            self.current_db.add_ent(func_ent)
            if not self.analyzing_typeshed and not self.manager.analyzing_typing_builtins:
                self.manager.func_uncalled_set.add(func_ent)
            else:
                func_ent.typeshed_func = True
            # add reference of current contest to the function entity
            current_ctx.add_ref(Ref(RefKind.DefineKind, func_ent, span.start_line, span.start_col, False, None))
            func_ent.add_ref(Ref(RefKind.ChildOfKind, current_ctx, -1, -1, False, None))

            if isinstance(current_ctx, Class):
                func_ent.parent_class = current_ctx

            exported = False if func_name.startswith("__") and not func_name.endswith("__") \
                                and not isinstance(current_ctx, Module) else current_ctx.exported
            func_ent.exported = exported
            # create a function summary
            fun_summary = self.manager.create_function_summary(func_ent)
            func_ent.summary = fun_summary
            env.get_scope().get_builder().add_child(fun_summary)
            # and corresponding summary builder
            builder = SummaryBuilder(fun_summary)
            # add function entity to the current environment
            direct_type = FunctionType(func_ent) if not isinstance(current_ctx, Class) else MethodType(func_ent)
            new_binding: "Bindings" = [(func_name, [(func_ent, direct_type)])]
            func_ent.set_direct_type(direct_type)
            env.get_scope().add_continuous(new_binding)
            # create the scope environment corresponding to the function
            body_env = ScopeEnv(ctx_ent=func_ent, location=new_scope, builder=builder)
            # add function entity to the scope environment corresponding to the function while it's not a class method
            if not isinstance(current_ctx, Class):
                body_env.add_continuous(new_binding)
            else:
                # Class method
                func_ent.set_method()
                # add override ref if possible
                process_override(func_name, func_ent, current_ctx, span)

            # add parameters to the scope environment
            hook_scope = env.get_scope(1) if in_class_env else env.get_scope()
            hook_scope.add_hook(body, body_env)
            func_ent.set_body_env(env.get_env(), body_env, self.current_db.module_path)
        else:  # overload to function
            current_ctx.add_ref(Ref(RefKind.OverloadKind, func_ent, span.start_line, span.start_col, False, None))
        body_env = func_ent.get_scope_env()
        fun_summary = func_ent.summary
        # update body, we assume that the last overload function will overload former functions
        func_ent.set_body(body)

        process_parameters(args, body_env, env, self.manager, self.package_db, self.current_db, fun_summary,
                           env.get_class_ctx())
        # TODO: staticmethod
        for decorator in decorators:
            avaler = ExprAnalyzer(self.manager, self.package_db, self.current_db, None, CallContext(),
                                  env.get_scope().get_builder(), env)
            store_able, info = avaler.aval(decorator)
            if info and info[0]:
                decorator_ent = info[0][0]
                func_ent.decorators.append(decorator_ent)
                if decorator_ent.longname.longname == "typing.overload":
                    # we shouldn't call this overload signature
                    func_ent.signatures[-1].is_overload = True
                elif decorator_ent.longname.longname == "builtins.property":
                    func_ent.property = True  # call it directly


        # set callable signatures
        if not func_ent.signatures[-1].is_overload:
            func_ent.callable_signature = func_ent.signatures[-1]
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
        exported = False if isinstance(env.get_ctx(), Function) else env.get_ctx().exported
        class_ent.exported = exported


        env.get_ctx().add_ref(Ref(RefKind.DefineKind, class_ent, class_code_span.start_line, class_code_span.start_col, False, None))
        class_ent.add_ref(Ref(RefKind.ChildOfKind, env.get_ctx(), -1, -1, False, None))
        if self.analyzing_typeshed:
            class_ent.typeshed_class = True
            class_ent.typeshed_module_dummy_path = self.current_db.module_dummy_path

        bases = []
        bases_storables = []
        bases_index = 0
        signature = Signature(class_name, is_func=False)
        for base_expr in class_stmt.bases:
            store_ables, avalue = avaler.aval(base_expr)
            name = f"({bases_index})"
            bases_index += 1

            base_loc = new_scope.append(name, get_syntactic_span(base_expr), None)
            parameter_ent = Parameter(base_loc.to_longname(), base_loc)
            parameter_ent.add_type(avalue[0][1])
            bases.append(avalue[0][1])
            self.current_db.add_ent(parameter_ent)
            signature.append_posonlyargs(parameter_ent)

            bases_storables.append(store_ables)

            for base_ent, ent_type in avalue:
                if isinstance(ent_type, ConstructorType):
                    class_ent.add_ref(Ref(RefKind.InheritKind, ent_type.class_ent, base_expr.lineno,
                                          base_expr.col_offset, False, base_expr))
                    class_ent.add_ref(Ref(RefKind.ChildOfKind, ent_type.class_ent, -1, -1, False, None))
                    for child in ent_type.class_ent.children:
                        if child != class_ent:
                            child.add_ref(Ref(RefKind.ChildOfKind, class_ent, -1, -1, False, None))

                    # TODO: add ParameteredClass alias_map to this class
                    if ent_type.class_ent.longname.longname == "typing.Generic":
                        for para in ent_type.paras:
                            assert isinstance(para, InstanceType)

                            TypeVar_name = para.paras[0].paras[0].value
                            generic_name = class_ent.location.append(TypeVar_name, _Nil_Span, None).to_longname().longname
                            class_ent.alias_self_set.add(generic_name)
                    else:
                        class_ent.alias_set = class_ent.alias_self_set.union(ent_type.class_ent.alias_set)
                else:
                    class_ent.add_ref(Ref(RefKind.InheritKind, base_ent, base_expr.lineno,
                                          base_expr.col_offset, False, base_expr))
                    # todo: handle unknown class

        class_ent.signatures.append(signature)
        class_ent.bases = bases
        env.get_scope().get_builder().add_inherit(class_ent, bases_storables)
        # add class to current environment
        constructor_type = ConstructorType(class_ent)
        class_ent.type = constructor_type
        new_binding: Bindings = [(class_name, [(class_ent, class_ent.type)])]
        env.get_scope().add_continuous(new_binding)
        class_summary = self.manager.create_class_summary(class_ent)
        builder = SummaryBuilder(class_summary)
        body_env = ScopeEnv(ctx_ent=class_ent, location=new_scope, class_ctx=class_ent, builder=builder)
        body_env.add_continuous(new_binding)
        # todo: bugfix, the environment should be same as the environment of class
        class_ent.set_body_env(body_env)
        env.add_scope(body_env)
        class_ent.env = env
        if not class_ent.typeshed_class:
            self.analyze_top_stmts(class_stmt.body, builder, env)
        env.pop_scope()
        # env.get_scope().add_hook(class_stmt.body, body_env)
        # we can't use this solution because after class definition, the stmts after class definition should be able to
        # know the class's attribute

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
        # for stmt in if_stmt.orelse:
        #     env.add_sub_env(BasicSubEnv())
        #     self.analyze(stmt, env)
        #     branch_env = env.pop_sub_env()
        #     body_env = ParallelSubEnv(body_env, branch_env)
        for stmt in if_stmt.orelse:
            env.add_sub_env(body_env)
            self.analyze(stmt, env)
            body_env = env.pop_sub_env()
        forward_env = env.pop_sub_env()
        env.add_sub_env(ContinuousSubEnv(forward_env, body_env))
        out_len = len(env.get_scope())
        # print(f"in length: {in_len} out length: {out_len}")
        assert (in_len == out_len)

    def analyze_For(self, for_stmt: ast.For, env: EntEnv) -> None:
        from enre.analysis.assign_target import unpack_semantic, dummy_iter
        iterable_store, iterable = self.get_default_avaler(env).aval(for_stmt.iter)
        iter_value = dummy_iter(iterable)
        iter_store = dummy_iter_store(iterable_store, env.get_scope().get_builder(), for_stmt.iter)
        target_expr = for_stmt.target
        target_lineno = target_expr.lineno
        target_col_offset = target_expr.col_offset

        # Assign iter to target
        unpack_semantic(target_expr, iter_value, iter_store, env.get_scope().get_builder(),
                        AnalyzeContext(env, self.manager, self.package_db, self.current_db,
                                       (target_lineno, target_col_offset), True))

        # self._avaler.aval(for_stmt.target, env)
        # self._avaler.aval(for_stmt.iter, env)
        # todo: verify it's two re evaluation
        env.add_sub_env(BasicSubEnv())
        self.analyze_stmts(for_stmt.body, env)
        sub_env = env.pop_sub_env()
        # optional_sub_env = OptionalSubEnv(sub_env)
        # continuous_sub_env = ContinuousSubEnv(env.pop_sub_env(), optional_sub_env)
        continuous_sub_env = ContinuousSubEnv(env.pop_sub_env(), sub_env)
        env.add_sub_env(continuous_sub_env)
        # todo: loop the for statement until stabilized

        # todo: For.orelse need to visit

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
            annotation_store_ables, annotation_values = annotation_avaler.aval(annotation)
            for lhs_ent in lhs_ents:
                # print(lhs_ent)
                for annotation_value in annotation_values:
                    lhs_ent.add_type(annotation_value[1])
                    # print(lhs_ent.get_type_list())

    def analyze_Import(self, import_stmt: ast.Import, env: EntEnv) -> None:  # import xxx
        def create_proper_alias(file_ent: ty.Union[Module, Package], location: Location) -> Entity:
            if isinstance(file_ent, Module):
                return ModuleAlias(file_ent, location)
            else:
                return PackageAlias(file_ent, location)

        for module_alias in import_stmt.names:
            path_ent, bound_ent = self.manager.import_module(self.module, module_alias.name, import_stmt.lineno,
                                                             import_stmt.col_offset, True)
            # typing.Ty
            bound_name = bound_ent.longname.name
            if module_alias.asname is None:
                module_binding: Bindings = [(bound_name, [(path_ent, ModuleType(path_ent.names))])]
                env.get_scope().add_continuous(module_binding)
            else:
                span = get_syntactic_span(module_alias)
                alias_location = env.get_ctx().location.append(module_alias.asname, span, None)
                alias_ent = create_proper_alias(path_ent, alias_location)
                self.current_db.add_ent(alias_ent)
                alias_binding: Bindings = [(module_alias.asname, [(alias_ent, ModuleType(path_ent.names))])]
                env.get_scope().add_continuous(alias_binding)
            module_alias_lineno = module_alias.lineno
            module_alias_colno = module_alias.col_offset
            env.get_ctx().add_ref(Ref(RefKind.ImportKind, path_ent, module_alias_lineno,
                                      module_alias_colno, False, None))

    def analyze_ImportFrom(self, import_stmt: ast.ImportFrom, env: EntEnv) -> None:  # from A import B
        # todo: import from statement
        if import_stmt.level == 1:
            def create_proper_alias(file_ent: ty.Union[Module, Package], location: Location) -> Entity:
                if isinstance(file_ent, Module):
                    return ModuleAlias(file_ent, location)
                else:
                    return PackageAlias(file_ent, location)

            module_id_prefix = None
            if import_stmt.module:
                module_id_prefix = import_stmt.module
                path_elems = module_id_prefix.split(".")
                rel_path = Path("/".join(path_elems) + ".py")
                from_path = self.module.module_path.parent
                real_path = self.manager.project_root.parent.joinpath(from_path).joinpath(rel_path)
                if real_path.exists():  # from module import Attrs
                    module_identifier = module_id_prefix
                    file_ent, bound_ent = self.manager.import_module(self.module, module_identifier, import_stmt.lineno,
                                                                     import_stmt.col_offset, True)
                    process_imports(import_stmt, env, self, file_ent)
                    return None
            # from path import module
            for module_alias in import_stmt.names:
                module_id = module_id_prefix + "." + module_alias.name if module_id_prefix else module_alias.name
                """
                check "module_id_prefix.py" exists or not?
                    exists --> import it

                    no exists --> import module_id_prefix + "." + module_alias.name
                """

                path_ent, bound_ent = self.manager.import_module(self.module, module_id, import_stmt.lineno,
                                                                 import_stmt.col_offset, True)
                bound_name = bound_ent.longname.name
                if module_alias.asname is None:
                    module_binding: Bindings = [(bound_name, [(bound_ent, ModuleType(bound_ent.names))])]
                    env.get_scope().add_continuous(module_binding)
                else:
                    alias_location = env.get_ctx().location.append(module_alias.asname, Span.get_nil(), None)
                    alias_ent = create_proper_alias(path_ent, alias_location)
                    self.current_db.add_ent(alias_ent)
                    alias_binding: Bindings = [(module_alias.asname, [(alias_ent, ModuleType(path_ent.names))])]
                    env.get_scope().add_continuous(alias_binding)
                module_alias_lineno = module_alias.lineno
                module_alias_colno = module_alias.col_offset
                env.get_ctx().add_ref(Ref(RefKind.ImportKind, path_ent, module_alias_lineno,
                                          module_alias_colno, False, None))
            return None

        module_identifier = import_stmt.module
        if module_identifier is None:
            log.warn("implicit import not implemented yet")
            return
        file_ent, bound_ent = self.manager.import_module(self.module, module_identifier, import_stmt.lineno,
                                                         import_stmt.col_offset, True)
        process_imports(import_stmt, env, self, file_ent)

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
        from enre.analysis.error_handler import handler_except_alias
        env.add_sub_env(BasicSubEnv())
        self.analyze_stmts(try_stmt.body, env)
        try_body_env = env.pop_sub_env()

        for handler in try_stmt.handlers:
            env.add_sub_env(try_body_env)
            err_constructor = handler.type

            if err_constructor is not None:
                target_lineno = handler.lineno
                target_col_offset = handler.col_offset
                handler_except_alias(handler.name, ast.Expr(err_constructor),
                                     AnalyzeContext(env, self.manager, self.package_db, self.current_db,
                                                    (target_lineno, target_col_offset), False))

            self.analyze_stmts(handler.body, env)
            env.pop_sub_env()

        env.add_sub_env(try_body_env)
        self.analyze_stmts(try_stmt.orelse, env)
        env.pop_sub_env()

        env.add_sub_env(try_body_env)
        self.analyze_stmts(try_stmt.finalbody, env)
        env.pop_sub_env()

        forward_env = env.pop_sub_env()
        env.add_sub_env(ContinuousSubEnv(forward_env, try_body_env))

    def analyze_Raise(self, raise_expr: ast.Raise, env: EntEnv) -> None:
        use_avaler = self.get_default_avaler(env)
        exc_store_ables, exc_info = use_avaler.aval(raise_expr.exc)
        if not isinstance(exc_info[0][0], Anonymous):
            exc_ent = exc_info[0][0]
            current_ctx = env.get_ctx()
            current_ctx.add_ref(Ref(RefKind.Raise, exc_ent, raise_expr.lineno, raise_expr.col_offset, False, None))

    # entry of analysis of a module
    def analyze_top_stmts(self, stmts: ty.List[ast.stmt], builder: SummaryBuilder,
                          env: ty.Optional[EntEnv]) -> None:
        if env is None:
            env = EntEnv(ScopeEnv(ctx_ent=self.module, location=Location(), builder=builder))

        for stmt in stmts:
            self.analyze(stmt, env)

    def analyze_Return(self, return_stmt: ast.Return, env: EntEnv) -> None:
        avaler = self.get_default_avaler(env)
        builder = env.get_scope().get_builder()
        value = return_stmt.value
        if value is not None:
            return_store_ables, return_abstract_value = avaler.aval(value)
            builder.add_return(return_store_ables, value)
            if isinstance(builder.mod, FunctionSummary):
                func = builder.mod.func
                if return_abstract_value:
                    ent_type = return_abstract_value[0][0].type
                    func.calling_stack[-1].set_return_type(ent_type)
                    func.callable_signature.set_return_type(ent_type)
                else:
                    func.calling_stack[-1].set_return_type(ValueInfo.get_any())
                    func.callable_signature.set_return_type(ValueInfo.get_any())

    def analyze_stmts(self, stmts: ty.List[ast.stmt], env: EntEnv) -> None:
        for stmt in stmts:
            self.analyze(stmt, env)

    def declare_semantic(self, target_expr: ast.expr, env: EntEnv) -> None:
        raise NotImplementedError("not implemented yet")

    def get_default_avaler(self, env: EntEnv) -> ExprAnalyzer:
        return ExprAnalyzer(self.manager, self.package_db, self.current_db, None, UseContext(),
                            env.get_scope().get_builder(), env)


def process_override(func_name, func_ent, current_ctx, span):
    assert isinstance(current_ctx, Class)
    for base in current_ctx.inherits:
        names = base.names
        for ent_name, ent_list in names.items():
            if ent_name == func_name:
                for ent in ent_list:
                    if isinstance(ent, Function):
                        func_ent.add_ref(Ref(RefKind.OverrideKind, ent, span.start_line, span.start_col, False, None))
                break


def process_imports(import_stmt: ast.ImportFrom, env: EntEnv, analyzer: Analyzer, file_ent: Module):
    current_ctx = env.get_ctx()
    new_bindings: "Bindings"
    # if not isinstance(file_ent, UnknownModule):
    # if the imported module can be found in package
    frame_entities: ty.List[ty.Tuple[Entity, ValueInfo]]
    new_bindings = []
    for alias in import_stmt.names:
        name = alias.name
        as_name = alias.asname

        imported_ents = get_file_level_ent(analyzer.manager, file_ent, name)  # name --> B
        # if not imported_ents and file_ent.is_stub():
        #     imported_ents = get_stub_file_level_ent(self.manager, file_ent, name)
        import_binding: Binding
        alias_span = get_syntactic_head(alias)
        for e in imported_ents:
            current_ctx.add_ref(
                Ref(RefKind.ImportKind, e, alias_span.start_line, alias_span.start_col, False, None))
        if as_name is not None:
            alias_span.offset(len(name))
            alias_span.head_offset(DefaultAsHeadLen)
            location = env.get_scope().get_location().append(as_name, alias_span, None)
            alias_ent = Alias(location.to_longname(), location, imported_ents)
            analyzer.current_db.add_ent(alias_ent)
            import_binding = as_name, [(alias_ent, alias_ent.direct_type())]
        else:
            import_binding = name, [(ent, ent.direct_type()) for ent in imported_ents]
        new_bindings.append(import_binding)
    env.get_scope().add_continuous(new_bindings)


def process_annotation(typing_ent: Entity, manager: AnalyzeManager, package_db: RootDB, current_db: ModuleDB,
                       annotation: ty.Optional[ast.expr], env: EntEnv) -> None:
    if annotation is not None:
        avaler = ExprAnalyzer(manager, package_db, current_db, [typing_ent],
                              UseContext(), env.get_scope().get_builder(), env)
        store_ables, abstract_value = avaler.aval(annotation)
        if isinstance(typing_ent, Function):
            # if typing_ent.longname.longname == "AnyStrTests.test_type_parameters.f":
            #     print("123")
            # typing_ent.signature.return_type = abstract_value[0][1]
            signature = typing_ent.signatures[-1]
            signature.set_return_type(abstract_value[0][1])
            if typing_ent.property:
                return_type = resolve_typeshed_return(typing_ent.callable_signature.return_type, typing_ent.get_scope_env(), typing_ent,
                                                      signature)
                env.get_scope().reset_binding_value(typing_ent.longname.name, return_type)
                typing_ent.type = return_type
        elif isinstance(typing_ent, Parameter):
            if isinstance(abstract_value[0], tuple):
                annotation_type = abstract_value[0][1]
                typing_ent.set_type(annotation_type)

                # TODO: add formal type to Parameter, generic name
                # get rid of Union, Option
                typing_ent.formal_type = annotation_type
                process_alias_map(typing_ent, annotation_type, None, typing_ent.typing_signature)
            else:
                log.error(f"process_annotation wrong: {abstract_value}")


def process_parameters(args: ast.arguments, scope: ScopeEnv, env: EntEnv, manager: AnalyzeManager, package_db: RootDB,
                       current_db: ModuleDB, summary: FunctionSummary, class_ctx: ty.Optional[Class] = None) -> None:
    location_base = scope.get_location()
    ctx_fun = scope.get_ctx()
    para_constructor = LambdaParameter if isinstance(scope.get_ctx(), LambdaFunction) else Parameter
    default_avaler = ExprAnalyzer(manager, package_db, current_db, None, UseContext(),
                                  env.get_scope().get_builder(), env)

    # TODO: should we add body scope to resolve parameters

    assert isinstance(ctx_fun, Function)
    signature = Signature(ident=ctx_fun.longname.name, is_func=True, func_ent=ctx_fun)

    def process_helper(a: ast.arg, ent_type: ValueInfo, bindings: "Bindings", arg_kind: str, has_default: bool) -> None:
        para_code_span = get_syntactic_span(a)
        arg_name = a.arg
        lookup_res = scope[arg_name]
        parameter_ent = None
        entities = lookup_res.found_entities
        for ent in entities:
            if isinstance(ent[0], Parameter):
                # function overload
                parameter_ent = ent[0]
                break
        if not parameter_ent:
            # new to parameter
            parameter_loc = location_base.append(a.arg, para_code_span, current_db.module_path)
            parameter_ent = para_constructor(parameter_loc.to_longname(), parameter_loc)
            parameter_ent.add_type(ent_type)
            current_db.add_ent(parameter_ent)
            bindings.append((a.arg, [(parameter_ent, ent_type)]))  # correct
            summary.parameter_list.append(a.arg)
            ctx_fun.add_ref(Ref(RefKind.DefineKind, parameter_ent, a.lineno, a.col_offset, a.annotation is not None, None))
            parameter_ent.add_ref(Ref(RefKind.ChildOfKind, ctx_fun, -1, -1, False, None))
            parameter_ent.parent_func_ent = ctx_fun
        else:
            # override
            ...
        parameter_ent.typing_signature = signature
        process_annotation(parameter_ent, manager, package_db, current_db, a.annotation, env)
        if has_default:
            parameter_ent.has_default = True
            parameter_ent.default = ent_type

        # if isinstance(scope.get_ctx(), Function) and a.arg != "self" and a.arg != "cls":  # Class Method
        #     scope.get_ctx().append_parameters(parameter_ent)

        if isinstance(ctx_fun, Function) or isinstance(ent_type, AnyType):  # Class Method
            assert isinstance(ctx_fun, Function)
            if arg_kind == "posonlyargs":
                signature.append_posonlyargs(parameter_ent)
            elif arg_kind == "kwonlyargs":
                signature.append_kwonlyargs(arg_name, parameter_ent)
            elif arg_kind == "stararg":
                signature.has_stararg = True
                signature.stararg = parameter_ent
            elif arg_kind == "starstararg":
                signature.has_starstararg = True
                signature.starstararg = parameter_ent

    args_binding: "Bindings" = []

    for arg in args.posonlyargs:
        process_helper(arg, ValueInfo.get_any(), args_binding, "posonlyargs", has_default=False)

    # TODO: whatever first para in Method should be 'self' except staticmethod
    p_defaults = 0
    i_defaults_starts = len(args.args) - len(args.defaults)
    for i in range(len(args.args)):
        arg = args.args[i]
        typ = ValueInfo.get_any()
        if i == 0:  # first_arg
            first_arg = args.args[0].arg
            if first_arg == "self" or first_arg == "cls":
                if class_ctx is not None:
                    typ = InstanceType(class_ctx)
                    signature.alias_seen = signature.alias_seen.union(class_ctx.alias_self_set)
                    process_helper(arg, typ, args_binding, "posonlyargs", has_default=True)
                    continue

        if args.defaults and i >= i_defaults_starts and p_defaults < len(args.defaults):
            default_expr = args.defaults[p_defaults]
            store_able, info = default_avaler.aval(default_expr)
            typ = info[0][1]
            process_helper(arg, typ, args_binding, "posonlyargs", has_default=True)
            p_defaults += 1
        else:
            process_helper(arg, typ, args_binding, "posonlyargs", has_default=False)

    if args.vararg is not None:  # stararg no default
        process_helper(args.vararg, ValueInfo.get_any(), args_binding, "stararg", has_default=False)

    for i in range(len(args.kwonlyargs)):
        arg = args.kwonlyargs[i]
        default_expr = args.kw_defaults[i]
        if default_expr:
            store_able, info = default_avaler.aval(default_expr)
            typ = info[0][1]
            process_helper(arg, typ, args_binding, "kwonlyargs", has_default=True)
        else:
            typ = ValueInfo.get_any()
            process_helper(arg, typ, args_binding, "kwonlyargs", has_default=False)

    if args.kwarg is not None:  # starstararg no default
        process_helper(args.kwarg, ValueInfo.get_any(), args_binding, "starstararg", has_default=False)

    ctx_fun.append_signature(signature)

    scope.add_continuous(args_binding)

skip_type = ["typing.Union", "typing.Optional", "typing.Tuple"]


def process_alias_map(typing_ent: Parameter, annotation_type: ValueInfo, parent_ent: ty.Optional[Entity], signature: Signature):
    if isinstance(annotation_type, (InstanceType, ConstructorType)):
        annotation_type_name = annotation_type.class_ent.longname.longname
    elif isinstance(annotation_type, UnknownVarType):
        annotation_type_name = annotation_type.unknown_var_ent.longname.longname
    else:  # Union, Option
        return
    if annotation_type_name == "typing.TypeVar":
        parent_ent = parent_ent if parent_ent else typing_ent.parent_func_ent
        generic_name = annotation_type.paras[0].paras[0].value
        generic_location = parent_ent.location.append(generic_name, _Nil_Span, None)

        alias_name = generic_location.to_longname().longname
        typing_ent.alias_set.add(alias_name)
        signature.alias_seen.add(alias_name)
    elif annotation_type_name in skip_type:
        for para in annotation_type.paras:
            process_alias_map(typing_ent, para, parent_ent, signature)
    else:
        # append to
        if isinstance(annotation_type, (InstanceType, ConstructorType)):
            for para in annotation_type.paras:
                process_alias_map(typing_ent, para, annotation_type.class_ent, signature)
        elif isinstance(annotation_type, UnknownVarType):
            for para in annotation_type.paras:
                process_alias_map(typing_ent, para, annotation_type.unknown_var_ent, signature)

