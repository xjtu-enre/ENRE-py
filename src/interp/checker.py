import ast
import typing as ty

from dep.DepDB import DepDB
from ent.EntKind import RefKind
from ent.entity import Variable, Function, Module, Location, UnknownVar, Parameter, Class, ClassAttribute, ModuleAlias, \
    Entity
from interp.aval import Avaler, EntType, ClassType, ConstructorType, ModuleType
from interp.env import EntEnv, ScopeEnv, SubEnv, not_in_class_env
# Avaler stand for Abstract evaluation
from interp.manager_interp import InterpManager
from ref.Ref import Ref


class AInterp:
    def __init__(self, ctx: Module, manager: InterpManager):
        self.manager = manager
        self.module = ctx
        self.global_env: ty.List
        self.dep_db.add_ent(ctx)
        self._avaler = Avaler(self.dep_db)

    @property
    def dep_db(self) -> DepDB:
        return self.manager.dep_db

    def interp(self, stmt: ast.AST, env: EntEnv) -> None:
        """Visit a node."""
        method = 'interp_' + stmt.__class__.__name__
        if isinstance(stmt, ast.expr):
            self._avaler.aval(stmt, env)
            return
        visitor = getattr(self, method, self.generic_interp)
        return visitor(stmt, env)

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

        now_scope = env.get_scope().get_location()
        new_scope = now_scope.append(def_stmt.name)
        func_ent = Function(new_scope.to_longname(), new_scope)

        # add function entity to dependency database
        self.dep_db.add_ent(func_ent)
        # add reference of current contest to the function entity
        self.dep_db.add_ref(env.get_ctx(), Ref(RefKind.DefineKind, func_ent))

        # add function entity to the current environment
        env.add(func_ent, EntType.get_bot())
        # create the scope environment corresponding to the function
        body_env = ScopeEnv(ctx_ent=func_ent, location=new_scope)
        # add function entity to the scope environment corresponding to the function
        body_env.append_ent(func_ent, EntType.get_bot())
        # add parameters to the scope environment
        process_parameters(def_stmt, body_env, self.dep_db, env.get_class_ctx())
        # todo: add parameters to environment
        if not_in_class_env(env):
            env.get_scope().add_hook(def_stmt.body, body_env)
        else:
            class_scope: ScopeEnv = env.get_class_scope()
            class_scope.add_hook(def_stmt.body, body_env)
        # todo: fill until defined Function entity and ScopeEnv

    def interp_ClassDef(self, class_stmt: ast.ClassDef, env: EntEnv) -> None:
        avaler = Avaler(self.dep_db)
        now_scope = env.get_scope().get_location()
        new_scope = now_scope.append(class_stmt.name)
        class_ent = Class(new_scope.to_longname(), new_scope)

        for base_expr in class_stmt.bases:
            avalue = avaler.aval(base_expr, env)
            for base_ent, ent_type in avalue:
                if isinstance(ent_type, ClassType):
                    self.dep_db.add_ref(class_ent, Ref(RefKind.InheritKind, base_ent))

        # add class to current environment
        env.add(class_ent, ConstructorType(class_ent))

        body_env = ScopeEnv(ctx_ent=class_ent, location=new_scope, class_ctx=class_ent)

        body_env.append_ent(class_ent, ConstructorType(class_ent))

        # todo: bugfix, the environment should be same as the environment of class
        env.add_scope(body_env)
        self.interp_top_stmts(class_stmt.body, env)
        env.pop_scope()
        # env.get_scope().add_hook(class_stmt.body, body_env)
        # we can't use this solution because after class definition, the stmts after class definition should be able to
        # known the class's attribute

    def interp_If(self, if_stmt: ast.If, env: EntEnv) -> None:
        avaler = Avaler(self.dep_db)
        avaler.aval(if_stmt.test, env)
        env.add_sub_env(SubEnv())
        self.interp_stmts(if_stmt.body, env)
        body_env = env.pop_sub_env()
        env.add_sub_env(body_env)
        for stmt in if_stmt.orelse:
            env.add_sub_env(SubEnv())
            self.interp(stmt, env)
            branch_env = env.pop_sub_env()
            env.add_sub_env(branch_env)

    def interp_Assign(self, assign_stmt: ast.Assign, env: EntEnv) -> None:
        target_exprs: ty.List[ast.expr] = assign_stmt.targets
        rvalue_expr = assign_stmt.value
        self.get_class_attr(target_exprs, env)
        self.process_assign_helper(rvalue_expr, target_exprs, env)

    def process_assign_helper(self, rvalue_rxpr: ast.expr, target_exprs: ty.List[ast.expr], env: EntEnv):
        avaler = Avaler(self.dep_db)
        for value, value_type in avaler.aval(rvalue_rxpr, env):
            for target_expr in target_exprs:
                for target, target_type in avaler.aval(target_expr, env):
                    # target_ent should be the entity the target_expr could eval to
                    # if target entity is a defined variable or parameter
                    if isinstance(target, Variable) or isinstance(target, Parameter):
                        add_target_var(target, value_type, env, self.dep_db)
                        self.dep_db.add_ref(env.get_ctx(), Ref(RefKind.SetKind, target))
                        # record the target assign to target entity
                    # if the target is a newly defined variable
                    elif isinstance(target, UnknownVar):
                        # newly defined variable
                        location = env.get_scope().get_location()
                        location = location.append(target.longname.name)
                        new_var = Variable(location.to_longname(), location)
                        env.add(new_var, value_type)
                        self.dep_db.add_ref(env.get_ctx(), Ref(RefKind.DefineKind, new_var))
                        self.dep_db.add_ref(env.get_ctx(), Ref(RefKind.SetKind, new_var))
                        # record the target assign to target entity
                        # do nothing if target is not a variable, record the possible Set relation in add_ref method of DepDB
                    else:
                        self.dep_db.add_ref(env.get_ctx(), Ref(RefKind.SetKind, target))

    def interp_AugAssign(self, aug_stmt: ast.AugAssign, env: EntEnv):
        target_expr = aug_stmt.target
        rvalue_expr = aug_stmt.value
        self.process_assign_helper(rvalue_expr, [target_expr], env)

    def interp_Import(self, import_stmt: ast.Import, env: EntEnv) -> None:
        for module_alias in import_stmt.names:
            module_ent = self.manager.import_module(self.module.module_path, module_alias.name)
            if module_alias.asname is None:
                env.add(module_ent, ModuleType.get_module_type())
            else:
                alias_location = env.get_ctx().location.append(module_alias.asname)
                module_alias_ent = ModuleAlias(module_ent.module_path, alias_location)
                env.add(module_alias_ent, ModuleType.get_module_type())
            self.dep_db.add_ref(env.get_ctx(), Ref(RefKind.ImportKind, module_ent))

    # entry of analysis of a module
    def interp_top_stmts(self, stmts: ty.List[ast.stmt], env: EntEnv = None) -> None:
        if env is None:
            env = EntEnv(ScopeEnv(ctx_ent=self.module, location=Location()))

        for stmt in stmts:
            self.interp(stmt, env)

        for hook in env.get_scope().get_hooks():
            stmts, scope_env = hook.stmts, hook.scope_env
            env.add_scope(scope_env)
            self.interp_top_stmts(stmts, env)
            env.pop_scope()

    def interp_stmts(self, stmts: ty.List[ast.stmt], env: EntEnv) -> None:
        for stmt in stmts:
            self.interp(stmt, env)

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
                self.dep_db.add_ref(class_ctx,
                                    Ref(RefKind.DefineKind,
                                        ClassAttribute(attr_location.to_longname(), attr_location)))


