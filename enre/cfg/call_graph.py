import ast
from collections import defaultdict
from dataclasses import dataclass
from typing import Set, Dict, Iterable, Optional

from enre.ent.entity import Entity


class CallGraph:
    sources: Set[Entity]
    graph: Dict[Entity, Set[Entity]]

    def __init__(self) -> None:
        self.sources = set()
        self.graph: Dict[Entity, Set[Entity]] = defaultdict(set)

    def add_call(self, source: Optional[Entity], target: Entity) -> None:
        if not source:
            return
        self.sources.add(source)
        self.graph[source].add(target)
