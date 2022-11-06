import ast
from abc import ABC, abstractmethod
from typing import List, TYPE_CHECKING, Tuple, TypeAlias, Optional

from enre.cfg.module_tree import SummaryBuilder
from enre.ent.entity import Entity, Location

if TYPE_CHECKING:
    from enre.ent.entity import AbstractValue, Class

    Binding = Tuple[str, AbstractValue]
    Bindings: TypeAlias = List[Binding]


class SubEnvLookupResult:
    def __init__(self, found_entities: "AbstractValue", must_found: bool) -> None:
        self._found_entities: AbstractValue = found_entities
        self._must_found = must_found

    @property
    def found_entities(self) -> "AbstractValue":
        return self._found_entities

    @property
    def must_found(self) -> bool:
        return self._must_found


class SubEnv(ABC):

    def __init__(self, depth: int = 0) -> None:
        self.depth = depth

    def join(self, sub_env: "SubEnv") -> "ParallelSubEnv":
        return ParallelSubEnv(self, sub_env)

    @abstractmethod
    def get(self, name: str) -> SubEnvLookupResult:
        ...

    @abstractmethod
    def create_continuous_bindings(self, pairs: "Bindings") -> "SubEnv":
        ...


def get_from_bindings(name: str, bindings: "Bindings") -> "AbstractValue":
    ret = []
    for n, binds in bindings:
        if n == name:
            ret.extend(binds)
    return ret


class BasicSubEnv(SubEnv):
    def __init__(self, pairs: "Optional[Bindings]" = None):
        super().__init__(1)
        if pairs is None:
            pairs = []
        self._bindings_list = [pairs]

    def get(self, name: str) -> SubEnvLookupResult:
        for bindings in reversed(self._bindings_list):
            ret = get_from_bindings(name, bindings)
            if ret:
                return SubEnvLookupResult(ret, True)
        return SubEnvLookupResult([], False)

    def create_continuous_bindings(self, pairs: "Bindings") -> "SubEnv":
        self._bindings_list.append(pairs)
        return self


class ParallelSubEnv(SubEnv):
    def __init__(self, b1: SubEnv, b2: SubEnv) -> None:
        super().__init__(max(b1.depth, b2.depth) + 1)
        self._branch1_sub_env = b1
        self._branch2_sub_env = b2

    def get(self, name: str) -> SubEnvLookupResult:
        look_up_res1 = self._branch1_sub_env.get(name)
        look_up_res2 = self._branch2_sub_env.get(name)
        is_must_found = look_up_res1.must_found and look_up_res2.must_found
        found_entities = look_up_res1.found_entities + look_up_res2.found_entities
        return SubEnvLookupResult(found_entities, is_must_found)

    def create_continuous_bindings(self, pairs: "Bindings") -> "SubEnv":
        new_sub_env = BasicSubEnv(pairs)
        return ContinuousSubEnv(self, new_sub_env)


class ContinuousSubEnv(SubEnv):
    def __init__(self, forward: SubEnv, backward: SubEnv) -> None:
        """
        find identifier in backward environment, if can't find the name, then find it in forward environment
        """
        super().__init__(1 + max(forward.depth, backward.depth))
        # print(f"ContinuousSubEnv constructed, depth: {self.depth}")
        self._forward = forward
        self._backward = backward

    def get(self, name: str) -> SubEnvLookupResult:
        backward_lookup_res = self._backward.get(name)
        # print(f"finding name {name} in env {self}")
        if backward_lookup_res.must_found:
            return backward_lookup_res
        else:
            # print(f"name {name} not found continue find at {self._forward}")
            forward_lookup_res = self._forward.get(name)
            found_entities = backward_lookup_res.found_entities + forward_lookup_res.found_entities
            return SubEnvLookupResult(found_entities, forward_lookup_res.must_found)

    def create_continuous_bindings(self, pairs: "Bindings") -> "SubEnv":
        self._backward = self._backward.create_continuous_bindings(pairs)
        return self


