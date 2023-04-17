import ast

from enre.analysis.env import EntEnv


class ISInstanceVisitor(ast.NodeVisitor):
    def __init__(self, env, test: ast.expr) -> None:
        self._env: EntEnv = env
        self.generic_analyze(test)

    def visit(self, node: ast.AST) -> None:
        method = 'analyze_' + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)
        visitor(node)

    def generic_analyze(self, node: ast.AST) -> None:
        for field, value in ast.iter_fields(node):
            if isinstance(value, list):
                for item in value:
                    self.visit(item)
            elif isinstance(value, ast.AST):
                self.visit(value)

    def analyze_BoolOp(self, node: ast.BoolOp, ctx_op=None) -> None:
        op = node.op
        values = node.values
        for value in values:
            if isinstance(value, ast.BoolOp):
                self.analyze_BoolOp(value, op)
            elif isinstance(value, ast.Call):
                # 1. isintance?
                # 2. not isinstance --> remove all itemitem adds that type
                ...



    def analyze_UnaryOp(self, node: ast.UnaryOp) -> None:
        ...
