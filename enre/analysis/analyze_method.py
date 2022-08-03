# -*- coding:utf-8
import ast
import typing
from enum import Enum
from typing import List, Optional

if typing.TYPE_CHECKING:
    from enre.ent.entity import Function


class FunctionKind(Enum):
    Constructor = "Abstract Constructor"
    AbstractMethod = "Abstract Method"
    StaticMethod = "Static Method"


class AbstractClassInfo:
    # information about an abstract class
    def __init__(self) -> None:
        self.abstract_methods: List[Function] = []
        self.inherit: Optional[str] = None


class MethodVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.abstract_kind: Optional[FunctionKind] = None
        self.static_kind: Optional[FunctionKind] = None
        self.have_raise_NotImplementedError: bool = False
        self.current_func_name: str = ''
        self.readonly_property_name: Optional[str] = None

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.current_func_name = node.name
        for decorator in node.decorator_list:
            if type(decorator) == ast.Name:
                if decorator.id == 'abstractmethod':
                    if node.name.startswith("__") and node.name.endswith("__"):
                        self.abstract_kind = FunctionKind.Constructor
                    else:
                        self.abstract_kind = FunctionKind.AbstractMethod
                elif decorator.id == 'staticmethod':
                    self.static_kind = FunctionKind.StaticMethod
                elif decorator.id == 'property':
                    self.readonly_property_name = node.name
        # 如果普通函数的函数体中只有raise NotImplementError的话也算是抽象函数
        if len(node.body) == 1 and type(node.body[0]) == ast.Raise:
            self.visit_Raise(node.body[0])
            if self.have_raise_NotImplementedError:
                self.abstract_kind = FunctionKind.AbstractMethod

        # 这里是根据return返回属性判断的，判断逻辑不全，已舍弃
        # if self.have_property_decorator and len(node.body) == 1:
        #     if type(node.body[0]) == ast.Return and type(node.body[0].value) == ast.Attribute:
        #         self.readonly_property_name = node.body[0].value.attr

    def visit_Raise(self, node: ast.Raise) -> None:
        if type(node.exc) == ast.Call:
            if type(node.exc.func) == ast.Name and node.exc.func.id == 'NotImplementedError':
                if self.current_func_name.startswith("__") and self.current_func_name.endswith("__"):
                    self.abstract_kind = FunctionKind.Constructor
                else:
                    self.have_raise_NotImplementedError = True
        self.generic_visit(node)
