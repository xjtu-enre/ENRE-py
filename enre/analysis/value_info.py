from abc import abstractmethod
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from enre.ent.entity import Class, Entity, NamespaceType


class ValueInfo:
    """ValueInfo contain the part of analyze result of an expression.

    ValueInfo of an expression could be changed during analyzing,
    when the analyzed expression corresponds to an entity whose
    analyze progress haven't finished.
    """

    @classmethod
    def get_any(cls) -> "AnyType":
        return _any_type

    @abstractmethod
    def join(self, rhs: "ValueInfo") -> "ValueInfo":
        pass


class InstanceType(ValueInfo):
    def __init__(self, class_ent: "Class"):
        self.class_ent = class_ent

    def lookup_attr(self, attr: str) -> List["Entity"]:
        return self.class_ent.get_attribute(attr)

    def join(self, rhs: "ValueInfo") -> "ValueInfo":
        ...


class ConstructorType(ValueInfo):
    def __init__(self, class_ent: "Class"):
        self.class_ent = class_ent

    def lookup_attr(self, attr: str) -> List["Entity"]:
        return self.class_ent.get_attribute(attr)

    def to_class_type(self) -> InstanceType:
        return InstanceType(self.class_ent)

    def join(self, rhs: "ValueInfo") -> "ValueInfo":
        if isinstance(rhs, ConstructorType) and rhs.class_ent == self.class_ent:
            return self
        else:
            return ValueInfo.get_any()


# Every Module Entity is Module Type
class ModuleType(ValueInfo):

    def __init__(self, names: "NamespaceType"):
        self._names = names

    @property
    def namespace(self) -> "NamespaceType":
        return self._names

    def join(self, rhs: "ValueInfo") -> "ValueInfo":
        return ValueInfo.get_any()


class PackageType(ValueInfo):
    def __init__(self, names: "NamespaceType"):
        self._names = names

    @property
    def namespace(self) -> "NamespaceType":
        return self._names

    def join(self, rhs: "ValueInfo") -> "ValueInfo":
        return ValueInfo.get_any()


class AnyType(ValueInfo):
    def join(self, rhs: "ValueInfo") -> "ValueInfo":
        return _any_type


_any_type = AnyType()
