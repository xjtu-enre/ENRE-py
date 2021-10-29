import ast
from _ast import AST
from abc import ABC
from dataclasses import dataclass
from typing import List

from interp.env import EntEnv
from interp.manager_interp import ModuleDB


class PatternBuilder:

    def visit(self, node: ast.expr) -> "Target":
        method = 'visit_' + node.__class__.__name__
        visitor = getattr(self, method, self.visit_Lvalue)
        return visitor(node)

    def visit_Attribute(self, node: ast.Attribute) -> "Target":
        return LvalueTar(node)

    def visit_Lvalue(self, node: ast.Name) -> "Target":
        return LvalueTar(node)

    def visit_List(self, node: ast.List) -> "ListTar":
        tar_list: List[Target] = []
        for e in node.elts:
            tar_list.append(self.visit(e))
        return ListTar(tar_list)

    def visit_Tuple(self, node: ast.Tuple) -> "TupleTar":
        tar_list: List[Target] = []
        for e in node.elts:
            tar_list.append(self.visit(e))
        return TupleTar(tar_list)

    def visit_Starred(self, node: ast.Starred) -> "StarTar":
        return StarTar(self.visit(node.value))


class Target(ABC):
    ...


# `Tar` stands for target
@dataclass
class TupleTar(Target):
    tar_list: List[Target]


@dataclass
class LvalueTar(Target):
    lvalue_expr: ast.expr


@dataclass
class ListTar(Target):
    tar_list: List[Target]


@dataclass
class StarTar(Target):
    target: Target


def build_target(tar_expr: ast.expr) -> Target:
    return PatternBuilder().visit(tar_expr)


def assign2target(target: Target, rvalue_expr: ast.expr, env: EntEnv, current_db: ModuleDB) -> None:
    match target:
        case LvalueTar(lvalue_expr):
            ...
        case TupleTar(tar_list):
            ...
        case ListTar(tar_list):
            ...
        case StarTar(tar):
            ...


if __name__ == '__main__':
    tree = ast.parse("*[(x, y), y]")
    tar = build_target(tree.body[0].value)
    print(tar)
