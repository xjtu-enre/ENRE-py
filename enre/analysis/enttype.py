from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Dict, List

if TYPE_CHECKING:
    from enre.ent.entity import Class, Entity, NamespaceType


class EntType(ABC):
    @classmethod
    def get_bot(cls) -> "AnyType":
        return _any_type

    @abstractmethod
    def join(self, rhs: "EntType") -> "EntType":
        pass


class InstanceType(EntType):
    def __init__(self, class_ent: "Class"):
        self.class_ent = class_ent
        self._names: "NamespaceType"= class_ent.names

    @property
    def namespace(self) -> "NamespaceType":
        return self._names

    def join(self, rhs: "EntType") -> "EntType":
        ...


class ConstructorType(EntType):
    def __init__(self, class_ent: "Class"):
        self.class_ent = class_ent
        self._names: "NamespaceType" = class_ent.names

    @property
    def namespace(self) -> "NamespaceType":
        return self._names

    def to_class_type(self) -> InstanceType:
        return InstanceType(self.class_ent)

    def join(self, rhs: "EntType") -> "EntType":
        if isinstance(rhs, ConstructorType) and rhs.class_ent == self.class_ent:
            return self
        else:
            return EntType.get_bot()


# Every Module Entity is Module Type
class ModuleType(EntType):
    @classmethod
    def get_module_type(cls) -> "ModuleType":
        return _module_type

    def join(self, rhs: "EntType") -> "EntType":
        return EntType.get_bot()


class AnyType(EntType):
    def join(self, rhs: "EntType") -> "EntType":
        return _any_type


_any_type = AnyType()
_module_type = ModuleType()
