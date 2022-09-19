import typing
from abc import abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, TypeAlias, Set, Iterable

from enre.ent.entity import Class, Function, Module

if typing.TYPE_CHECKING:
    from enre.cfg.module_tree import FunctionSummary, ClassSummary, ModuleSummary, Invoke


def update_if_not_contain_all(lhs: Set["HeapObject"], rhs: typing.Iterable["HeapObject"]) -> bool:
    if lhs.issuperset(rhs):
        return True
    else:
        lhs.update(rhs)
        return False


class HeapObject:
    depend_by: Set["ModuleSummary"]
    namespace: "NameSpace"

    @abstractmethod
    def get_member(self, name: str, obj_slots: "ObjectSlot") -> None:
        pass

    @abstractmethod
    def write_field(self, name: str, objs: "ObjectSlot") -> bool:
        ...

    @abstractmethod
    def representation(self) -> str:
        ...


class NameSpaceObject:
    @abstractmethod
    def get_namespace(self) -> "NameSpace":
        ...


@dataclass(frozen=True)
class ModuleObject(HeapObject, NameSpaceObject):
    module_ent: Module
    summary: "ModuleSummary"
    namespace: "NameSpace"
    depend_by: Set["ModuleSummary"] = field(default_factory=set)

    def get_member(self, name: str, obj_slot: "ObjectSlot") -> None:
        obj_slot.update(self.namespace[name])

    def write_field(self, name: str, objs: "ObjectSlot") -> bool:
        return update_if_not_contain_all(self.namespace[name], objs)

    def get_namespace(self) -> "NameSpace":
        return self.namespace

    def __hash__(self) -> int:
        return id(self)

    def representation(self) -> str:
        return f"ModuleObject: {self.module_ent.longname.longname}"


@dataclass(frozen=True)
class ClassObject(HeapObject, NameSpaceObject):
    class_ent: Class
    summary: "ClassSummary"
    namespace: "NameSpace"
    inherits: Set["ClassObject"] = field(default_factory=set)
    depend_by: Set["ModuleSummary"] = field(default_factory=set)

    def get_namespace(self) -> "NameSpace":
        return self.namespace

    def get_member(self, name: str, obj_slot: "ObjectSlot") -> None:
        this_class_member = self.namespace[name]
        obj_slot.update(this_class_member)
        if this_class_member:
            # if name already contained by class object, stop further lookup
            return
        else:
            for base in self.inherits:
                base.get_member(name, obj_slot)

    def write_field(self, name: str, objs: "ObjectSlot") -> bool:
        return update_if_not_contain_all(self.namespace[name], objs)

    def __hash__(self) -> int:
        return id(self)

    def add_base(self, obj: "ClassObject") -> bool:
        if obj in self.inherits:
            return True
        else:
            self.inherits.add(obj)
            return False

    def representation(self) -> str:
        return f"ClassObject: {self.class_ent.longname.longname}"


@dataclass(frozen=True)
class InstanceObject(HeapObject, NameSpaceObject):
    class_obj: ClassObject
    namespace: "NameSpace"
    invoke: "Invoke"
    depend_by: Set["ModuleSummary"] = field(default_factory=set)

    def get_namespace(self) -> "NameSpace":
        return self.namespace

    def __hash__(self) -> int:
        return hash((self.class_obj, self.invoke))

    def __eq__(self, other: object) -> bool:
        return isinstance(other, InstanceObject) and self.class_obj == other.class_obj and self.invoke == other.invoke

    def write_field(self, name: str, objs: "ObjectSlot") -> bool:
        return update_if_not_contain_all(self.namespace[name], objs)

    def get_member(self, name: str, obj_slot: "ObjectSlot") -> None:
        def extend_method_ref_is_not_exist(obj: "HeapObject", slot: "ObjectSlot") -> None:
            if isinstance(obj, FunctionObject):
                if not contain_same_ref(obj, self, slot):
                    slot.add(InstanceMethodReference(obj, self))
            else:
                slot.add(obj)

        if name in self.namespace:
            obj_slot.update(self.namespace[name])
        else:
            cls_member: ObjectSlot = set()
            self.class_obj.get_member(name, cls_member)
            for obj in cls_member:
                extend_method_ref_is_not_exist(obj, obj_slot)

    def representation(self) -> str:
        return f"InstanceObject: instance of {self.class_obj.class_ent.longname.longname}"


@dataclass(frozen=True)
class FunctionObject(HeapObject, NameSpaceObject):
    func_ent: Function
    summary: "FunctionSummary"
    namespace: "NameSpace" = field(default_factory=lambda: defaultdict(set))
    return_slot: "ObjectSlot" = field(default_factory=set)
    depend_by: Set["ModuleSummary"] = field(default_factory=set)

    def get_namespace(self) -> "NameSpace":
        return self.namespace

    def get_member(self, name: str, obj_slot: "ObjectSlot") -> None:
        return

    def write_field(self, name: str, objs: "ObjectSlot") -> bool:
        return update_if_not_contain_all(self.namespace[name], objs)

    def __hash__(self) -> int:
        return id(self)

    def representation(self) -> str:
        return f"FunctionObject: {self.func_ent.longname.longname}"


@dataclass(frozen=True)
class InstanceMethodReference(HeapObject):
    func_obj: FunctionObject
    from_obj: InstanceObject
    namespace: "NameSpace" = field(default_factory=lambda: defaultdict(set))
    depend_by: Set["ModuleSummary"] = field(default_factory=set)

    def write_field(self, name: str, objs: "ObjectSlot") -> bool:
        return update_if_not_contain_all(self.namespace[name], objs)

    def get_member(self, name: str, obj_slot: "ObjectSlot") -> None:
        obj_slot.update(self.namespace[name])

    def __hash__(self) -> int:
        return hash((self.func_obj, self.from_obj))

    def __eq__(self, other: object) -> bool:
        return isinstance(other,
                          InstanceMethodReference) and self.func_obj == other.func_obj and self.from_obj == other.from_obj

    def representation(self) -> str:
        return f"MethodReference: {self.func_obj.func_ent.longname.longname}"


@dataclass(frozen=True)
class ListObject:
    ...

ObjectSlot: TypeAlias = Set[HeapObject]
ReadOnlyObjectSlot: TypeAlias = Iterable[HeapObject]
NameSpace: TypeAlias = Dict[str, ObjectSlot]


def contain_same_ref(obj1: FunctionObject, obj2: InstanceObject, slot: ObjectSlot) -> bool:
    for obj in slot:
        if isinstance(obj, InstanceMethodReference):
            if obj.func_obj == obj1 and obj.from_obj == obj2:
                return True
    return False
