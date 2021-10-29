from dataclasses import dataclass
from typing import List, Dict, Union, Literal

from ent.entity import Entity
from interp.manager_interp import PackageDB

NodeTy = Dict[Union[str, Literal["id"]], Union[str, int]]
EdgeTy = Dict[str, Union[str, int]]


@dataclass
class Node:
    id: int
    longname: str
    ent_type: str


@dataclass
class Edge:
    src: int
    dest: int
    kind: str
    lineno: int
    col_offset: int


class DepRepr:
    def __init__(self):
        self._node_list: List[Node] = []
        self._edge_list: List[Edge] = []

    def add_node(self, n: Node):
        self._node_list.append(n)

    def add_edge(self, e: Edge):
        self._edge_list.append(e)

    def to_json(self) -> Dict:
        ret: Dict[str, List[Union[NodeTy, EdgeTy]]] = dict()
        ret["Entities"] = []
        ret["Dependencies"] = []
        for n in self._node_list:
            ret["Entities"].append(n.__dict__)
        for e in self._edge_list:
            ret["Dependencies"].append(e.__dict__)
        return ret

    @classmethod
    def write_ent_repr(cls, ent: Entity, dep_repr: "DepRepr"):
        dep_repr.add_node(Node(ent.id, ent.longname.longname, ent.kind().value))
        for ref in ent.refs():
            dep_repr._edge_list.append(Edge(src=ent.id,
                                            dest=ref.target_ent.id,
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
    def from_und_db(cls, und_db) -> "DepRepr":
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
                                       dest=tar_ent.id(),
                                       kind=ref.kind().lvalueexpr(),
                                       lineno=lineno,
                                       col_offset=col_offset))
        return dep_repr
