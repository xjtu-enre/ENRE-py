from abc import ABC

from ent.EntKind import RefKind
from ent.entity import Entity


class Ref(ABC):
    ref_kind: RefKind

    target_ent: Entity

    lineno: int

    col_offset: int

    def __init__(self, ref_kind: RefKind, target_ent: Entity, lineno: int, colno: int):
        ...

    def __eq__(self, other: object) -> bool:
        ...
