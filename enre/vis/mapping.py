from abc import ABC
from typing import List

from enre.vis.representation import NodeTy, EdgeTy


class Mapping(ABC):
    def is_same_node(self, base_node: NodeTy, und_node: NodeTy) -> bool:
        ...

    def is_same_edge(self, base_edge: EdgeTy, und_edge: EdgeTy) -> bool:
        ...
