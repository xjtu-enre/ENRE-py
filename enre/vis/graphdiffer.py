import json
from collections import defaultdict
from pathlib import Path
from typing import List, Iterable, TypeVar, Optional, Dict, Tuple, IO

from vis.mapping import Mapping
from vis.representation import NodeTy, EdgeTy

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
        self._diff_nodes: Optional[List[NodeTy]] = None
        self._diff_edges: Optional[List[EdgeTy]] = None
        self._diff_ent_statistic: Optional[Dict] = None
        self._diff_dep_statistic: Optional[Dict] = None

    def diff_nodes(self) -> List[NodeTy]:
        if self._diff_nodes is not None:
            return self._diff_nodes
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
        if self._diff_edges is not None:
            return self._diff_edges
        diff_edge_list: List[EdgeTy] = []
        length = len(self.tar_graph.edge_list)
        for index, edge in enumerate(self.tar_graph.edge_list):
            print(f"processing: {index}/{length}")

            matched_edge = first_match(self.base_graph.edge_list,
                                       lambda e: self._mapping.is_same_edge(e, edge))
            if matched_edge is None:
                diff_edge_list.append(edge)
        return diff_edge_list

    def diff_statistic(self) -> Tuple[Dict, Dict]:
        if self._diff_edges is None:
            self.diff_edges()
        if self._diff_nodes is None:
            self.diff_nodes()
        diff_node_statistic = defaultdict(int)
        diff_edge_statistic = defaultdict(int)
        for node in self._diff_nodes:
            diff_node_statistic[node["ent_type"]] += 1
        for edge in self._diff_edges:
            diff_edge_statistic[edge["kind"]] += 1
        self._diff_ent_statistic = diff_node_statistic
        self._diff_dep_statistic = diff_edge_statistic
        return diff_node_statistic, diff_edge_statistic

    def dump_statistic(self, fp: IO):
        import csv
        writer = csv.writer(fp)
        
