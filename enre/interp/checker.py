import ast
import typing as ty
from dataclasses import dataclass
from pathlib import Path

from dep.DepDB import DepDB
from ent.EntKind import RefKind
from ent.ent_finder import get_module_level_ent
from ent.entity import Variable, Function, Module, Location, UnknownVar, Parameter, Class, ClassAttribute, ModuleAlias, \
    Entity, UnresolvedAttribute, Alias, UnknownModule, LambdaFunction, LambdaParameter, Span, get_syntactic_span
from interp.enttype import EntType
from interp.env import EntEnv, ScopeEnv, ParallelSubEnv, ContinuousSubEnv, OptionalSubEnv, BasicSubEnv
# Avaler stand for Abstract evaluation
from interp.manager_interp import InterpManager, PackageDB, ModuleDB
from ref.Ref import Ref


@dataclass
class InterpContext:
    env: EntEnv
    package_db: PackageDB
    current_db: ModuleDB
    coordinate: ty.Tuple[int, int]


class AInterp:
    def __init__(self, rel_path: Path, manager: InterpManager):
        module_ent = manager.package_db[rel_path].module_ent
        self.manager = manager
        self.module = module_ent
        self.global_env: ty.List
        self.package_db: "PackageDB" = manager.package_db
        self.current_db: "ModuleDB" = manager.package_db[rel_path]
        self._avaler = UseAvaler(self.package_db, self.current_db)

    def interp(self, stmt: ast.AST, env: EntEnv) -> None:
        """Visit a node."""
        method = 'interp_' + stmt.__class__.__name__
        if isinstance(stmt, ast.expr):
            self._avaler.aval(stmt, env)
            return
        visitor = getattr(self, method, self.generic_interp)
        visitor(stmt, env)

    def generic_interp(self, stmt: ast.AST, env: EntEnv) -> None:
        """Called if no explicit visitor function exists for a node."""
        for field, value in ast.iter_fields(stmt):
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, ast.expr):
                        self._avaler.aval(item, env)
                    elif isinstance(item, ast.AST):
                        self.interp(item, env)
            elif isinstance(value, ast.AST):
                self.interp(value, env)

    def interp_FunctionDef(self, def_stmt: ast.FunctionDef, env: EntEnv) -> None:
        in_class_env = isinstance(env.get_ctx(), Class)
        fun_code_span = get_syntactic_span(def_stmt)
        now_scope = env.get_scope().get_location()
        new_scope = now_scope.append(def_stmt.name, fun_code_span)
        func_ent = Function(new_scope.to_longname(), new_scope)

        # add function entity to dependency database
        self.current_db.add_ent(func_ent)
        # add reference of current contest to the function entity
        current_ctx = env.get_ctx()
        current_ctx.add_ref(Ref(RefKind.DefineKind, func_ent, def_stmt.lineno, def_stmt.col_offset))

        # add function entity to the current environment
        env.get_scope().add_continuous([(func_ent, EntType.get_bot())])
        # create the scope environment corresponding to the function
        body_env = ScopeEnv(ctx_ent=func_ent, location=new_scope)
        # add function entity to the scope environment corresponding to the function while it's not a class method
        if not isinstance(current_ctx, Class):
            body_env.add_continuous([(func_ent, EntType.get_bot())])
        # add parameters to the scope environment
        process_parameters(def_stmt.args, body_env, self.current_db, env.get_class_ctx())
        hook_scope = env.get_scope(1) if in_class_env else env.get_scope()

        hook_scope.add_hook(def_stmt.body, body_env)
        self.process_annotations(def_stmt.args, env)

    def interp_ClassDef(self, class_stmt: ast.ClassDef, env: EntEnv) -> None:
        avaler = UseAvaler(self.package_db, self.current_db)
        now_scope = env.get_scope().get_location()
        class_code_span = get_syntactic_span(class_stmt)
        new_scope = now_scope.append(class_stmt.name, class_code_span)
        class_ent = Class(new_scope.to_longname(), new_scope)
        self.current_db.add_ent(class_ent)
        env.get_ctx().add_ref(Ref(RefKind.DefineKind, class_ent, class_stmt.lineno, class_stmt.col_offset))
        for base_expr in class_stmt.bases:
            avalue = avaler.aval(base_expr, env)
            for base_ent, ent_type in avalue:
                if isinstance(ent_type, ConstructorType):
                    class_ent.add_ref(Ref(RefKind.InheritKind, base_ent, class_stmt.lineno,
                                          class_stmt.col_offset))
                else:
                    class_ent.add_ref(Ref(RefKind.InheritKind, base_ent, class_stmt.lineno,
                                          class_stmt.col_offset))
                    # todo: handle unknown class

        # add class to current environment
        env.get_scope().add_continuous([(class_ent, ConstructorType(class_ent))])

        body_env = ScopeEnv(ctx_ent=class_ent, location=new_scope, class_ctx=class_ent)

        body_env.add_continuous([(class_ent, ConstructorType(class_ent))])
        # todo: bugfix, the environment should be same as the environment of class
        env.add_scope(body_env)
        self.interp_top_stmts(class_stmt.body, env)
        env.pop_scope()
        # env.get_scope().add_hook(class_stmt.body, body_env)
        # we can't use this solution because after class definition, the stmts after class definition should be able to
        # known the class's attribute

    def interp_If(self, if_stmt: ast.If, env: EntEnv) -> None:
        in_len = len(env.get_scope())
        avaler = UseAvaler(self.package_db, self.current_db)
        avaler.aval(if_stmt.test, env)
        before = len(env.get_scope())
        env.add_sub_env(BasicSubEnv())
        self.interp_stmts(if_stmt.body, env)
        body_env = env.pop_sub_env()
        after = len(env.get_scope())
        assert before == after
        for stmt in if_stmt.orelse:
            env.add_sub_env(BasicSubEnv())
            self.interp(stmt, env)
            branch_env = env.pop_sub_env()
            body_env = ParallelSubEnv(body_env, branch_env)
        forward_env = env.pop_sub_env()
        env.add_sub_env(ContinuousSubEnv(forward_env, body_env))
        out_len = len(env.get_scope())
        # print(f"in length: {in_len} out length: {out_len}")
        assert (in_len == out_len)

    def interp_For(self, for_stmt: ast.For, env: EntEnv) -> None:
        from interp.assign_target import build_target, unpack_semantic, dummy_iter
        iter_value = dummy_iter(self._avaler.aval(for_stmt.iter, env))
        target_expr = for_stmt.target
        target_lineno = target_expr.lineno
        target_col_offset = target_expr.col_offset
        target = build_target(target_expr)
        unpack_semantic(target, iter_value,
                        InterpContext(env, self.package_db, self.current_db, (target_lineno, target_col_offset)))

        # self._avaler.aval(for_stmt.target, env)
        # self._avaler.aval(for_stmt.iter, env)
        # todo: verify it's two re evaluation
        env.add_sub_env(BasicSubEnv())
        self.interp_stmts(for_stmt.body, env)
        sub_env = env.pop_sub_env()
        optional_sub_env = OptionalSubEnv(sub_env)
        continuous_sub_env = ContinuousSubEnv(env.pop_sub_env(), optional_sub_env)
        env.add_sub_env(continuous_sub_env)
        # todo: loop the for statement until stabilized

    def interp_Assign(self, assign_stmt: ast.Assign, env: EntEnv) -> None:
        target_exprs: ty.List[ast.expr] = assign_stmt.targets
        rvalue_expr = assign_stmt.value
        self.process_assign_helper(rvalue_expr, target_exprs, env)

    def interp_AugAssign(self, aug_stmt: ast.AugAssign, env: EntEnv):
        target_expr = aug_stmt.target
        rvalue_expr = aug_stmt.value
        if rvalue_expr is not None:
            self.process_assign_helper(rvalue_expr, [target_expr], env)
        else:
            self.declare_semantic(target_expr, env)

    def interp_AnnAssign(self, ann_stmt: ast.AnnAssign, env: EntEnv):
        target_expr = ann_stmt.target
        rvalue_expr = ann_stmt.value
        self._avaler.aval(ann_stmt.annotation, env)
        self.process_assign_helper(rvalue_expr, [target_expr], env)

    def interp_Expr(self, expr_stmt: ast.Expr, env: EntEnv) -> None:
        self._avaler.aval(expr_stmt.value, env)

    def process_assign_helper(self, rvalue_expr: ty.Optional[ast.expr], target_exprs: ty.List[ast.expr], env: EntEnv):
        set_avaler = SetAvaler(self.package_db, self.current_db)
        use_avaler = UseAvaler(self.package_db, self.current_db)
        from interp.assign_target import build_target, assign2target

        frame_entities: ty.List[ty.Tuple[Entity, EntType]]
        for target_expr in target_exprs:
            target_lineno = target_expr.lineno
            target_col_offset = target_expr.col_offset
            target = build_target(target_expr)
            assign2target(target, rvalue_expr,
                          InterpContext(env, self.package_db, self.current_db, (target_lineno, target_col_offset)))

    def interp_Import(self, import_stmt: ast.Import, env: EntEnv) -> None:
        for module_alias in import_stmt.names:
            module_ent = self.manager.import_module(self.module, module_alias.name, import_stmt.lineno,
                                                    import_stmt.col_offset)
            if module_alias.asname is None:
                env.get_scope().add_continuous([(module_ent, ModuleType.get_module_type())])
            else:
                alias_location = env.get_ctx().location.append(module_alias.asname, Span.get_nil())
                module_alias_ent = ModuleAlias(module_ent, alias_location)
                self.current_db.add_ent(module_alias_ent)
                env.get_scope().add_continuous([(module_alias_ent, ModuleType.get_module_type())])
            env.get_ctx().add_ref(Ref(RefKind.ImportKind, module_ent, import_stmt.lineno,
                                      import_stmt.col_offset))

    def interp_ImportFrom(self, import_stmt: ast.ImportFrom, env: EntEnv) -> None:
        # todo: import from statement
        module_identifier = import_stmt.module
        if module_identifier is None:
            print("implicit import not implemented yet")
            return
        module_ent = self.manager.import_module(self.module, module_identifier, import_stmt.lineno,
                                                import_stmt.col_offset)
        current_ctx = env.get_ctx()
        current_ctx.add_ref(Ref(RefKind.ImportKind, module_ent, import_stmt.lineno, import_stmt.col_offset))
        if not isinstance(module_ent, UnknownModule):
            # if the imported module can't found in package
            frame_entities: ty.List[ty.Tuple[Entity, EntType]]
            for alias in import_stmt.names:
                name = alias.name
                as_name = alias.asname
                imported_ents = get_module_level_ent(module_ent, name)
                frame_entities = []
                for ent in imported_ents:
                    if as_name is not None:
                        location = env.get_scope().get_location().append(as_name, Span.get_nil())
                        alias_ent = Alias(location.to_longname(), location, ent)
                        current_ctx.add_ref(Ref(RefKind.DefineKind, alias_ent, alias.lineno, alias.col_offset))
                        self.current_db.add_ent(alias_ent)
                        frame_entities.append((alias_ent, ent.direct_type()))
                    else:
                        frame_entities.append((ent, ent.direct_type()))
                env.get_scope().add_continuous(frame_entities)
        else:
            self.package_db.add_ent_global(module_ent)
            frame_entities = []
            for alias in import_stmt.names:
                alias_code_span = get_syntactic_span(alias)
                location = module_ent.location.append(alias.name, alias_code_span)
                unknown_var = UnknownVar.get_unknown_var(location.to_longname().name)
                self.package_db.add_ent_global(unknown_var)
                module_ent.add_ref(Ref(RefKind.DefineKind, unknown_var, 0, 0))
                if alias.asname is not None:
                    as_location = env.get_scope().get_location().append(alias.asname, alias_code_span)
                    alias_ent = Alias(as_location.to_longname(), location, unknown_var)
                    self.current_db.add_ent(alias_ent)
                    frame_entities.append((alias_ent, EntType.get_bot()))
                else:
                    frame_entities.append((unknown_var, EntType.get_bot()))
            env.get_scope().add_continuous(frame_entities)

    def interp_With(self, with_stmt: ast.With, env: EntEnv) -> None:
        from interp.assign_target import build_target, unpack_semantic
        for with_item in with_stmt.items:
            context_expr = with_item.context_expr
            optional_var = with_item.optional_vars
            with_value = self._avaler.aval(context_expr, env)
            if optional_var is not None:
                target = build_target(optional_var)
                target_lineno = optional_var.lineno
                target_col_offset = optional_var.col_offset
                unpack_semantic(target, with_value,
                                InterpContext(env, self.package_db, self.current_db,
                                              (target_lineno, target_col_offset)))
        self.interp_stmts(with_stmt.body, env)

    def interp_Try(self, try_stmt: ast.Try, env: EntEnv) -> None:
        from interp.error_handler import handler_semantic
        env.add_sub_env(BasicSubEnv())
        self.interp_stmts(try_stmt.body, env)
        try_body_env = env.pop_sub_env()

        for handler in try_stmt.handlers:
            env.add_sub_env(BasicSubEnv())
            err_constructor = handler.type

            if err_constructor is not None:
                target_lineno = handler.lineno
                target_col_offset = handler.col_offset
                handler_semantic(handler.name, ast.Expr(err_constructor),
                                 InterpContext(env, self.package_db, self.current_db,
                                               (target_lineno, target_col_offset)))
            self.interp_stmts(handler.body, env)
            handler_env = env.pop_sub_env()
            try_body_env = ParallelSubEnv(try_body_env, handler_env)

        env.add_sub_env(BasicSubEnv())
        self.interp_stmts(try_stmt.orelse, env)
        orelse_body_env = env.pop_sub_env()

        env.add_sub_env(BasicSubEnv())
        self.interp_stmts(try_stmt.finalbody, env)
        finally_body_env = env.pop_sub_env()

        try_env = ParallelSubEnv(try_body_env, ParallelSubEnv(orelse_body_env, finally_body_env))
        forward_env = env.pop_sub_env()
        env.add_sub_env(ContinuousSubEnv(forward_env, try_env))

    # entry of analysis of a module
    def interp_top_stmts(self, stmts: ty.List[ast.stmt], env: EntEnv = None) -> None:
        if env is None:
            env = EntEnv(ScopeEnv(ctx_ent=self.module, location=Location()))

        for stmt in stmts:
            self.interp(stmt, env)

        for hook in env.get_scope().get_hooks():
            stmts, scope_env = hook.stmts, hook.scope_env
            before = len(env.get_scope())
            env.add_scope(scope_env)
            self.interp_top_stmts(stmts, env)
            env.pop_scope()
            after = len(env.get_scope())
            assert (before == after)

    def interp_stmts(self, stmts: ty.List[ast.stmt], env: EntEnv) -> None:
        for stmt in stmts:
            self.interp(stmt, env)

    # unused function
    @ty.no_type_check
    def get_class_attr(self, target_exprs: ty.List[ast.expr], env: EntEnv):
        class_ctx = env.get_class_ctx()
        if class_ctx is None:
            return

        def get_self_accessing(expr: ast.expr) -> ty.Optional[str]:
            if isinstance(expr, ast.Attribute) and isinstance(expr.value, ast.Name) and expr.value.id == "self":
                return expr.attr
            else:
                return None

        for target_expr in target_exprs:
            attr = get_self_accessing(target_expr)
            if attr is not None:
                attr_location = class_ctx.location.append(attr)
                class_ctx.add_ref(Ref(RefKind.DefineKind,
                                      ClassAttribute(attr_location.to_longname(), attr_location),
                                      target_expr.lineno, target_expr.col_offset))

    def declare_semantic(self, target_expr: ast.expr, env: EntEnv):
        pass

    def process_annotations(self, args: ast.arguments, env: EntEnv):
        for arg in args.args:
            if arg.annotation is not None:
                self._avaler.aval(arg.annotation, env)


