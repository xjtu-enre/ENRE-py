from collections import defaultdict
from pathlib import Path
from typing import Dict, Union, List

from vis.mapping import Mapping
from vis.representation import NodeTy, EdgeTy

ENTMAPPING = {
    "Module File": ["Module"],
    "Class": ["Class"],
    "Attribute": ["Class Attribute"],
    "Unresolved Attribute": ["Unresolved Attribute"],
    "Unknown Module": ["Unknown Module"],
    "Package": ["Package"],
    "Variable": ["Variable"],
    "Parameter": ["Parameter"],
    "Abstract Class": ["Class"]
}

DEPMAPPING = defaultdict(list, {
    "Import From": ["Import"],
    "Import": ["Import"],
    "Use": ["Use"]})


def get_node_by_id(id_num: int, node_list: List[NodeTy]) -> NodeTy:
    for n in node_list:
        if n["id"] == id_num:
            return n
    raise Exception(f"not included id {id_num}")


class UndMapping(Mapping):

    def __init__(self, root_dir: Path, node_list: List[NodeTy], und_node_list: List[NodeTy]):
        super(UndMapping, self).__init__()
        self._node_list: List[NodeTy] = node_list
        self._und_node_list: List[NodeTy] = und_node_list
        self._root_dir = root_dir

    def is_same_node(self, base_node: NodeTy, und_node: NodeTy) -> bool:
        und_node_kind = und_node["ent_type"]
        base_node_kind = base_node["ent_type"]
        if und_node_kind not in ENTMAPPING:
            return False
        if base_node_kind not in ENTMAPPING[und_node_kind]:
            return False
        if base_node_kind != "Module File":
            return und_node["longname"] == base_node["longname"]
        else:
            rel_path = Path(und_node["longname"]).relative_to(self._root_dir.parent)
            new_longname = ".".join((rel_path.name.removesuffix(".py")).split("\\"))
            return new_longname == und_node["longname"]

    def is_same_edge(self, base_edge: EdgeTy, und_edge: EdgeTy) -> bool:
        base_edge_kind = base_edge["kind"]
        und_edge_kind = und_edge["kind"]
        base_edge_lineno = base_edge["lineno"]
        und_edge_lineno = und_edge["lineno"]
        if und_edge_kind not in DEPMAPPING or base_edge_kind not in DEPMAPPING[und_edge_kind]:
            return False
        if base_edge_lineno != und_edge_lineno:
            return False
        base_src_node = get_node_by_id(base_edge["src"], self._node_list)
        base_dest_node = get_node_by_id(base_edge["dest"], self._node_list)
        und_src_node = get_node_by_id(und_edge["src"], self._und_node_list)
        und_dest_node = get_node_by_id(und_edge["dest"], self._und_node_list)
        return self.is_same_node(base_src_node, und_src_node) and \
               self.is_same_node(base_dest_node,und_dest_node)
