from collections import defaultdict
from typing import Dict, Set, Sequence, Iterable

from enre.cfg.HeapObject import HeapObject, InstanceObject, FunctionObject, ObjectSlot, InstanceMethodReference, \
    ClassObject, NameSpaceObject
from enre.cfg.module_tree import ModuleSummary, FunctionSummary, ClassSummary, Rule, NameSpace, ValueFlow, \
    VariableLocal, Temporary, FuncConst, Scene, Return, StoreAble, ClassConst, Invoke, ParameterLocal, FieldAccess
from enre.ent.entity import Class


def contain_object_of_type(lhs_slot: ObjectSlot, cls: Class) -> bool:
    for obj in lhs_slot:
        if isinstance(obj, InstanceObject):
            if obj.class_obj.class_ent == cls:
                return True
    return False


class Resolver:
    scene: Scene

    module_object_dict: Dict[ModuleSummary, HeapObject]

    def __init__(self, scene: Scene) -> None:
        self.scene = scene
        self.module_object_dict = dict()

    def resolve_all(self) -> None:
        for i in range(10):
            for module in self.scene.summaries:
                self.module_object_dict[module] = module.get_object()
                self.resolve_module(module)

    def resolve_module(self, module: ModuleSummary) -> None:
        for rule in module.rules:
            singleton = module.get_object()
            self.resolve_rules_in_singleton_object(rule, singleton)

    def resolve_function(self, summary: FunctionSummary) -> None:
        for rule in summary.rules:
            self.resolve_rules_in_singleton_object(rule, summary.get_object())

    def resolve_rules_in_singleton_object(self, rule: Rule, obj: HeapObject) -> None:
        if isinstance(rule, ValueFlow) and isinstance(obj, NameSpaceObject):
            self.resolve_value_flow_namespace(rule, obj.get_namespace())
        elif isinstance(rule, Return) and isinstance(obj, FunctionObject):
            self.resolve_return(rule, obj)

    def resolve_value_flow_namespace(self, rule: ValueFlow, namespace: NameSpace) -> None:
        match rule.lhs, rule.rhs:
            case VariableLocal() | Temporary() | ParameterLocal() as lhs, \
                 VariableLocal() | Temporary() | ParameterLocal() as rhs:
                """
                simple assignment
                """
                namespace[lhs.name()].update(namespace[rhs.name()])
            case (Temporary() | VariableLocal() as lhs, Invoke() as invoke):
                """
                invoke function
                """
                l_name = lhs.name()
                target = invoke.target
                args = invoke.args
                self.abstract_call(target, args, namespace, namespace[l_name])
            case (FieldAccess() as field_access, VariableLocal() | Temporary() | ParameterLocal() as rhs):
                self.abstract_store(field_access, namespace, namespace[rhs.name()])
            case (Temporary() | VariableLocal() as lhs, FieldAccess() as field_access):
                namespace[lhs.name()].update(self.abstract_load(field_access, namespace))
            case Temporary(l_name), FuncConst() as fc:
                namespace[l_name].add(self.get_const_object(fc))
            case VariableLocal() as v, FuncConst() as fc:
                namespace[v.name()].add(self.get_const_object(fc))

    def abstract_store(self, field_access: FieldAccess, namespace: NameSpace, rhs_slot: ObjectSlot) -> None:
        objs = self.get_store_able_value(field_access.target, namespace)
        field = field_access.field
        for obj in objs:
            obj.write_field(field, rhs_slot)

    def get_const_object(self, store: StoreAble) -> HeapObject:
        match store:
            case FuncConst() as fc:
                return self.scene.summary_map[fc.func].get_object()
            case ClassConst() as cc:
                return self.scene.summary_map[cc.cls].get_object()
            case _:
                raise NotImplementedError

    def resolve_return(self, rule: Return, summary: FunctionObject) -> None:
        match rule.ret_value:
            case VariableLocal(v):
                summary.return_slot.update(summary.namespace[v.longname.name])
            case Temporary(name):
                summary.return_slot.update(summary.namespace[name])
            case ParameterLocal(para) as p:
                summary.return_slot.update(summary.namespace[p.name()])
            case FuncConst() as fc:
                summary.return_slot.add(self.scene.summary_map[fc.func].get_object())
            case ClassConst() as cc:
                summary.return_slot.add(self.scene.summary_map[cc.cls].get_object())
            case _:
                assert False

    def abstract_call(self,
                      target: StoreAble,
                      args: Sequence[StoreAble],
                      namespace: NameSpace,
                      lhs_slot: ObjectSlot) -> None:
        args_slot: Sequence[ObjectSlot] = list(map(lambda x: self.get_store_able_value(x, namespace), args))
        match target:
            case FuncConst() as fc:
                lhs_slot.update(self.abstract_direct_function_call(fc, args, namespace))
            case VariableLocal() | Temporary() | ParameterLocal() as v:
                for func in namespace[v.name()]:
                    lhs_slot.update(self.abstract_object_call(func, args_slot, namespace))
            case ClassConst() as cc:
                cls_obj = self.scene.summary_map[cc.cls].get_object()
                assert isinstance(cls_obj, ClassObject)
                if not contain_object_of_type(lhs_slot, cc.cls):
                    lhs_slot.add(self.abstract_class_call(cls_obj, args_slot, namespace))
                else:
                    for obj in lhs_slot:
                        if isinstance(obj, InstanceObject):
                            if obj.class_obj.class_ent == cc.cls:
                                initializer = obj.class_obj.members["__init__"]
                                obj1: HeapObject = obj
                                args_slots: Sequence[ObjectSlot] = [{obj1}] + list(args_slot)
                                for obj in initializer:
                                    if isinstance(obj, FunctionObject):
                                        self.abstract_function_object_call(obj, args_slots, namespace)

            case FieldAccess() as field_access:
                for func in self.abstract_load(field_access, namespace):
                    lhs_slot.update(self.abstract_object_call(func, args_slot, namespace))
            case _:
                raise NotImplementedError(target.__class__.__name__)

    def abstract_object_call(self,
                             func: HeapObject,
                             args: Sequence[ObjectSlot],
                             namespace: NameSpace) -> Iterable[HeapObject]:
        match func:
            case FunctionObject() as f:
                return self.abstract_function_object_call(f, args, namespace)
            case InstanceMethodReference() as ref:
                instance: HeapObject = ref.from_obj
                args_slots: Sequence[ObjectSlot] = [{instance}] + list(args)
                return self.abstract_function_object_call(ref.func_obj, args_slots, namespace)
            case ClassObject() as c:
                return {self.abstract_class_call(c, args, namespace)}
            case InstanceObject(i):
                # todo: call __call__
                return []
            case _:
                raise NotImplementedError(func.__class__.__name__)

    def abstract_function_object_call(self,
                                      func_obj: FunctionObject,
                                      args: Sequence[ObjectSlot],
                                      namespace: NameSpace) -> Iterable[HeapObject]:
        target_summary = self.scene.summary_map[func_obj.func_ent]
        assert isinstance(target_summary, FunctionSummary)
        for index, arg in enumerate(args):
            parameter_name = target_summary.parameter_list[index]
            target_summary.get_namespace()[parameter_name].update(arg)
        return func_obj.return_slot

    def abstract_direct_function_call(self,
                                      func: FuncConst,
                                      args: Sequence[StoreAble],
                                      namespace: NameSpace) -> Iterable[HeapObject]:
        target_summary = self.scene.summary_map[func.func]
        assert isinstance(target_summary, FunctionSummary)
        for index, arg in enumerate(args):
            match arg:
                case VariableLocal() | Temporary() as v:
                    parameter_name = target_summary.parameter_list[index]
                    target_summary.get_namespace()[parameter_name].update(namespace[v.name()])
                case FuncConst() as fc:
                    parameter_name = target_summary.parameter_list[index]
                    target_summary.get_namespace()[parameter_name].add(self.get_const_object(fc))
        return target_summary.get_object().return_slot

    def abstract_class_call(self, cls: ClassObject, args: Sequence[ObjectSlot], namespace: NameSpace) -> HeapObject:
        target_summary = self.scene.summary_map[cls.class_ent]
        assert isinstance(target_summary, ClassSummary)
        cls_obj = target_summary.get_object()
        instance: HeapObject = InstanceObject(cls_obj, defaultdict(set))
        initializer = cls_obj.members["__init__"]

        args_slots: Sequence[ObjectSlot] = [{instance}] + list(args)
        for obj in initializer:
            if isinstance(obj, FunctionObject):
                self.abstract_function_object_call(obj, args_slots, namespace)
        return instance

    def abstract_load(self, field_access: FieldAccess, namespace: NameSpace) -> Iterable[HeapObject]:
        field = field_access.field
        match field_access.target:
            case VariableLocal() | Temporary() | ParameterLocal() as v:
                ret: Set[HeapObject] = set()
                for obj in namespace[v.name()]:
                    obj.get_member(field, ret)
                return ret
            case ClassConst() as cc:
                ret = set()
                self.scene.summary_map[cc.cls].get_object().get_member(field, ret)
                return ret
            case _:
                raise NotImplementedError

    def get_store_able_value(self, store: StoreAble, namespace: NameSpace) -> Set[HeapObject]:
        match store:
            case VariableLocal() | Temporary() | ParameterLocal() as v:
                return namespace[v.name()]
            case FuncConst() as fc:
                return {self.get_const_object(fc)}
            case ClassConst() as cc:
                return {self.get_const_object(cc)}
            case FieldAccess() as field_access:
                return set(self.abstract_load(field_access, namespace))
            case _:
                raise NotImplementedError
