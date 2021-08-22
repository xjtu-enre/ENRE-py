import ast
from typing import List

from ent.entity import Entity, Location


class SubEnv:

    def __init__(self, pairs=None):
        if pairs is None:
            pairs = []
        self._pairs = pairs

    def join(self, sub_env: "SubEnv"):
        return SubEnv(self._pairs + sub_env._pairs)

    def add(self, target_ent: Entity, value):
        self._pairs.append((target_ent, value))

    def __getitem__(self, name: str):
        ret = []
        for ent, ent_type in self._pairs:
            if ent.longname.name == name:
                ret.append((ent, ent_type))
                return ret
        return ret


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
        self._sub_envs: List[SubEnv] = [SubEnv()]

    def add_sub_env(self, sub_env: SubEnv):
        self._sub_envs.append(sub_env)

    def pop_sub_env(self):
        return self._sub_envs.pop()

    def append_ent(self, ent, ent_type):
        self._sub_envs[-1].add(ent, ent_type)

    def get_ctx(self):
        return self._ctx_ent

    def get_class_ctx(self):
        return self._class_ctx

    def __getitem__(self, name: str):
        ret = []
        for sub_env in reversed(self._sub_envs):
            ret += sub_env[name]

        return ret


class EntEnv:
    def add(self, target_ent: Entity, value):
        self.scope_envs[-1].append_ent(target_ent, value)

    def get_scope(self):
        return self.scope_envs[-1]

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

    def get_class_scope(self):
        from ent.entity import Class
        for i in reversed(range(0, len(self.scope_envs))):
            if isinstance(self.scope_envs[i].get_ctx(), Class):
                return self.scope_envs[i - 1]

        raise RuntimeError("Try to get class scope while not in any of class context!")


def not_in_class_env(env):
    scope = env.get_scope()
    ctx_ent = scope.get_ctx()
    from ent.entity import Class
    return not isinstance(ctx_ent, Class)
