from abc import ABC

from enre.ent.EntKind import RefKind
from enre.ent.entity import Entity


class Ref(ABC):
    ref_kind: RefKind

    target_ent: Entity

    lineno: int

    col_offset: int

    in_type_ctx: bool

    def __init__(self, ref_kind: RefKind, target_ent: Entity, lineno: int, colno: int, in_type_ctx: bool):
        ...

    def __eq__(self, other: object) -> bool:
        ...
