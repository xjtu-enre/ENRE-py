# -*- coding:utf-8
import enre.typeshed_client as typeshed_client
import typing

from enre.analysis.analyze_manager import AnalyzeManager, ModuleDB, builtins_stub_names, builtins_stub_file
from enre.analysis.value_info import ValueInfo
from enre.analysis.env import ScopeEnv
from enre.analysis.value_info import ConstructorType
from enre.cfg.module_tree import SummaryBuilder
from enre.ent.EntKind import RefKind
from enre.ent.entity import Entity, Class, Location, Function, Span
from enre.ref.Ref import Ref

if typing.TYPE_CHECKING:
    from enre.analysis.env import Bindings

_builtins_pool: typing.Dict[str, Entity] = dict()


class BuiltinsVisitor:
    @staticmethod
    def is_builtins_continue(expr_id: str, manager: AnalyzeManager, current_db: ModuleDB) -> Entity | None:
        get_builtins = builtins_stub_names.get(expr_id)
        if get_builtins is not None:
            cached = _builtins_pool.get(expr_id)
            if cached:
                return cached
            else:
                bv = BuiltinsVisitor(expr_id, get_builtins, manager, current_db)
                ent = bv.generic_analyze(expr_id, get_builtins)
                _builtins_pool[expr_id] = ent
                return ent
        else:
            return None

    def __init__(self, expr_id: str, info: typeshed_client.NameInfo,
                 manager: AnalyzeManager, current_db: ModuleDB) -> None:
        self._id = expr_id
        self._info = info
        self._env = manager.builtins_env
        self._manager = manager
        self._current_db = current_db

    def generic_analyze(self, expr_id: str, info: typeshed_client.NameInfo) -> Entity:
        stub_type = self.judge_stub_type(info)
        method = 'analyze_' + stub_type.__class__.__name__
        visitor = getattr(self, method)
        return visitor(expr_id, info)

    def analyze_ClassDef(self, expr_id: str, info: typeshed_client.NameInfo) -> Entity:
        now_scope = self._env.get_scope().get_location()
        new_scope = now_scope.append(expr_id, Span.get_nil(), None)  # EntLongname(["builtins", expr_id])
        class_ent = Class(new_scope.to_longname(), Location(file_path=builtins_stub_file))
        class_name = expr_id
        new_binding: Bindings = [(class_name, [(class_ent, ConstructorType(class_ent))])]
        self._env.get_scope().add_continuous(new_binding)
        class_summary = self._manager.create_class_summary(class_ent)
        builder = SummaryBuilder(class_summary)
        body_env = ScopeEnv(ctx_ent=class_ent, location=new_scope, class_ctx=class_ent,
                            builder=builder)
        body_env.add_continuous(new_binding)
        self._env.add_scope(body_env)
        for child in info.child_nodes.values():
            if child.is_exported:
                self.generic_analyze(child.name, child)

        self._env.pop_scope()
        self._current_db.add_ent(class_ent)
        return class_ent

    def analyze_FunctionDef(self, expr_id: str, info: typeshed_client.NameInfo) -> Entity:
        now_scope = self._env.get_scope().get_location()
        new_scope = now_scope.append(expr_id, Span.get_nil(), None)
        func_ent = Function(new_scope.to_longname(), Location(file_path=builtins_stub_file))
        self._current_db.add_ent(func_ent)
        # add reference of current contest to the function entity
        current_ctx = self._env.get_ctx()
        current_ctx.add_ref(Ref(RefKind.DefineKind, func_ent, -1, -1, False, None))
        fun_summary = self._manager.create_function_summary(func_ent)
        self._env.get_scope().get_builder().add_child(fun_summary)
        # add function entity to the current environment
        new_binding: "Bindings" = [(expr_id, [(func_ent, ValueInfo.get_any())])]
        self._env.get_scope().add_continuous(new_binding)

        return func_ent

    def analyze_AnnAssign(self, expr_id: str, info: typeshed_client.NameInfo) -> None:
        print(f"builtins AnnAssign: {expr_id}")

    def analyze_Assign(self, expr_id: str, info: typeshed_client.NameInfo) -> None:
        print(f"builtins Assign: {expr_id}")

    def analyze_ImportedName(self, expr_id: str, info: typeshed_client.NameInfo) -> None:
        print(f"builtins ImportedName: {expr_id}")

    @staticmethod
    def judge_stub_type(info: typeshed_client.NameInfo):
        assert isinstance(info, typeshed_client.NameInfo)
        ast_tree = info.ast
        if isinstance(ast_tree, typeshed_client.OverloadedName):
            ast_tree = ast_tree.definitions[0]
        return ast_tree
