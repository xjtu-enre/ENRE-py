import typing
from abc import abstractmethod
from dataclasses import dataclass, field
from typing import Dict, TypeAlias, Set

from enre.ent.entity import Class, Function, Module

if typing.TYPE_CHECKING:
    from enre.cfg.module_tree import FunctionSummary, ClassSummary, ModuleSummary


class HeapObject:
    depend_by: Set["ModuleSummary"]

    @abstractmethod
    def get_member(self, name: str, obj_slots: "ObjectSlot") -> None:
        pass

    @abstractmethod
    def write_field(self, name: str, objs: "ObjectSlot") -> None:
        ...


class NameSpaceObject:
    @abstractmethod
    def get_namespace(self) -> "NameSpace":
        ...


@dataclass(frozen=True)
class ModuleObject(HeapObject, NameSpaceObject):
    module_ent: Module
    summary: "ModuleSummary"
    members: "NameSpace"
    depend_by: Set["ModuleSummary"] = field(default_factory=set)

    def get_member(self, name: str, obj_slot: "ObjectSlot") -> None:
        obj_slot.update(self.members[name])

    def write_field(self, name: str, objs: "ObjectSlot") -> None:
        self.members[name].update(objs)

    def get_namespace(self) -> "NameSpace":
        return self.members

    def __hash__(self) -> int:
        return id(self)


@dataclass(frozen=True)
class ClassObject(HeapObject, NameSpaceObject):
    class_ent: Class
    summary: "ClassSummary"
    members: "NameSpace"
    inherits: Set["ClassObject"] = field(default_factory=set)
    depend_by: Set["ModuleSummary"] = field(default_factory=set)

    def get_namespace(self) -> "NameSpace":
        return self.members

    def get_member(self, name: str, obj_slot: "ObjectSlot") -> None:
        obj_slot.update(self.members[name])

    def write_field(self, name: str, objs: "ObjectSlot") -> None:
        self.members[name].update(objs)

    def __hash__(self) -> int:
        return id(self)


@dataclass(frozen=True)
class InstanceObject(HeapObject, NameSpaceObject):
    class_obj: ClassObject
    members: "NameSpace"
    depend_by: Set["ModuleSummary"] = field(default_factory=set)

    def get_namespace(self) -> "NameSpace":
        return self.members

    def __hash__(self) -> int:
        return id(self)

    def write_field(self, name: str, objs: "ObjectSlot") -> None:
        self.members[name].update(objs)

    def get_member(self, name: str, obj_slot: "ObjectSlot") -> None:
        def extend_method_ref_is_not_exist(obj: "HeapObject", slot: "ObjectSlot") -> None:
            if isinstance(obj, FunctionObject):
                if not contain_same_ref(obj, self, slot):
                    slot.add(InstanceMethodReference(obj, self))
            else:
                slot.add(obj)

        if name in self.members:
            obj_slot.update(self.members[name])
        else:
            cls_member: ObjectSlot = set()
            self.class_obj.get_member(name, cls_member)
            for obj in cls_member:
                extend_method_ref_is_not_exist(obj, obj_slot)


@dataclass(frozen=True)
class FunctionObject(HeapObject, NameSpaceObject):
    func_ent: Function
    summary: "FunctionSummary"
    namespace: "NameSpace"
    return_slot: "ObjectSlot"
    depend_by: Set["ModuleSummary"] = field(default_factory=set)

    def get_namespace(self) -> "NameSpace":
        return self.namespace

    def get_member(self, name: str, obj_slot: "ObjectSlot") -> None:
        return

    def write_field(self, name: str, objs: "ObjectSlot") -> None:
        return

    def __hash__(self) -> int:
        return id(self)


@dataclass(frozen=True)
class InstanceMethodReference(HeapObject):
    func_obj: FunctionObject
    from_obj: InstanceObject
    depend_by: Set["ModuleSummary"] = field(default_factory=set)

    def write_field(self, name: str, objs: "ObjectSlot") -> None:
        return

    def get_member(self, name: str, obj_slot: "ObjectSlot") -> None:
        return

    def __hash__(self) -> int:
        return id(self)


ObjectSlot: TypeAlias = Set[HeapObject]
NameSpace: TypeAlias = Dict[str, ObjectSlot]


def contain_same_ref(obj1: FunctionObject, obj2: InstanceObject, slot: ObjectSlot) -> bool:
    for obj in slot:
        if isinstance(obj, InstanceMethodReference):
            if obj.func_obj == obj1 and obj.from_obj == obj2:
                return True
    return False