# todo: if target not in the current scope, create a new Variable Entity to the current scope
# deprecated function
@ty.no_type_check
def add_target_var(target: Entity, ent_type: EntType, env: EntEnv, dep_db: DepDB) -> None:
    raise ValueError("calling deprecated function")
    scope_env = env.get_scope()
    matched_ents = scope_env[target.longname.name]
    for ent, ent_type1 in matched_ents:
        if ent.longname == target.longname:
            return

    # founded target variable not in the current scope
    # create a new variable entity to the current scope
    location = env.get_scope().get_location()
    location = location.append(target.longname.name)
    new_var = Variable(location.to_longname(), location)
    scope_env.append_ent(new_var, ent_type)


def process_parameters(args: ast.arguments, env: ScopeEnv, current_db: ModuleDB, class_ctx=ty.Optional[Class]):
    location_base = env.get_location()
    ctx_fun = env.get_ctx()
    para_constructor = LambdaParameter if isinstance(env.get_ctx(), LambdaFunction) else Parameter

    def process_helper(a: ast.arg, ent_type=None):
        if ent_type == None:
            ent_type = EntType.get_bot()
        para_code_span = get_syntactic_span(a)
        parameter_loc = location_base.append(a.arg, para_code_span)
        parameter_ent = para_constructor(parameter_loc.to_longname(), parameter_loc)
        current_db.add_ent(parameter_ent)
        env.add_continuous([(parameter_ent, ent_type)])
        ctx_fun.add_ref(Ref(RefKind.DefineKind, parameter_ent, a.lineno, a.col_offset))

    for arg in args.posonlyargs:
        process_helper(arg)

    if len(args.args) >= 1:
        first_arg = args.args[0].arg
        if first_arg == "self":
            if class_ctx is not None:
                class_type: EntType = ClassType(class_ctx)
            else:
                class_type = EntType.get_bot()
            process_helper(args.args[0], class_type)
        elif first_arg == "cls":
            if class_ctx is not None:
                constructor_type: EntType = ConstructorType(class_ctx)
            else:
                constructor_type = EntType.get_bot()
            process_helper(args.args[0], constructor_type)
        else:
            process_helper(args.args[0])

    for arg in args.args[1:]:
        process_helper(arg)
    if args.vararg is not None:
        process_helper(args.vararg)
    for arg in args.kwonlyargs:
        process_helper(arg)
    if args.kwarg is not None:
        process_helper(args.kwarg)


from interp.aval import UseAvaler, ClassType, ConstructorType, ModuleType, SetAvaler
