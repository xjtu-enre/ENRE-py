# -*- coding:utf-8
import ast
from pathlib import Path
import astpretty

import enre.typeshed_client as typeshed_client
import typing

from enre.analysis.analyze_manager import AnalyzeManager, ModuleDB, builtins_stub_names, builtins_stub_file
from enre.analysis.value_info import ValueInfo, AttributeType
from enre.analysis.env import ScopeEnv, EntEnv
from enre.analysis.value_info import ConstructorType
from enre.cfg.module_tree import SummaryBuilder
from enre.ent.EntKind import RefKind
from enre.ent.entity import Entity, Class, Location, Function, Span, Variable, ReferencedAttribute, Attribute, \
    get_syntactic_head
from enre.ref.Ref import Ref

DefaultDefHeadLen = 4
DefaultClassHeadLen = 6
DefaultAsyncDefHeadLen = 8

if typing.TYPE_CHECKING:
    from enre.analysis.env import Bindings

_builtins_pool: typing.Dict[str, Entity] = dict()


class NameInfoVisitor:
    @staticmethod
    def is_builtins_continue(expr_id: str, manager: AnalyzeManager, current_db: ModuleDB) -> Entity | None:
        get_builtins = builtins_stub_names.get(expr_id)
        if get_builtins is not None:
            cached = _builtins_pool.get(expr_id)
            if cached:
                return cached
            else:
                bv = NameInfoVisitor(expr_id, get_builtins, manager, current_db,
                                     manager.builtins_env, builtins_stub_file)
                ent = bv.generic_analyze(expr_id, get_builtins)
                _builtins_pool[expr_id] = ent
                return ent
        else:
            return None

    def __init__(self, expr_id: str, info: typeshed_client.NameInfo,
                 manager: AnalyzeManager, current_db: ModuleDB, env: EntEnv, stub_file: Path) -> None:
        self._id = expr_id
        self._info = info
        self._manager = manager
        self._current_db = current_db
        self._env = env
        self._stub_file = stub_file

    def generic_analyze(self, expr_id: str, info: typeshed_client.NameInfo) -> Entity:
        try:
            stub_type = self.judge_stub_type(info)
            method = 'analyze_' + stub_type.__class__.__name__
            visitor = getattr(self, method)
            return visitor(expr_id, info, stub_type)
        except AssertionError:
            # print("AssertionError", expr_id)
            return self.create_attr(expr_id, info, None)

    def analyze_ClassDef(self, expr_id: str, info: typeshed_client.NameInfo, stub: ast.ClassDef) -> Entity:
        now_scope = self._env.get_scope().get_location()
        class_code_span = get_syntactic_head(stub)
        class_code_span.offset(DefaultClassHeadLen)
        new_scope = now_scope.append(expr_id, class_code_span, None)  # EntLongname(["builtins", expr_id])
        class_ent = Class(new_scope.to_longname(), new_scope)
        class_name = expr_id
        new_binding: Bindings = [(class_name, [(class_ent, ConstructorType(class_ent))])]
        self._env.get_scope().add_continuous(new_binding)
        current_ctx = self._env.get_ctx()
        current_ctx.add_ref(Ref(RefKind.DefineKind, class_ent, -1, -1, False, None))
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

    def analyze_FunctionDef(self, expr_id: str, info: typeshed_client.NameInfo, stub: ast.AST) -> Entity:
        now_scope = self._env.get_scope().get_location()
        func_span = get_syntactic_head(stub)
        func_span.offset(DefaultDefHeadLen)
        new_scope = now_scope.append(expr_id, func_span, None)
        func_ent = Function(new_scope.to_longname(), new_scope)
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

    def analyze_AnnAssign(self, expr_id: str, info: typeshed_client.NameInfo, stub: ast.AST) -> Entity:
        return self.create_attr(expr_id, info, stub)
        # now_scope = self._env.get_scope().get_location()
        # new_scope = now_scope.append(expr_id, Span.get_nil(), None)
        #
        #
        #
        # new_var = Variable(new_scope.to_longname(), Location(file_path=self._stub_file))
        #
        # new_binding: "Bindings" = [(new_var.longname.name, [(new_var, ValueInfo.get_any())])]
        # current_ctx = self._env.get_ctx()
        # self._current_db.add_ent(new_var)
        # current_ctx.add_ref(Ref(RefKind.DefineKind, new_var, -1, -1, False, None))
        # current_ctx.add_ref(Ref(RefKind.SetKind, new_var, -1, -1, False, None))
        # self._env.get_scope().add_continuous(new_binding)
        # # print(f"NameInfoVisitor AnnAssign: {expr_id}")
        # return new_var

    def analyze_Assign(self, expr_id: str, info: typeshed_client.NameInfo, stub: ast.AST) -> Entity:
        return self.create_attr(expr_id, info, stub)
        # now_scope = self._env.get_scope().get_location()
        # new_scope = now_scope.append(expr_id, Span.get_nil(), None)
        # new_var = Variable(new_scope.to_longname(), Location(file_path=self._stub_file))
        #
        # new_binding: "Bindings" = [(new_var.longname.name, [(new_var, ValueInfo.get_any())])]
        # current_ctx = self._env.get_ctx()
        # self._current_db.add_ent(new_var)
        # current_ctx.add_ref(Ref(RefKind.DefineKind, new_var, -1, -1, False, None))
        # current_ctx.add_ref(Ref(RefKind.SetKind, new_var, -1, -1, False, None))
        # self._env.get_scope().add_continuous(new_binding)
        # # print(f"NameInfoVisitor AnnAssign: {expr_id}")
        # return new_var

    def analyze_ImportedName(self, expr_id: str, info: typeshed_client.NameInfo, stub: ast.AST) -> Entity:
        return self.create_attr(expr_id, info, None)

    @staticmethod
    def judge_stub_type(info: typeshed_client.NameInfo):
        assert isinstance(info, typeshed_client.NameInfo)
        ast_tree = info.ast
        if isinstance(ast_tree, typeshed_client.OverloadedName):
            ast_tree = ast_tree.definitions[0]
        return ast_tree

    def create_attr(self, expr_id: str, info: typeshed_client.NameInfo, stub: ast.AST) -> Entity:
        # astpretty.pprint(stub)
        span = Span(stub.lineno, stub.end_lineno, stub.col_offset, stub.end_col_offset) if stub else Span.get_nil()
        now_scope = self._env.get_scope().get_location()
        new_scope = now_scope.append(expr_id, span, None)
        new_attr = Attribute(new_scope.to_longname(),
                             self._env.get_scope().get_location().append(expr_id, Span.get_nil(), None))

        new_binding: "Bindings" = [(new_attr.longname.name, [(new_attr, AttributeType(new_attr))])]
        current_ctx = self._env.get_ctx()
        self._current_db.add_ent(new_attr)
        current_ctx.add_ref(Ref(RefKind.ImportKind, new_attr, -1, -1, False, None))  # This location can be mark sure
        current_ctx.add_ref(Ref(RefKind.DefineKind, new_attr, -1, -1, False, None))
        self._env.get_scope().add_continuous(new_binding)
        # print(f"NameInfoVisitor ImportedName: {expr_id}")
        return new_attr

