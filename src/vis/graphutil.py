from typing import Callable, List, Set, Dict


class EntityNode:
    def __init__(self, **raw_repr):
        self.raw_repr = raw_repr
        self.edges: "List[Target]" = []

    def add_edge(self, target: "Target"):
        self.edges.append(target)


class Target:
    def __init__(self, **raw_repr):
        self.node = EntityNode(raw_repr=raw_repr["node"])
        self.edge_kind = raw_repr["kind"]


class Graph():
    def __init__(self):
        self.nodes: "List[EntityNode]" = []

    def add_node(self, node: "EntityNode"):
        self.nodes.append(node)


def from_ent(raw_repr: Dict) -> EntityNode:
    node = EntityNode(longname=raw_repr["longname"],
                      kind=raw_repr["kind"])
    for ref in raw_repr["edges"]:
        target = Target(raw_repr=EntityNode(raw_repr=ref))
        node.add_edge(target)
    return node


# sub-graph of surface which not cover the base
def graph_coverage(
        base: Graph,
        surface: Graph,
        same_node: "Callable[[EntityNode, EntityNode], bool]",
        same_edge: "Callable[[EntityNode, EntityNode], bool]") -> Graph:
    graph = Graph()
    for node in surface.nodes:
        if base.nodes.count(node) >= 1:
            pass
        else:
            ...

