from dataclasses import dataclass
from typing import List, TypedDict, Any, TypeAlias, Dict, Iterable

from enre.analysis.analyze_manager import RootDB
from enre.ent.EntKind import EntKind
from enre.ent.entity import Entity

EdgeTy = TypedDict("EdgeTy", {"src": int,
                              "src_name": str,
                              "dest": int,
                              "dest_name": str,
                              "kind": str,
                              "lineno": int,
                              "col_offset": int,
                              "in_type_context": bool
                              })

NodeTy = TypedDict("NodeTy", {"id": int, "longname": str, "ent_type": str,
                              "start_line": int, "end_line": int, "start_col": int, "end_col": int})

DepTy = TypedDict("DepTy", {"Entities": List[NodeTy], "Dependencies": List[EdgeTy]})


@dataclass
class Node:
    id: int
    longname: str
    ent_type: str
    start_line: int
    end_line: int
    start_col: int
    end_col: int


@dataclass
class Edge:
    src: int
    src_name: str
    dest: int
    dest_name: str
    kind: str
    lineno: int
    col_offset: int
    in_type_ctx: bool
    resolved_targets: Iterable[int]


JsonDict: TypeAlias = Dict[str, Any]


class DepRepr:
    def __init__(self) -> None:
        self._node_list: List[Node] = []
        self._edge_list: List[Edge] = []

    def add_node(self, n: Node) -> None:
        self._node_list.append(n)

    def add_edge(self, e: Edge) -> None:
        self._edge_list.append(e)

    def to_json(self) -> DepTy:
        ret: DepTy = {"Entities": [], "Dependencies": []}
        for n in self._node_list:
            ret["Entities"].append({"id": n.id, "longname": n.longname, "ent_type": n.ent_type,
                                    "start_line": n.start_line, "end_line": n.end_line,
                                    "start_col": n.start_col, "end_col": n.end_col})
        for e in self._edge_list:
            ret["Dependencies"].append({"src": e.src,
                                        "src_name": e.src_name,
                                        "dest": e.dest,
                                        "dest_name": e.dest_name,
                                        "kind": e.kind,
                                        "lineno": e.lineno,
                                        "col_offset": e.col_offset,
                                        "in_type_context": e.in_type_ctx})
        return ret

    @classmethod
    def write_ent_repr(cls, ent: Entity, dep_repr: "DepRepr") -> None:
        helper_ent_types = [EntKind.ReferencedAttr, EntKind.Anonymous]
        if ent.kind() not in helper_ent_types:
            dep_repr.add_node(Node(ent.id, ent.longname.longname, ent.kind().value, ent.location.code_span.start_col,
                                   ent.location.code_span.end_col, ent.location.code_span.start_col,
                                   ent.location.code_span.end_col))
            for ref in ent.refs():
                if ref.target_ent.kind() not in helper_ent_types:
                    resolved_targets = [t.id for t in ref.resolved_targets]
                    dep_repr._edge_list.append(Edge(src=ent.id,
                                                    src_name=ent.longname.longname,
                                                    dest=ref.target_ent.id,
                                                    dest_name=ref.target_ent.longname.longname,
                                                    kind=ref.ref_kind.value,
                                                    in_type_ctx=ref.in_type_ctx,
                                                    lineno=ref.lineno,
                                                    col_offset=ref.col_offset,
                                                    resolved_targets=resolved_targets))

    def to_json_1(self) -> JsonDict:
        ret: JsonDict = {"variables": [], "cells": []}
        for n in self._node_list:
            ret["variables"].append({"id": n.id, "qualifiedName": n.longname, "category": n.ent_type,
                                     "location": {"startLine": n.start_line, "endLine": n.end_line,
                                                  "startColumn": n.start_col, "endColumn": n.end_col}})
        for e in self._edge_list:
            values: JsonDict = {"kind": e.kind}
            if e.resolved_targets:
                values["resolved"] = e.resolved_targets
            ret["cells"].append({"src": e.src,
                                 "dest": e.dest,
                                 "values": values})
        return ret

    @classmethod
    def from_package_db(cls, package_db: RootDB) -> "DepRepr":
        dep_repr = DepRepr()
        for rel_path, module_db in package_db.tree.items():
            for ent in module_db.dep_db.ents:
                cls.write_ent_repr(ent, dep_repr)
        for ent in package_db.global_db.ents:
            cls.write_ent_repr(ent, dep_repr)
        return dep_repr

    @classmethod
    def from_und_db(cls, und_db: Any) -> "DepRepr":
        dep_repr = DepRepr()
        for ent in und_db.ents():
            dep_repr.add_node(Node(id=ent.id(),
                                   longname=ent.longname(),
                                   ent_type=ent.kindname(),
                                   start_line=-1,
                                   end_line=-1,
                                   start_col=-1,
                                   end_col=-1))

            for ref in ent.refs():
                if not ref.isforward():
                    continue
                tar_ent = ref.ent()
                lineno = ref.line()
                col_offset = ref.column()
                dep_repr.add_edge(Edge(src=ent.id(),
                                       src_name=ent.longname(),
                                       dest=tar_ent.id(),
                                       dest_name=tar_ent.longname(),
                                       kind=ref.kind().name(),
                                       lineno=lineno,
                                       col_offset=col_offset,
                                       in_type_ctx=False,
                                       resolved_targets=[]))
        return dep_repr
