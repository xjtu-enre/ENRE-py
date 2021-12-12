import ast
from abc import ABC
from typing import List

from ent.entity import Entity, Location


class SubEnv(ABC):

    def __init__(self, depth = 0):
        self.depth = depth

    def join(self, sub_env: "SubEnv"):
        return ParallelSubEnv(self, sub_env)

    def __getitem__(self, name: str):
        raise NotImplementedError


class BasicSubEnv(SubEnv):
    def __init__(self, pairs=None):
        super().__init__(1)
        if pairs is None:
            pairs = []
        self._pairs = pairs

    def __getitem__(self, name: str):
        ret = []
        for ent, ent_type in self._pairs:
            if ent.longname.name == name:
                ret.append((ent, ent_type))
        return [None] if ret == [] else ret


class ParallelSubEnv(SubEnv):
    def __init__(self, b1, b2):
        super().__init__(max(b1.depth, b2.depth) + 1)
        self._branch1_sub_env = b1
        self._branch2_sub_env = b2

    def __getitem__(self, name: str):
        ents_b1 = self._branch1_sub_env[name]
        ents_b2 = self._branch2_sub_env[name]
        return ents_b1 + ents_b2


class ContinuousSubEnv(SubEnv):
    def __init__(self, forward: SubEnv, backward: SubEnv):
        super().__init__(1 + max(forward.depth, backward.depth))
        # print(f"ContinuousSubEnv constructed, depth: {self.depth}")
        self._forward = forward
        self._backward = backward

    def __getitem__(self, name: str):
        backward_res = self._backward[name]
        # print(f"finding name {name} in env {self}")
        if None not in backward_res:
            return backward_res
        else:
            # print(f"name {name} not found continue find at {self._forward}")
            return backward_res + self._forward[name]


class OptionalSubEnv(SubEnv):
    def __init__(self, sub_env: SubEnv):
        super().__init__(sub_env.depth + 1)
        self._optional = sub_env

    def __getitem__(self, name: str):
        optional_ents = self._optional[name]
        return optional_ents + [None]


class Hook:
    def __init__(self, stmts: List[ast.stmt], scope_env: "ScopeEnv"):
        self.stmts: List[ast.stmt] = stmts
        self.scope_env: "ScopeEnv" = scope_env


class ScopeEnv:

    def add_hook(self, stmts: List[ast.stmt], scope_env: "ScopeEnv"):
        self._hooks.append(Hook(stmts, scope_env))

    def get_location(self):
        return self._location

    def get_hooks(self) -> List[Hook]:
        return self._hooks

    def __init__(self, ctx_ent: Entity, location: Location, class_ctx=None):
        self._ctx_ent = ctx_ent
        self._location = location
        self._class_ctx = class_ctx
        self._hooks = []
        self._sub_envs: List[BasicSubEnv] = [BasicSubEnv()]

    def add_sub_env(self, sub_env: SubEnv):
        self._sub_envs.append(sub_env)

    def pop_sub_env(self):
        return self._sub_envs.pop()

    def __len__(self):
        return len(self._sub_envs)

    def append_ent(self, ent, ent_type):
        self._sub_envs[-1].add(ent, ent_type)

    def get_ctx(self):
        return self._ctx_ent

    def get_class_ctx(self):
        return self._class_ctx

    def __getitem__(self, name: str):
        ret = []
        for sub_env in reversed(self._sub_envs):
            sub_ents = sub_env[name]
            ret.extend(sub_ents)
            if None not in sub_ents:
                return sub_ents

        return [x for x in ret if x is not None]

    def add_continuous(self, pairs):
        before = len(self)
        top_sub_env = self.pop_sub_env()
        non_duplicate = []
        for p in pairs:
            if p not in non_duplicate:
                non_duplicate.append(p)
        new_sub_env = BasicSubEnv(non_duplicate)
        continuous_env = ContinuousSubEnv(top_sub_env, new_sub_env)
        self.add_sub_env(continuous_env)
        after = len(self)
        assert before == after


class EntEnv:

    def get_scope(self, offset=0):
        return self.scope_envs[-(offset + 1)]

    def add_scope(self, scope_env: ScopeEnv):
        self.scope_envs.append(scope_env)

    def pop_scope(self):
        return self.scope_envs.pop()

    def add_sub_env(self, sub_env: SubEnv):
        self.scope_envs[-1].add_sub_env(sub_env)

    def pop_sub_env(self):
        return self.scope_envs[-1].pop_sub_env()

    def get_ctx(self):
        return self.get_scope().get_ctx()

    def get_class_ctx(self):
        for scope_env in reversed(self.scope_envs):
            if scope_env.get_class_ctx() is not None:
                return scope_env.get_class_ctx()
        return None

    def __init__(self, scope_env: ScopeEnv):
        self.scope_envs: List[ScopeEnv] = [scope_env]

    def __getitem__(self, name: str):
        for scope_env in reversed(self.scope_envs):
            ents_in_scope = scope_env[name]
            if len(ents_in_scope) != 0:
                return ents_in_scope
        return []