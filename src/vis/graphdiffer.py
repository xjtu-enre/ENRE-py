import json
from pathlib import Path
from typing import List, Iterable, TypeVar

from vis.mapping import Mapping
from vis.representation import NodeTy, EdgeTy
import tqdm
A = TypeVar("A")


class Graph:
    def __init__(self, file_path: Path):
        graph_obj = json.loads(file_path.read_text())
        self.node_list: List[NodeTy] = graph_obj["Entities"]
        self.edge_list: List[EdgeTy] = graph_obj["Dependencies"]


def first_match(l: Iterable[A], f):
    return next((x for x in l if f(x)), None)


class GraphDiffer:
    def __init__(self, base_path: Path, tar_path: Path, mapping: Mapping):
        self._mapping = mapping
        self.base_graph = Graph(base_path)
        self.tar_graph = Graph(tar_path)

    def diff_nodes(self) -> List[NodeTy]:
        diff_node_list: List[NodeTy] = []
        length = len(self.tar_graph.node_list)
        for index, node in enumerate(self.tar_graph.node_list):
            print(f"processing: {index}/{length}")
            matched_node = first_match(self.base_graph.node_list,
                                       lambda n: self._mapping.is_same_node(n, node))
            if matched_node is None:
                diff_node_list.append(node)

        return diff_node_list

    def diff_edges(self) -> List[EdgeTy]:
        diff_edge_list: List[EdgeTy] = []
        length = len(self.tar_graph.edge_list)
        for index, edge in enumerate(self.tar_graph.edge_list):
            print(f"processing: {index}/{length}")

            matched_edge = first_match(self.base_graph.edge_list,
                                       lambda e: self._mapping.is_same_edge(e, edge))
            if matched_edge is None:
                diff_edge_list.append(edge)
        return diff_edge_list
