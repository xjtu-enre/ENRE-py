import ast
from typing import List, Optional, Tuple

from enre.ent.entity import Entity as Entity, Location as Location, Class
from enre.analysis.analyze_expr import EntType as EntType


class SubEnv:

    depth: int

    def join(self, sub_env: SubEnv) -> SubEnv: ...

    def add(self, target_ent: Entity, value: EntType) -> None: ...

    def __getitem__(self, name: str) -> List[Optional[Tuple[Entity, EntType]]]:
        ...


class BasicSubEnv(SubEnv):
    _pairs: List[Tuple[Entity, EntType]]

    def __init__(self, pairs: Optional[List[Tuple[Entity, EntType]]] = None):
        ...

    def add(self, target_ent: Entity, value: EntType) -> None:
        ...

    def __getitem__(self, name: str) -> List[Optional[Tuple[Entity, EntType]]]:
        ...


class ParallelSubEnv(SubEnv):
    _branch1_sub_env: SubEnv
    _branch2_sub_env: SubEnv

    def __init__(self, b1: SubEnv, b2: SubEnv):
        super(ParallelSubEnv, self).__init__()
        ...

    def __getitem__(self, name: str) -> List[Optional[Tuple[Entity, EntType]]]: ...


class ContinuousSubEnv(SubEnv):
    _forward: SubEnv
    _backward: SubEnv

    def __init__(self, forward: SubEnv, backward: SubEnv):
        super(ContinuousSubEnv, self).__init__()

    def __getitem__(self, name: str) -> List[Optional[Tuple[Entity, EntType]]]: ...


class OptionalSubEnv(SubEnv):
    _optional: SubEnv

    def __init__(self, sub_env: SubEnv):
        super().__init__()
        ...

    def __getitem__(self, name: str) -> List[Optional[Tuple[Entity, EntType]]]: ...


class ScopeEnv:
    class Hook:
        stmts: List[ast.stmt]
        scope_env: ScopeEnv

        def __init__(self, stmts: List[ast.stmt], scope_env: ScopeEnv) -> None: ...

    _hooks: List[Hook]
    _location: Location
    _sub_envs: List[SubEnv]
    _ctx_ent: Entity
    _class_ctx: Class

    def add_hook(self, stmts: List[ast.stmt], scope_env: ScopeEnv) -> None: ...

    def get_location(self) -> Location: ...

    def get_hooks(self) -> List[Hook]: ...

    def __init__(self, ctx_ent: Entity, location: Location, class_ctx: Optional[Class] = None) -> None:
        ...

    def __len__(self) -> int: ...

    def add_sub_env(self, sub_env: SubEnv) -> None: ...

    def pop_sub_env(self) -> SubEnv: ...

    def append_ent(self, ent: Entity, ent_type: EntType) -> None: ...

    def get_ctx(self) -> Entity: ...

    def get_class_ctx(self) -> Optional[Class]: ...

    def __getitem__(self, name: str) -> List[Tuple[Entity, EntType]]: ...

    def add_continuous(self, pairs: List[Tuple[Entity, EntType]]) -> None: ...


class EntEnv:

    def get_scope(self, offset: int = -1) -> ScopeEnv: ...

    def add_scope(self, scope_env: ScopeEnv) -> None: ...

    def pop_scope(self) -> ScopeEnv: ...

    def add_sub_env(self, sub_env: SubEnv) -> None: ...

    def pop_sub_env(self) -> SubEnv: ...

    def get_ctx(self) -> Entity: ...

    def get_class_ctx(self) -> Optional[Class]: ...

    scope_envs: List[ScopeEnv]

    def __init__(self, scope_env: ScopeEnv) -> None: ...

    def __getitem__(self, name: str) -> List[Tuple[Entity, EntType]]: ...
