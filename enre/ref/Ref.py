from abc import ABC
from dataclasses import dataclass

from enre.ent.EntKind import RefKind
from enre.ent.entity import Entity


@dataclass(frozen=True)
class Ref(ABC):
    ref_kind : RefKind
    target_ent: Entity
    lineno: int

    col_offset: int

    in_type_ctx: bool
