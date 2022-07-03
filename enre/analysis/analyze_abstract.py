# -*- coding:utf-8
import ast
from typing import Any

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
    def __init__(self):
        # quite simple, old-school way.
        if self.__class__.__name__ == "A_abstract": 
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


class Visitor(ast.NodeVisitor):
    def __init__(self):
        self.current_class = ''
        self.result = dict()

        self.is_abstract = False
        self.abstract_method = []
        self.static_method = []

    def visit_ClassDef(self, node: ast.ClassDef) -> Any:
        # todo: check whether parent is abstract class
        print(f"ClassDef: \nname: {node.name}")
        self.current_class = node.name
        self.result[self.current_class] = dict(
            is_abstract=False,
            abstract_method=[],
            static_method=[]
        )
        for name in node.bases:
            if type(name) == ast.Name:
                print(f"bases: {name.id}")
                if name.id == 'ABC':
                    self.result[self.current_class]['is_abstract'] = True
                    print("inherit abstract base class")

        print("-----------------------------")
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:
        print(f"FunctionDef: \nname: {node.name}")
        for decorator in node.decorator_list:
            if type(decorator) == ast.Name:
                print(f"decorated by {decorator.id}")
                if decorator.id == 'abstractmethod':
                    self.result[self.current_class]['is_abstract'] = True
                    self.result[self.current_class]['abstract_method'].append(node.name)
                elif decorator.id == 'staticmethod':
                    self.result[self.current_class]['static_method'].append(node.name)

        print("-----------------------------")
        self.generic_visit(node)

    def visit_Raise(self, node: ast.Raise) -> Any:
        # node.exc: Call
        if type(node.exc) == ast.Call:
            if type(node.exc.func) == ast.Name and node.exc.func.id == 'NotImplementedError':
                print(f"Raise: \nname:{node.exc.func.id}")
                self.result[self.current_class]['is_abstract'] = True
                print("raise not implement error")

        print("-----------------------------")
        self.generic_visit(node)


AST = ast.parse(abstract_class_def3)
print(ast.dump(AST))
visitor = Visitor()
visitor.visit(AST)

# output the result
print('analyze result')
for k, v in visitor.result.items():
    print("-----------------------------")
    print(f"class name: {k}")
    for attr, val in v.items():
        print(f"{attr}: {val}")

