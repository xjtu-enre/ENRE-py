import os
from pathlib import Path
from typing import List, Dict

from vis.mapping import Mapping
from vis.representation import NodeTy, EdgeTy

ENTMAPPING = {
    "Module File": ["Module"],
    "File": ["Module"],
    "Class": ["Class"],
    "Attribute": ["Class Attribute"],
    "Unresolved Attribute": ["Unresolved Attribute"],
    "Ambiguous Attribute": [],
    "Unknown Module": ["Unknown Module"],
    "Unknown Class": ["Unknown Variable"],
    "Unknown Variable": ["Unknown Variable"],
    "Package": ["Package"],
    "Function": ["Function"],
    "Variable": ["Variable", "Module Alias"],
    "Parameter": ["Parameter"],
    "Abstract Class": ["Class"],
    "Property": ["Function"]
}

DEPMAPPING = {
    "Import From": ["Import"],
    "Import": ["Import"],
    "Use": ["Use"]
}


def get_node_by_id(id_num: int, node_dict: Dict[int, NodeTy]) -> NodeTy:
    return node_dict[id_num]
    raise Exception(f"not included id {id_num}")


class UndMapping(Mapping):

    def __init__(self, root_dir: Path, node_list: List[NodeTy], und_node_list: List[NodeTy]):
        super(UndMapping, self).__init__()
        self._node_list: List[NodeTy] = node_list
        self._und_node_list: List[NodeTy] = und_node_list
        self._root_dir = root_dir
        self._node_dict: Dict[int, NodeTy] = dict()
        self._und_node_dict: Dict[int, NodeTy] = dict()
        self.initialize_node_dict()

    def is_same_node(self, base_node: NodeTy, und_node: NodeTy) -> bool:
        und_node_kind = und_node["ent_type"]
        base_node_kind = base_node["ent_type"]
        if und_node_kind not in ENTMAPPING:
            return False
        if ENTMAPPING[und_node_kind] == []:
            # for ignoring specific kind of entity
            return True

        if base_node_kind not in ENTMAPPING[und_node_kind]:
            return False
        if und_node_kind not in  ["Module File", "File"]:
            return und_node["longname"] == base_node["longname"]
        else:
            rel_path = Path(und_node["longname"]).relative_to(self._root_dir.parent.resolve())
            new_longname = ".".join((str(rel_path).replace(".py", "")).split(os.sep))
            return new_longname == base_node["longname"]

    def is_same_edge(self, base_edge: EdgeTy, und_edge: EdgeTy) -> bool:
        base_edge_kind = base_edge["kind"]
        und_edge_kind = und_edge["kind"]
        base_edge_lineno = base_edge["lineno"]
        und_edge_lineno = und_edge["lineno"]
        if und_edge_kind not in DEPMAPPING or base_edge_kind not in DEPMAPPING[und_edge_kind]:
            return False
        if base_edge_lineno != und_edge_lineno:
            return False
        base_src_node = get_node_by_id(base_edge["src"], self._node_dict)
        base_dest_node = get_node_by_id(base_edge["dest"], self._node_dict)
        und_src_node = get_node_by_id(und_edge["src"], self._und_node_dict)
        und_dest_node = get_node_by_id(und_edge["dest"], self._und_node_dict)
        return self.is_same_node(base_src_node, und_src_node) and \
               self.is_same_node(base_dest_node,und_dest_node)

    def initialize_node_dict(self):
        for node in self._node_list:
            self._node_dict[node["id"]] = node

        for node in self._und_node_list:
            self._und_node_dict[node["id"]] = node

