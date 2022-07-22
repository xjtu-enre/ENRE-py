import typing
from abc import abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Dict, TypeAlias, Set, Iterable

from enre.ent.entity import Class, Function, Module

if typing.TYPE_CHECKING:
    from enre.cfg.module_tree import FunctionSummary


class HeapObject:
    @abstractmethod
    def get_member(self, name: str, obj_slots: "ObjectSlot") -> None:
        pass

    @abstractmethod
    def write_field(self, name: str, objs: "ObjectSlot") -> None:
        ...


@dataclass(frozen=True)
class ModuleObject(HeapObject):
    module_ent: Module
    members: "NameSpace"

    def get_member(self, name: str, obj_slot: "ObjectSlot") -> None:
        obj_slot.update(self.members[name])

    def write_field(self, name: str, objs: "ObjectSlot") -> None:
        self.members[name].update(objs)

    def __hash__(self) -> int:
        return id(self)


@dataclass(frozen=True)
class ClassObject(HeapObject):
    class_ent: Class
    members: "NameSpace"

    def get_member(self, name: str, obj_slot: "ObjectSlot") -> None:
        obj_slot.update(self.members[name])

    def write_field(self, name: str, objs: "ObjectSlot") -> None:
        self.members[name].update(objs)

    def __hash__(self) -> int:
        return id(self)


@dataclass(frozen=True)
class InstanceObject(HeapObject):
    class_obj: ClassObject
    members: "NameSpace"

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
class FunctionObject(HeapObject):
    func_ent: Function
    summary: "FunctionSummary"

    def get_member(self, name: str, obj_slot: "ObjectSlot") -> None:
        return

    def write_field(self, name: str, objs: "ObjectSlot") -> None:
        return

@dataclass(frozen=True)
class InstanceMethodReference(HeapObject):
    func_obj: FunctionObject
    from_obj: InstanceObject

    def write_field(self, name: str, objs: "ObjectSlot") -> None:
        return
    def get_member(self, name: str, obj_slot: "ObjectSlot") -> None:
        return


ObjectSlot: TypeAlias = Set[HeapObject]
NameSpace: TypeAlias = Dict[str, ObjectSlot]


def contain_same_ref(obj1: FunctionObject, obj2: InstanceObject, slot: ObjectSlot) -> bool:
    for obj in slot:
        if isinstance(obj, InstanceMethodReference):
            if obj.func_obj == obj1 and obj.from_obj == obj2:
                return True
    return False
