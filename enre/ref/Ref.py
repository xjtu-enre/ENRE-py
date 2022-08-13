import ast
from abc import ABC
from dataclasses import dataclass, field
from typing import Optional, Set

from enre.ent.EntKind import RefKind
from enre.ent.entity import Entity


@dataclass(frozen=True)
class Ref(ABC):
    ref_kind: RefKind
    target_ent: Entity

    lineno: int

    col_offset: int

    in_type_ctx: bool

    expr: Optional[ast.expr]

    resolved_targets: Set[Entity] = field(default_factory=set)
    # not none if a reference's target entity is created by an evaluation
