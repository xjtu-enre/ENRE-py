from collections import defaultdict
from typing import Dict, Set, Sequence, Iterable, List

from enre.cfg.HeapObject import HeapObject, InstanceObject, FunctionObject, ObjectSlot, InstanceMethodReference, \
    ClassObject, NameSpaceObject, update_if_not_contain_all
from enre.cfg.module_tree import ModuleSummary, FunctionSummary, Rule, NameSpace, ValueFlow, \
    VariableLocal, Temporary, FuncConst, Scene, Return, StoreAble, ClassConst, Invoke, ParameterLocal, FieldAccess, \
    ModuleConst, AddBase, PackageConst, ClassAttributeAccess
from enre.ent.entity import Class, UnknownModule


def distill_object_of_type_and_invoke_site(lhs_slot: ObjectSlot,
                                           cls: Class,
                                           invoke: Invoke) -> Iterable[InstanceObject]:
    ret = []
    for obj in lhs_slot:
        if isinstance(obj, InstanceObject) and obj.class_obj == cls and obj.invoke == invoke:
            ret.append(obj)
    return ret


class Resolver:
    scene: Scene

    module_object_dict: Dict[ModuleSummary, HeapObject]

    def __init__(self, scene: Scene) -> None:
        self.scene = scene
        self.module_object_dict = dict()
        self.work_list: List[ModuleSummary] = scene.summaries.copy()
        # todo: create work_list by module calling dependency

    def do_analysis(self) -> None:
        current_module = self.work_list.pop(0)
        while self.work_list:
            self.resolve_module(current_module)
            current_module = self.work_list.pop()
            already_satisfied = self.resolve_module(current_module)
            if not already_satisfied:
                # if some namespace changed, add all module depends on it to work list
                for m in current_module.get_object().depend_by:
                    if m not in self.work_list:
                        self.work_list.append(m)

    def do_analysis_chaotic(self) -> None:
        while True:
            all_satisfied = True
            for module in self.work_list:
                satisfied = self.resolve_module(module)
                all_satisfied = all_satisfied and satisfied
            if all_satisfied:
                break

    def resolve_all(self) -> None:
        for i in range(10):
            for module in self.scene.summaries:
                self.module_object_dict[module] = module.get_object()
                self.resolve_module(module)

    def resolve_module(self, module: ModuleSummary) -> bool:
        all_satisfied = True
        for rule in module.rules:
            singleton = module.get_object()
            rule_satisfied: bool = self.resolve_rule_in_singleton_object(rule, singleton)
            all_satisfied = all_satisfied and rule_satisfied
        return all_satisfied

    def resolve_rule_in_singleton_object(self, rule: Rule, obj: HeapObject) -> bool:
        if isinstance(rule, ValueFlow) and isinstance(obj, NameSpaceObject):
            return self.resolve_value_flow_namespace(rule, obj.get_namespace())
        elif isinstance(rule, Return) and isinstance(obj, FunctionObject):
            return self.resolve_return(rule, obj)
        elif isinstance(rule, AddBase):
            return self.resolve_add_base(obj, rule.cls, rule.bases)
        else:
            assert False, f"unsupported rule type {rule.__class__}, object type {obj.__class__}"

    def resolve_function(self, summary: FunctionSummary) -> None:
        for rule in summary.rules:
            self.resolve_rule_in_singleton_object(rule, summary.get_object())

    def resolve_value_flow_namespace(self, rule: ValueFlow, namespace: NameSpace) -> bool:
        already_satisfied = True
        match rule.lhs, rule.rhs:
            case VariableLocal() | Temporary() | ParameterLocal() as lhs, \
                 VariableLocal() | Temporary() | ParameterLocal() as rhs:
                """
                simple assignment
                """
                already_satisfied = already_satisfied and update_if_not_contain_all(namespace[lhs.name()],
                                                                                    namespace[rhs.name()])
            case (Temporary() | VariableLocal() as lhs, Invoke() as invoke):
                """
                invoke function
                """
                l_name = lhs.name()
                target = invoke.target
                args = invoke.args
                already_satisfied = already_satisfied and self.abstract_call(invoke, target, args, namespace,
                                                                             namespace[l_name])
            case (FieldAccess() as field_access, VariableLocal() | Temporary() | ParameterLocal() as rhs):
                already_satisfied = already_satisfied and self.abstract_store(field_access, namespace,
                                                                              namespace[rhs.name()])
            case (Temporary() | VariableLocal() as lhs, FieldAccess() as field_access):
                already_satisfied = already_satisfied and update_if_not_contain_all(namespace[lhs.name()],
                                                                                    self.abstract_load(field_access,
                                                                                                       namespace))
            case Temporary(l_name), FuncConst() as fc:
                already_satisfied = already_satisfied and update_if_not_contain_all(namespace[l_name],
                                                                                    {self.get_const_object(fc)})
            case VariableLocal() as v, FuncConst() as fc:
                already_satisfied = already_satisfied and update_if_not_contain_all(namespace[v.name()],
                                                                                    {self.get_const_object(fc)})
        return already_satisfied

    def resolve_add_base(self, namespace_obj: HeapObject, cls: ClassConst, bases: Sequence[StoreAble]) -> bool:
        cls_obj = self.scene.summary_map[cls.cls].get_object()
        assert isinstance(cls_obj, ClassObject)
        already_satisfied = True
        for base in bases:
            match base:
                case ClassConst() as c:
                    base_cls_obj = self.scene.summary_map[c.cls].get_object()
                    assert isinstance(base_cls_obj, ClassObject)
                    already_satisfied = already_satisfied and cls_obj.add_base(base_cls_obj)
                case VariableLocal() | Temporary() | ParameterLocal() as v:
                    base_cls_objs = namespace_obj.namespace[v.name()]
                    for base_cls_obj in base_cls_objs:
                        if isinstance(base_cls_obj, ClassObject):
                            already_satisfied = already_satisfied and cls_obj.add_base(base_cls_obj)
                case _:
                    """
                    just do nothing
                    """
        return already_satisfied

    def abstract_store(self, field_access: FieldAccess, namespace: NameSpace, rhs_slot: ObjectSlot) -> bool:
        objs = self.get_store_able_value(field_access.target, namespace)
        field = field_access.field
        already_satisfied = True
        for obj in objs:
            already_satisfied = already_satisfied and obj.write_field(field, rhs_slot)
        return already_satisfied

    def get_const_object(self, store: StoreAble) -> HeapObject:
        match store:
            case FuncConst() as fc:
                return self.scene.summary_map[fc.func].get_object()
            case ClassConst() as cc:
                return self.scene.summary_map[cc.cls].get_object()
            case ModuleConst() as m:
                return self.scene.summary_map[m.mod].get_object()
            case _:
                raise NotImplementedError

    def resolve_return(self, rule: Return, obj: FunctionObject) -> bool:
        match rule.ret_value:
            case VariableLocal(v):
                return update_if_not_contain_all(obj.return_slot, obj.namespace[v.longname.name])
            case Temporary(name):
                return update_if_not_contain_all(obj.return_slot, obj.namespace[name])
            case ParameterLocal() as p:
                return update_if_not_contain_all(obj.return_slot, obj.namespace[p.name()])
            case FuncConst() as fc:
                return update_if_not_contain_all(obj.return_slot, {self.scene.summary_map[fc.func].get_object()})
            case ClassConst() as cc:
                return update_if_not_contain_all(obj.return_slot, {self.scene.summary_map[cc.cls].get_object()})
            case ModuleConst() as m:
                if not isinstance(m.mod, UnknownModule):
                    return update_if_not_contain_all(obj.return_slot, {self.scene.summary_map[m.mod].get_object()})
                else:
                    return True
            case _:
                raise NotImplementedError(f"{rule.ret_value}")

    def abstract_call(self,
                      invoke: Invoke,
                      target: StoreAble,
                      args: Sequence[StoreAble],
                      namespace: NameSpace,
                      lhs_slot: ObjectSlot) -> bool:
        args_slot: Sequence[ObjectSlot] = list(map(lambda x: self.get_store_able_value(x, namespace), args))
        match target:
            case FuncConst() as fc:
                func_obj = self.scene.summary_map[fc.func].get_object()
                assert isinstance(func_obj, FunctionObject)
                return update_if_not_contain_all(lhs_slot,
                                                 self.abstract_function_object_call(func_obj, args_slot, namespace))
            case VariableLocal() | Temporary() | ParameterLocal() as v:
                all_satisfied = True
                for func in namespace[v.name()]:
                    all_satisfied = all_satisfied and self.abstract_object_call(lhs_slot, invoke, func, args_slot,
                                                                                namespace)
                return all_satisfied
            case ClassConst() as cc:
                cls_obj = self.scene.summary_map[cc.cls].get_object()
                assert isinstance(cls_obj, ClassObject)
                if not distill_object_of_type_and_invoke_site(lhs_slot, cc.cls, invoke):
                    # if not contain instance of class, create new instance
                    return update_if_not_contain_all(lhs_slot,
                                                     {self.abstract_class_call(invoke, cls_obj, args_slot, namespace)})
                else:
                    # if already contain instance of class, call initializer
                    # return True because no new instance is created, if an object is changed, the function changing the
                    # object responsible for adding dependencies to worklist
                    for obj in lhs_slot:
                        if isinstance(obj, InstanceObject):
                            if obj.class_obj.class_ent == cc.cls:
                                self.call_initializer_on_instance(obj.class_obj, obj, args_slot, namespace)
                    return True

            case FieldAccess() as field_access:
                all_satisfied = True
                for func in self.abstract_load(field_access, namespace):
                    all_satisfied = all_satisfied and \
                                    self.abstract_object_call(lhs_slot, invoke, func, args_slot, namespace)
                return all_satisfied
            case ClassAttributeAccess() as class_attribute_access:
                class_ent = class_attribute_access.class_attribute.class_ent
                class_obj = self.scene.summary_map[class_ent].get_object()
                assert isinstance(class_obj, ClassObject)
                class_namespace = class_obj.get_namespace()
                all_satisfied = True
                for func in class_namespace[class_attribute_access.class_attribute.longname.name]:
                    all_satisfied = all_satisfied and self.abstract_object_call(lhs_slot, invoke, func, args_slot,
                                                                                namespace)
                return all_satisfied
            case _:
                raise NotImplementedError(target.__class__.__name__)

    def abstract_object_call(self,
                             return_slot: ObjectSlot,
                             invoke: Invoke,
                             func: HeapObject,
                             args: Sequence[ObjectSlot],
                             namespace: NameSpace) -> bool:
        return_values: Iterable[HeapObject]
        match func:
            case FunctionObject() as f:
                return_values = self.abstract_function_object_call(f, args, namespace)
            case InstanceMethodReference() as ref:
                instance: HeapObject = ref.from_obj
                args_slots: Sequence[ObjectSlot] = [{instance}] + list(args)
                return_values = self.abstract_function_object_call(ref.func_obj, args_slots, namespace)
            case ClassObject() as c:
                if not (objs := distill_object_of_type_and_invoke_site(return_slot, c.class_ent, invoke)):
                    # create new object if the return slot doesn't contain object of same type and invoke site
                    return_values = {self.abstract_class_call(invoke, c, args, namespace)}
                else:
                    # just invoke initializer on the object with same type and invoke site
                    for obj in objs:
                        self.call_initializer_on_instance(obj.class_obj, obj, args, namespace)
                    return_values = {}
            case InstanceObject(i):
                # todo: call __call__
                return_values = []
            case _:
                raise NotImplementedError(func.__class__.__name__)
        return update_if_not_contain_all(return_slot, return_values)

    def abstract_function_object_call(self,
                                      func_obj: FunctionObject,
                                      args: Sequence[ObjectSlot],
                                      namespace: NameSpace) -> Iterable[HeapObject]:
        target_summary = func_obj.summary
        # todo: pull parameter passing out, and add packing semantic in parameter passing
        if len(args) != len(target_summary.parameter_list):
            return func_obj.return_slot
        for index, arg in enumerate(args):
            parameter_name = target_summary.parameter_list[index]
            update_if_not_contain_all(func_obj.namespace[parameter_name], arg)
        return func_obj.return_slot

    def abstract_class_call(self, invoke: Invoke, cls: ClassObject, args: Sequence[ObjectSlot],
                            namespace: NameSpace) -> HeapObject:
        target_summary = cls.summary
        cls_obj = target_summary.get_object()
        instance: HeapObject = InstanceObject(cls_obj, defaultdict(set), invoke)
        self.call_initializer_on_instance(cls_obj, instance, args, namespace)
        return instance

    def call_initializer_on_instance(self, cls_obj: ClassObject, instance: HeapObject,
                                     args: Sequence[ObjectSlot], namespace: NameSpace) -> None:
        initializer = cls_obj.members["__init__"]
        args_slots: Sequence[ObjectSlot] = [{instance}] + list(args)
        for obj in initializer:
            if isinstance(obj, FunctionObject):
                self.abstract_function_object_call(obj, args_slots, namespace)

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
            case ModuleConst() as m:
                if not isinstance(m.mod, UnknownModule):
                    # todo: build model for unknown module
                    return {self.get_const_object(m)}
                else:
                    return set()
            case PackageConst() as p:
                return set()
                # todo: implement package object
                return {self.get_const_object(p)}
            case _:
                raise NotImplementedError(f"{store.__class__.__name__}")

    def add_all_dependencies(self, module: ModuleSummary) -> None:
        for dep in module.get_object().depend_by:
            if dep not in self.work_list:
                self.work_list.append(dep)
