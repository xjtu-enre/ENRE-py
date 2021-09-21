from typing import Callable, List, TypeVar, Generic, Set

from ent.EntKind import RefKind
from ent.entity import Entity
from ref.Ref import Ref

N = TypeVar("N")

T = TypeVar("T")


class Node(Generic[N]):
    def __init__(self, raw_node: N):
        self.raw_node: N = raw_node
        self.edges: "List[Target]" = []

    def add_edge(self, target: "Target"):
        self.edges.append(target)


class Target(Generic[N, T]):
    def __init__(self, node: "Node[N]", kind: T):
        self.node = node
        self.edge_kind = kind


class Graph(Generic[N, T]):
    def __init__(self):
        self.nodes: "Set[Node[N]]" = set()

    def add_node(self, node: "Node[N]"):
        self.nodes.add(node)


def from_ent(ent: Entity) -> Node[Entity]:
    node = Node(ent)
    for ref in ent.refs():
        target = Target(Node(ref.target_ent), ref)
        node.add_edge(target)
    return node


def from_depDB(dep_db: "DepDB") -> Graph[Entity, Ref]:
    graph: Graph[Entity, Ref] = Graph()
    for ent in dep_db.ents:
        node = from_ent(ent)
        graph.add_node(node)

    return graph


# coverage rate of surface to base
def graph_coverage(base: Graph, surface: Graph, same_node: Callable, same_edge: Callable) -> Graph:
    ...


from dep.DepDB import DepDB
