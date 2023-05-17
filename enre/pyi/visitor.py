# -*- coding:utf-8
from enre.pyi.parser import NameInfo, OverloadedName
import typing

import enre.analysis.analyze_stmt as analyze_stmt
from enre.analysis.env import SubEnvLookupResult

from enre.ent.entity import Entity, Class


DefaultDefHeadLen = 4
DefaultClassHeadLen = 6
DefaultAsyncDefHeadLen = 8

if typing.TYPE_CHECKING:
    from enre.analysis.env import Bindings

_builtins_pool: typing.Dict[str, Entity] = dict()


class NameInfoVisitor:
    @staticmethod
    def analyze_wrapper(manager, dummy_path, env, stub_names, ent_name):
        if not stub_names or not dummy_path or not env:
            return None
        analyzer = analyze_stmt.Analyzer(dummy_path, manager)
        analyzer.analyzing_typeshed = True
        analyzer.current_db.set_env(env)
        if ent_name in stub_names:

            name_info = stub_names[ent_name]
            assert isinstance(name_info, NameInfo)
            ast_trees = []
            if isinstance(name_info.ast, OverloadedName):
                ast_trees.extend(name_info.ast.definitions)
            else:
                ast_trees.append(name_info.ast)
            for ast_tree in ast_trees:
                # print(ent_name, ast_tree)
                analyzer.analyze(ast_tree, env)
            lookup_res: SubEnvLookupResult = env[ent_name]
            if lookup_res.must_found:
                res_ent = lookup_res.found_entities[0][0]
                if isinstance(res_ent, Class):
                    res_ent.typeshed_children = name_info.child_nodes
                return res_ent
            else:
                return None
        else:
            return None
