from abc import ABC
from dataclasses import dataclass

from ent.EntKind import RefKind
from ent.entity import Entity


@dataclass(frozen=True)
class Ref(ABC):
    ref_kind : RefKind
    target_ent: Entity
    lineno: int

    col_offset: int

    def __eq__(self, other: "Ref"):
        return isinstance(other, Ref) and \
               self.ref_kind == other.ref_kind and self.target_ent == other.target_ent \
               and self.lineno == other.lineno and self.col_offset == other.col_offset
