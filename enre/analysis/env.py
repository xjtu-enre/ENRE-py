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
        ...

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
        self.TYPE_CHECKING = False

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
        for bindings in reversed(self._bindings_list):
            if len(bindings) == 0:
                self._bindings_list.remove(bindings)
        return old_binding

    def create_continuous_bindings(self, pairs: "Bindings") -> "SubEnv":
        self._bindings_list.append(pairs)
        return self

    def get_bindings_list(self):
        return self._bindings_list


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

    def get_sub_env(self) -> SubEnv:
        return self._sub_envs[-1]

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
        # print(f"---------------env ctx name: {self.get_ctx().longname.longname}-----------------------------")
        for sub_env in reversed(self._sub_envs):
            lookup_result = sub_env[name]
            if lookup_result.must_found:  # reset binding value
                reset_res = sub_env.reset_bindings(name, value, new_ent)
                if reset_res:
                    return reset_res
        return None

    def add_continuous(self, pairs: "Bindings") -> None:
        before = len(self)
        if len(self._sub_envs) == 0:
            print("len(self._sub_envs) == 0")
            return
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

    def get_scope_env(self):
        env: ScopeEnv = None
        for sub_env in self._sub_envs:
            if not env:
                env = ScopeEnv(self._ctx_ent, self._location, self._builder, self._class_ctx)
            else:
                env.add_sub_env(sub_env)
        return env

# ScopeEnvLookupResult: TypeAlias = List[Tuple[Entity, ValueInfo, ScopeEnv]]


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