class OptionalSubEnv(SubEnv):
    def __init__(self, sub_env: SubEnv) -> None:
        super().__init__(sub_env.depth + 1)
        self._optional = sub_env

    def get(self, name: str) -> SubEnvLookupResult:
        optional_lookup_res = self._optional.get(name)
        return SubEnvLookupResult(optional_lookup_res.found_entities, False)

    def create_continuous_bindings(self, pairs: "Bindings") -> "SubEnv":
        new_sub_env = BasicSubEnv(pairs)
        return ContinuousSubEnv(self, new_sub_env)


class Hook:
    def __init__(self, stmts: List[ast.stmt], scope_env: "ScopeEnv"):
        self.stmts: List[ast.stmt] = stmts
        self.scope_env: "ScopeEnv" = scope_env


class ScopeEnv:

    def add_hook(self, stmts: List[ast.stmt], scope_env: "ScopeEnv") -> None:
        self._hooks.append(Hook(stmts, scope_env))

    def get_location(self) -> Location:
        return self._location

    def get_hooks(self) -> List[Hook]:
        return self._hooks

    def __init__(self, ctx_ent: Entity, location: Location, builder: SummaryBuilder,
                 class_ctx: "Optional[Class]" = None) -> None:
        self._ctx_ent = ctx_ent
        self._location = location
        self._builder = builder
        self._class_ctx = class_ctx
        self._hooks: List[Hook] = []
        self._sub_envs: List[SubEnv] = [BasicSubEnv()]

    def get_builder(self) -> SummaryBuilder:
        return self._builder

    def add_sub_env(self, sub_env: SubEnv) -> None:
        self._sub_envs.append(sub_env)

    def pop_sub_env(self) -> SubEnv:
        return self._sub_envs.pop()

    def __len__(self) -> int:
        return len(self._sub_envs)

    def get_ctx(self) -> Entity:
        return self._ctx_ent

    def get_class_ctx(self) -> "Optional[Class]":
        return self._class_ctx

    def get(self, name: str) -> SubEnvLookupResult:
        ret = []
        for sub_env in reversed(self._sub_envs):
            lookup_res = sub_env.get(name)
            sub_ents = lookup_res.found_entities
            ret.extend(sub_ents)
            if lookup_res.must_found:
                return SubEnvLookupResult(ret, True)

        return SubEnvLookupResult(ret, False)

    def add_continuous(self, pairs: "Bindings") -> None:
        before = len(self)
        top_sub_env = self.pop_sub_env()
        non_duplicate = []
        for p in pairs:
            if p not in non_duplicate:
                non_duplicate.append(p)
        continuous_env = top_sub_env.create_continuous_bindings(non_duplicate)
        self.add_sub_env(continuous_env)
        after = len(self)
        assert before == after


# ScopeEnvLookupResult: TypeAlias = List[Tuple[Entity, ValueInfo, Scop-eEnv]]

class EntEnv:

    def get_scope(self, offset: int = 0) -> ScopeEnv:
        return self.scope_envs[-(offset + 1)]

    def add_scope(self, scope_env: ScopeEnv) -> None:
        self.scope_envs.append(scope_env)

    def pop_scope(self) -> ScopeEnv:
        return self.scope_envs.pop()

    def add_sub_env(self, sub_env: SubEnv) -> None:
        self.scope_envs[-1].add_sub_env(sub_env)

    def pop_sub_env(self) -> SubEnv:
        return self.scope_envs[-1].pop_sub_env()

    def get_ctx(self) -> Entity:
        return self.get_scope().get_ctx()

    def get_class_ctx(self) -> "Optional[Class]":
        for scope_env in reversed(self.scope_envs):
            if scope_env.get_class_ctx() is not None:
                return scope_env.get_class_ctx()
        return None

    def __init__(self, scope_env: ScopeEnv):
        self.scope_envs: List[ScopeEnv] = [scope_env]

    def get(self, name: str) -> SubEnvLookupResult:
        possible_ents: AbstractValue = []
        for scope_env in reversed(self.scope_envs):
            lookup_res = scope_env.get(name)
            ents_in_scope = lookup_res.found_entities
            possible_ents.extend(ents_in_scope)
            if lookup_res.must_found:
                return SubEnvLookupResult(possible_ents, True)
        return SubEnvLookupResult(possible_ents, False)
