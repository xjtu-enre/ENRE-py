# -*- coding:utf-8
import ast
from dataclasses import dataclass
from enum import Enum
from typing import List, Set, Optional

abstract_class_def1 = \
"""
from abc import ABC
class abstract(ABC):
    @staticmethod
    def __init__(self):
        pass
    
    @staticmethod
    def test_raise(self):
        raise NotImplementedError('not implement')
    
    @abstractmethod
    def test_decorator(self):
        pass
"""

abstract_class_def2 = \
"""
class F:
    def __new__(cls):
        if cls is F:
            raise NotImplementedError("Cannot create an instance of abstract class '{}'".format(cls.__name__))
        return super().__new__(cls)
"""

abstract_class_def3 = \
"""
class A_abstract(object):
    class inner:
        def __init__(self):
            if self.__class__.__name__ == "inner": 
                raise NotImplementedError("You can't instantiate this abstract class. Derive it, please.")
        
        def __new__(self):
            if self.__class__.__name__ == "inner": 
                raise NotImplementedError("You can't instantiate this abstract class. Derive it, please.")
        
        def bb(self):
            if self.__class__.__name__ == "inner": 
                raise NotImplementedError("You can't instantiate this abstract class. Derive it, please.")
        
        @abstractmethod
        def test(self):
            pass
            
class B(A_abstract):
    @staticmethod
    def __init__(self):
        pass
    
    @staticmethod
    def test_raise(self):
        pass
    
    def test_decorator(self):
        pass
"""


class Class:
    def __init__(self, name: str):
        self.name: str = name
        self.is_abstract: bool = False
        self.abstract_method: list = []
        self.static_method: list = []
        self.inner_class: dict = dict()


class Visitor(ast.NodeVisitor):
    def __init__(self):
        self.current_class_name_list: list = []
        self.result: dict = dict()
        self.current_class: Class
        self.current_func_name: str = ''

    def add_new_class(self, node: ast.ClassDef) -> None:
        """add new class info and update self.current_class"""
        self.current_class_name_list.append(node.name)

        if len(self.current_class_name_list) == 1:
            self.result[node.name] = Class(name='.'.join(self.current_class_name_list))
            self.current_class = self.result[node.name]
        else:
            self.current_class.inner_class[node.name] = Class(name='.'.join(self.current_class_name_list))
            self.current_class = self.current_class.inner_class[node.name]

    def remove_class(self):
        self.current_class_name_list.pop()
        self.current_class = self.get_current_class()

    def get_current_class(self) -> dict | Class:
        # todo: 分析不在类里面的代码时候current_class为self.result，可能会有问题
        """get current class dict according to self.current_class_name_list"""
        if len(self.current_class_name_list) == 0:
            return self.result
        else:
            temp_class: Class = self.result[self.current_class_name_list[0]]
            for class_name in self.current_class_name_list[1:]:
                temp_class = temp_class.inner_class[class_name]
            return temp_class

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.add_new_class(node)
        print(f"ClassDef: \nname: {self.current_class.name}")

        for name in node.bases:
            if type(name) == ast.Name:
                print(f"bases: {name.id}")
                if name.id == 'ABC':
                    self.current_class.is_abstract = True
                    print("inherit abstract base class")

        print("-----------------------------")
        self.generic_visit(node)
        self.remove_class()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        print(f"FunctionDef: \nname: {node.name}")
        self.current_func_name = node.name
        for decorator in node.decorator_list:
            if type(decorator) == ast.Name:
                print(f"decorated by {decorator.id}")
                if decorator.id == 'abstractmethod':
                    self.current_class.is_abstract = True
                    self.current_class.abstract_method.append(node.name)
                elif decorator.id == 'staticmethod':
                    self.current_class.static_method.append(node.name)

        print("-----------------------------")
        self.generic_visit(node)
        self.current_func_name = ''

    def visit_Raise(self, node: ast.Raise) -> None:
        # node.exc: Call
        if type(node.exc) == ast.Call:
            if type(node.exc.func) == ast.Name and node.exc.func.id == 'NotImplementedError':
                print(f"Raise: \nname:{node.exc.func.id}")

                if self.current_func_name == '__init__' or self.current_func_name == '__new__':
                    self.current_class.is_abstract = True

                    # 说明是在函数中出现的NotImplementError，需要把函数加入到抽象函数数组中
                    self.current_class.abstract_method.append(self.current_func_name)
                    print("raise not implement error")
                if self.current_func_name == '':
                    self.current_class.is_abstract = True
                    print("raise not implement error")

        print("-----------------------------")
        self.generic_visit(node)

    # def visit_If(self, node: ast.If) -> None:
    #     # todo: 关于对于raise NotImplementError的判断
    #     for body_content in node.body:
    #         if type(body_content) == ast.Raise:
    #             if type(body_content.exc) == ast.Call and type(body_content.exc.func) == ast.Name:
    #                 if body_content.exc.func.id == 'NotImplementedError':
    #                     print("123123123123")

class AbstractKind(Enum):
    Constructor = "Abstract Constructor"
    AbstractMethod = "Abstract Method"


class AbstractClassInfo:
    # todo: information about an abstract class
    ...

def is_abstract_method(node: ast.FunctionDef) -> Optional[AbstractKind]:
    # todo: test if the function is abstract method by decorator and its body
    return None


def print_result(class_instance: Class) -> None:
    print("-----------------------------")
    print(f"name : {class_instance.name}")
    print(f"is_abstract : {class_instance.is_abstract}")
    print(f"abstract_method : {class_instance.abstract_method}")
    print(f"static_method : {class_instance.static_method}")

    for inner in class_instance.inner_class.values():
        print_result(inner)


AST = ast.parse(abstract_class_def3)
# print(ast.dump(AST))
# print(astunparse.dump(AST))

visitor = Visitor()
visitor.visit(AST)

# output the result
print('analyze result')
for k, v in visitor.result.items():
    print_result(v)