# todo: if target not in the current scope, create a new Variable Entity to the current scope
def add_target_var(target: Entity, ent_type: EntType, env: EntEnv, dep_db: DepDB) -> None:
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
    dep_db.add_ref(scope_env.get_ctx(), Ref(RefKind.DefineKind, target))


def process_parameters(def_stmt: ast.FunctionDef, env: ScopeEnv, dep_db: DepDB, class_ctx=ty.Optional[Class]):
    location_base = env.get_location()
    ctx_fun = env.get_ctx()

    def process_helper(id: str, ent_type=None):
        if ent_type == None:
            ent_type = EntType.get_bot()
        parameter_loc = location_base.append(id)
        parameter_ent = Parameter(parameter_loc.to_longname(), parameter_loc)
        env.append_ent(parameter_ent, ent_type)
        dep_db.add_ref(ctx_fun, Ref(RefKind.DefineKind, parameter_ent))

    args = def_stmt.args
    for arg in args.posonlyargs:
        process_helper(arg.arg)

    if len(args.args) >= 1:
        first_arg = args.args[0].arg
        if first_arg == "self":
            if class_ctx is not None:
                class_type = ClassType(class_ctx)
            else:
                class_type = EntType.get_bot()
            process_helper(first_arg, class_type)
        elif first_arg == "cls":
            if class_ctx is not None:
                constructor_type = ConstructorType(class_ctx)
            else:
                constructor_type = EntType.get_bot()
            process_helper(first_arg, constructor_type)
        else:
            process_helper(first_arg)

    for arg in args.args[1:]:
        process_helper(arg.arg)
    if args.vararg is not None:
        process_helper(args.vararg.arg)
    for arg in args.kwonlyargs:
        process_helper(arg.arg)
    if args.kwarg is not None:
        process_helper(args.kwarg.arg)
