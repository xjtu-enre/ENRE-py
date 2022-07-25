# -*- coding:utf-8
import ast
import typing
from enum import Enum
from typing import List, Optional

if typing.TYPE_CHECKING:
    from enre.ent.entity import Function


class AbstractKind(Enum):
    Constructor = "Abstract Constructor"
    AbstractMethod = "Abstract Method"


class AbstractClassInfo:
    # information about an abstract class
    def __init__(self) -> None:
        self.abstract_methods: List[Function] = []
        self.inherit: Optional[str] = None


class MethodVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.method_kind: Optional[AbstractKind] = None
        self.have_raise_NotImplementedError: bool = False

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.current_func_name = node.name
        for decorator in node.decorator_list:
            if type(decorator) == ast.Name:
                if decorator.id == 'abstractmethod':
                    if node.name.startswith("__") and node.name.endswith("__"):
                        self.method_kind = AbstractKind.Constructor
                    else:
                        self.method_kind = AbstractKind.AbstractMethod
        # 如果普通函数的函数体中只有raise NotImplementError的话也算是抽象函数
        if self.have_raise_NotImplementedError and len(node.body) == 1 and type(node.body[0]) == ast.Raise:
            self.generic_visit(node)
            self.method_kind = AbstractKind.AbstractMethod

    def visit_Raise(self, node: ast.Raise) -> None:
        if type(node.exc) == ast.Call:
            if type(node.exc.func) == ast.Name and node.exc.func.id == 'NotImplementedError':
                if self.current_func_name.startswith("__") and self.current_func_name.endswith("__"):
                    self.method_kind = AbstractKind.Constructor
                else:
                    self.have_raise_NotImplementedError = True
        self.generic_visit(node)


def is_abstract_method(node: ast.FunctionDef) -> Optional[AbstractKind]:
    method_visitor: MethodVisitor = MethodVisitor()
    method_visitor.visit(node)
    return method_visitor.method_kind
