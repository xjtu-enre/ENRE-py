from typing import Callable, List, TypeVar, Generic

import neo4j


N = TypeVar("N")

class Graph(Generic[N]):
    class Node:
        def __init__(self):
            self.edges: "List[Graph.Node]"

    def __init__(self):
        self.nodes: "List[Graph.Node]"




def from_depDB(dep_db: "DepDB") -> Graph:
    ...


# coverage rate of surface to base
def graph_coverage(base: Graph, surface: Graph, same_node: Callable, same_edge: Callable) -> Graph:
    ...


from dep.DepDB import DepDB
