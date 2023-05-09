import ast
import copy
from abc import ABC, abstractmethod
from typing import List, TYPE_CHECKING, Tuple, TypeAlias, Optional

from enre.analysis.value_info import ValueInfo
from enre.cfg.module_tree import SummaryBuilder
from enre.ent.entity import Entity, Location, get_anonymous_ent

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

    @staticmethod
    def get_dummy_res():
        return SubEnvLookupResult([], False)


class SubEnv(ABC):

    def __init__(self, depth: int = 0) -> None:
        self.depth = depth

    def join(self, sub_env: "SubEnv") -> "ParallelSubEnv":
        return ParallelSubEnv(self, sub_env)

    @abstractmethod
    def __getitem__(self, name: str) -> SubEnvLookupResult:
        ...

    @abstractmethod
    def reset_bindings(self, name: str, value: ValueInfo, new_ent: Entity = None):
        ...

    @abstractmethod
    def create_continuous_bindings(self, pairs: "Bindings") -> "SubEnv":
        ...


class BasicSubEnv(SubEnv):
    def __init__(self, pairs: "Optional[Bindings]" = None):
        super().__init__(1)
        if pairs is None:
            pairs = []
        self._bindings_list = [pairs]

    def __getitem__(self, name: str) -> SubEnvLookupResult:
        for bindings in reversed(self._bindings_list):
            ret = []
            for n, binds in bindings:
                if n == name:
                    ret.extend(binds)
            if ret:
                return SubEnvLookupResult(ret, True)
        return SubEnvLookupResult([], False)

    def reset_bindings(self, name: str, value: ValueInfo, new_ent: Entity = None):
        flag = False
        old_binding = None
        for bindings in reversed(self._bindings_list):
            for n, binds in bindings:
                if n == name and not flag:
                    old_ent = binds[0][0]
                    old_value = binds[0][1]
                    if [(n, binds)] in self._bindings_list:
                        self._bindings_list.remove([(n, binds)])
                    assert old_ent is not None
                    assert old_value is not None
                    if not new_ent:
                        new_ent = old_ent
                    new_binding = [(name, [(new_ent, value)])]
                    old_binding = [(name, [(old_ent, old_value)])]
                    self.create_continuous_bindings(new_binding)
                    flag = True
                elif n == name and flag:
                    # remove old bindings
                    if [(n, binds)] in self._bindings_list:
                        # print(f"delete{(n, binds)}")
                        self._bindings_list.remove([(n, binds)])
        return old_binding

    def create_continuous_bindings(self, pairs: "Bindings") -> "SubEnv":
        self._bindings_list.append(pairs)
        return self

    def get_bindings_list(self):
        return self._bindings_list


class ParallelSubEnv(SubEnv):
    def __init__(self, b1: SubEnv, b2: SubEnv) -> None:
        super().__init__(max(b1.depth, b2.depth) + 1)
        self._branch1_sub_env = b1
        self._branch2_sub_env = b2

    def __getitem__(self, name: str) -> SubEnvLookupResult:
        look_up_res1 = self._branch1_sub_env[name]
        look_up_res2 = self._branch2_sub_env[name]
        is_must_found = look_up_res1.must_found or look_up_res2.must_found
        found_entities = look_up_res1.found_entities + look_up_res2.found_entities
        return SubEnvLookupResult(found_entities, is_must_found)

    def reset_bindings(self, name: str, value: ValueInfo, new_ent: Entity = None):
        look_up_res1 = self._branch1_sub_env[name]
        if look_up_res1.must_found:
            return self._branch1_sub_env.reset_bindings(name, value, new_ent)
        look_up_res2 = self._branch2_sub_env[name]
        if look_up_res2.must_found:
            return self._branch2_sub_env.reset_bindings(name, value, new_ent)
        return None

    def create_continuous_bindings(self, pairs: "Bindings") -> "SubEnv":
        new_sub_env = BasicSubEnv(pairs)
        return ContinuousSubEnv(self, new_sub_env)


class ContinuousSubEnv(SubEnv):
    def __init__(self, forward: SubEnv, backward: SubEnv) -> None:
        """
        Find identifier in backward environment. If we can't find the name, then find it in forward environment
        """
        super().__init__(1 + max(forward.depth, backward.depth))
        self._forward = forward
        self._backward = backward
        self.calling = False

    def __getitem__(self, name: str) -> SubEnvLookupResult:
        if self.calling:
            return SubEnvLookupResult.get_dummy_res()
        self.calling = True
        backward_lookup_res = self._backward[name]

        if backward_lookup_res.must_found:
            self.calling = False
            return backward_lookup_res
        else:
            forward_lookup_res = self._forward[name]
            found_entities = backward_lookup_res.found_entities + forward_lookup_res.found_entities
            self.calling = False
            return SubEnvLookupResult(found_entities, forward_lookup_res.must_found)

    def reset_bindings(self, name: str, value: ValueInfo, new_ent: Entity = None):
        backward_lookup_res = self._backward[name]
        if backward_lookup_res.must_found:
            return self._backward.reset_bindings(name, value, new_ent)
        else:
            return self._forward.reset_bindings(name, value, new_ent)

    def create_continuous_bindings(self, pairs: "Bindings") -> "SubEnv":
        self._backward = self._backward.create_continuous_bindings(pairs)
        return self


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

    def __getitem__(self, name: str) -> SubEnvLookupResult:
        ret = []
        for sub_env in reversed(self._sub_envs):
            lookup_res = sub_env[name]
            sub_ents = lookup_res.found_entities
            ret.extend(sub_ents)
            if lookup_res.must_found:
                return SubEnvLookupResult(ret, True)

        return SubEnvLookupResult(ret, False)

    def reset_binding_value(self, name: str, value: ValueInfo, new_ent: Entity = None) -> Optional["Bindings"]:
        ori_bindings: "Bindings"
        for sub_env in reversed(self._sub_envs):
            lookup_result = sub_env[name]
            if lookup_result.must_found:  # reset binding value
                reset_res = sub_env.reset_bindings(name, value, new_ent)
                if reset_res:
                    return reset_res
        return None

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

    def add_continuous_to_bottom(self, pairs: "Bindings") -> None:
        bottom_sub_env = self._sub_envs[0]
        non_duplicate = []
        for p in pairs:
            if p not in non_duplicate:
                non_duplicate.append(p)
        bottom_sub_env.create_continuous_bindings(non_duplicate)


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

    def __getitem__(self, name: str) -> SubEnvLookupResult:
        possible_ents: AbstractValue = []
        for scope_env in reversed(self.scope_envs):
            lookup_res = scope_env[name]
            ents_in_scope = lookup_res.found_entities
            possible_ents.extend(ents_in_scope)
            if lookup_res.must_found:
                return SubEnvLookupResult(possible_ents, True)
        return SubEnvLookupResult(possible_ents, False)

    def get_env(self):
        env: EntEnv = None
        for scope_env in self.scope_envs:
            if not env:
                env = EntEnv(scope_env)
            else:
                env.add_scope(scope_env)
        return env

    def get_env_copy(self):
        return copy.copy(self)





