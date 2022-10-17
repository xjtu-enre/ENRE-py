import ast
import typing
from abc import abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, TypeAlias, Set, Iterable

from enre.ent.entity import Class, Function, Module

if typing.TYPE_CHECKING:
    from enre.cfg.module_tree import FunctionSummary, ClassSummary, ModuleSummary, Invoke, IndexableInfo


def update_if_not_contain_all(lhs: Set["HeapObject"], rhs: typing.Iterable["HeapObject"]) -> bool:
    # return True if all rhs objects have been already contained
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
    def write_field(self, name: str, objs: "ReadOnlyObjectSlot") -> bool:
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

    def write_field(self, name: str, objs: "ReadOnlyObjectSlot") -> bool:
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
                temp: "ObjectSlot" = set()
                base.get_member(name, temp)
                obj_slot.update(temp)
            return

    def write_field(self, name: str, objs: "ReadOnlyObjectSlot") -> bool:
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

    def write_field(self, name: str, objs: "ReadOnlyObjectSlot") -> bool:
        return update_if_not_contain_all(self.namespace[name], objs)

    def get_member(self, name: str, obj_slot: "ObjectSlot") -> None:
        get_attribute_from_class_instance(self, name, obj_slot)

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
        # We can't get member of function yet
        return

    def write_field(self, name: str, objs: "ReadOnlyObjectSlot") -> bool:
        # We can't write member of function yet
        return True

    def __hash__(self) -> int:
        return id(self)

    def representation(self) -> str:
        return f"FunctionObject: {self.func_ent.longname.longname}"

    def __str__(self) -> str:
        return self.representation()


@dataclass(frozen=True)
class InstanceMethodReference(HeapObject):
    func_obj: FunctionObject
    from_obj: "InstanceObject | IndexableObject | ConstantInstance"
    namespace: "NameSpace" = field(default_factory=lambda: defaultdict(set))
    depend_by: Set["ModuleSummary"] = field(default_factory=set)

    def write_field(self, name: str, objs: "ReadOnlyObjectSlot") -> bool:
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
class IndexableObject(HeapObject):
    """
    indexable builtin object like dict and list
    """
    info: typing.Optional[ClassObject]
    expr: typing.Optional[ast.expr]
    list_contents: typing.Set[HeapObject] = field(default_factory=set)
    namespace: "NameSpace" = field(default_factory=lambda: defaultdict(set))
    depend_by: Set["ModuleSummary"] = field(default_factory=set)

    def get_member(self, name: str, obj_slots: "ObjectSlot") -> None:
        get_attribute_from_class_instance(self, name, obj_slots)

    def write_field(self, name: str, objs: "ReadOnlyObjectSlot") -> bool:
        return update_if_not_contain_all(self.namespace[name], objs)

    def representation(self) -> str:
        return "ListObject: member list"

    def __hash__(self) -> int:
        return id(self)


@dataclass(frozen=True)
class ConstantInstance(HeapObject):
    """
    constant instance
    """
    info: typing.Optional[ClassObject]
    expr: ast.Constant | ast.Str
    namespace: "NameSpace" = field(default_factory=lambda: defaultdict(set))
    depend_by: Set["ModuleSummary"] = field(default_factory=set)

    def get_member(self, name: str, obj_slots: "ObjectSlot") -> None:
        get_attribute_from_class_instance(self, name, obj_slots)

    def write_field(self, name: str, objs: "ReadOnlyObjectSlot") -> bool:
        return update_if_not_contain_all(self.namespace[name], objs)

    def representation(self) -> str:
        return f"Constant :{self.expr.value.__repr__()}"

    def __hash__(self) -> int:
        return id(self)


ObjectSlot: TypeAlias = Set[HeapObject]
ReadOnlyObjectSlot: TypeAlias = Iterable[HeapObject]
NameSpace: TypeAlias = Dict[str, ObjectSlot]


def get_attribute_from_class_instance(instance: InstanceObject | IndexableObject | ConstantInstance, attr: str,
                                      obj_slot: "ObjectSlot") -> None:
    def extend_method_ref_is_not_exist(obj: "HeapObject", slot: "ObjectSlot") -> None:
        if isinstance(obj, FunctionObject):
            if not contain_same_ref(obj, instance, slot):
                slot.add(InstanceMethodReference(obj, instance))
                # todo: create instance method only when it's not exist already
        else:
            slot.add(obj)

    if attr in instance.namespace:
        obj_slot.update(instance.namespace[attr])
    else:
        cls_member: ObjectSlot = set()
        class_object: typing.Optional[ClassObject]
        if isinstance(instance, InstanceObject):
            class_object = instance.class_obj
        elif isinstance(instance, IndexableObject):
            class_object = instance.info
        elif isinstance(instance, ConstantInstance):
            class_object = instance.info
        else:
            assert False
        if class_object is not None:
            class_object.get_member(attr, cls_member)
            for obj in cls_member:
                extend_method_ref_is_not_exist(obj, obj_slot)


def contain_same_ref(obj1: FunctionObject, obj2: InstanceObject | IndexableObject | ConstantInstance,
                     slot: ObjectSlot) -> bool:
    for obj in slot:
        if isinstance(obj, InstanceMethodReference):
            if obj.func_obj == obj1 and obj.from_obj == obj2:
                return True
    return False


def is_dict_update(func: FunctionObject) -> bool:
    return func.func_ent.longname.name == "update"


def is_list_append(func: FunctionObject) -> bool:
    return func.func_ent.longname.name == "append"
