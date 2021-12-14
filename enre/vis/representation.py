from dataclasses import dataclass
from typing import List, Dict, Union, Literal, TypedDict, Any

from enre.ent.entity import Entity
from enre.analysis.analyze_manager import PackageDB

EdgeTy = TypedDict("EdgeTy", {"src": int,
                              "src_name": str,
                              "dest": int,
                              "dest_name": str,
                              "kind": str,
                              "lineno": int,
                              "col_offset": int
                              })

NodeTy = TypedDict("NodeTy", {"id": int, "longname": str, "ent_type": str})

DepTy = TypedDict("DepTy", {"Entities": List[NodeTy], "Dependencies": List[EdgeTy]})


@dataclass
class Node:
    id: int
    longname: str
    ent_type: str


@dataclass
class Edge:
    src: int
    src_name: str
    dest: int
    dest_name: str
    kind: str
    lineno: int
    col_offset: int


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
            ret["Entities"].append({"id": n.id, "longname": n.longname, "ent_type": n.ent_type})
        for e in self._edge_list:
            ret["Dependencies"].append({"src": e.src,
                                        "src_name": e.src_name,
                                        "dest": e.dest,
                                        "dest_name": e.dest_name,
                                        "kind": e.kind,
                                        "lineno": e.lineno,
                                        "col_offset": e.col_offset})
        return ret

    @classmethod
    def write_ent_repr(cls, ent: Entity, dep_repr: "DepRepr") -> None:
        dep_repr.add_node(Node(ent.id, ent.longname.longname, ent.kind().value))
        for ref in ent.refs():
            dep_repr._edge_list.append(Edge(src=ent.id,
                                            src_name=ent.longname.longname,
                                            dest=ref.target_ent.id,
                                            dest_name=ref.target_ent.longname.longname,
                                            kind=ref.ref_kind.value,
                                            lineno=ref.lineno,
                                            col_offset=ref.col_offset))

    @classmethod
    def from_package_db(cls, package_db: PackageDB) -> "DepRepr":
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
                                   ent_type=ent.kindname()))

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
                                       col_offset=col_offset))
        return dep_repr
