import os
import re
from pathlib import Path
from typing import List, Dict

from enre.vis.mapping import Mapping
from enre.vis.representation import NodeTy, EdgeTy

ENTMAPPING = {
    "Module File": ["Module"],
    "File": ["Module"],
    "Class": ["Class"],
    "Attribute": ["Class Attribute"],
    "Unresolved Attribute": ["Unresolved Attribute", "Referenced Attribute"],
    "Ambiguous Attribute": ["Referenced Attribute", "Ambiguous Attribute"],
    "Unknown Module": ["Unknown Module"],
    "Unknown Class": ["Unknown Variable"],
    "Unknown Variable": ["Unknown Variable"],
    "Package": ["Package"],
    "Function": ["Function"],
    "Variable": ["Variable", "Module Alias", "Alias"],
    "LambdaParameter": ["LambdaParameter"],
    "Parameter": ["Parameter"],
    "Abstract Class": ["Class"],
    "Property": ["Function"]
}

DEPMAPPING = {
    "Import From": ["Import"],
    "Import": ["Import"],
    "Use": ["Use"],
    "Set": ["Set"]

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
        if und_node_kind in ["Module File", "File"]:
            rel_path = Path(und_node["longname"]).relative_to(self._root_dir.parent.resolve())
            new_longname = ".".join((str(rel_path).replace(".py", "")).split(os.sep))
            return new_longname == base_node["longname"]
        elif und_node_kind in ["LambdaParameter"]:
            base_new_longname = base_node["longname"]
            und_name = und_node["longname"]
            if "\\" in und_name:
                rel_path = Path(und_name).relative_to(self._root_dir.parent.resolve())
                und_name = ".".join((str(rel_path).replace(".py", "")).split(os.sep))
            return und_name == re.sub(r".\(\d+\)", "", base_new_longname)
        else:
            return und_node["longname"] == base_node["longname"]

    def is_same_edge(self, base_edge: EdgeTy, und_edge: EdgeTy) -> bool:
        base_edge_kind = base_edge["kind"]
        und_edge_kind = und_edge["kind"]
        base_edge_lineno = base_edge["lineno"]
        und_edge_lineno = und_edge["lineno"]
        in_dep_map = und_edge_kind in DEPMAPPING and base_edge_kind in DEPMAPPING[und_edge_kind]
        if not in_dep_map and base_edge_kind != und_edge_kind:
            return False
        # if base_edge_lineno != und_edge_lineno:
        #     return False
        base_src_node = get_node_by_id(base_edge["src"], self._node_dict)
        base_dest_node = get_node_by_id(base_edge["dest"], self._node_dict)
        und_src_node = get_node_by_id(und_edge["src"], self._und_node_dict)
        und_dest_node = get_node_by_id(und_edge["dest"], self._und_node_dict)
        return self.is_same_node(base_src_node, und_src_node) and \
               self.is_same_node(base_dest_node, und_dest_node)

    def initialize_node_dict(self) -> None:
        for node in self._node_list:
            self._node_dict[node["id"]] = node

        for node in self._und_node_list:
            self._und_node_dict[node["id"]] = node
