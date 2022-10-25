import ast
import functools
import itertools
from collections import defaultdict
from typing import Dict, Set, Sequence, Iterable, List, Optional, Tuple

from enre.cfg.call_graph import CallGraph
from enre.cfg.HeapObject import HeapObject, InstanceObject, FunctionObject, ObjectSlot, InstanceMethodReference, \
    ClassObject, NameSpaceObject, update_if_not_contain_all, ReadOnlyObjectSlot, IndexableObject, is_dict_update, \
    ConstantInstance, is_list_append
from enre.cfg.module_tree import ModuleSummary, FunctionSummary, Rule, NameSpace, ValueFlow, \
    VariableLocal, Temporary, FuncConst, Scene, Return, StoreAble, ClassConst, Invoke, ParameterLocal, FieldAccess, \
    ModuleConst, AddBase, PackageConst, ClassAttributeAccess, Constant, AddList, IndexAccess, IndexableInfo, \
    VariableOuter, Arguments
from enre.ent.entity import Class, UnknownModule, Entity


def is_object_of_type(cls: Class, lhs: HeapObject) -> bool:
    if isinstance(lhs, InstanceObject) and lhs.class_obj.class_ent == cls:
        return True
    elif isinstance(lhs, IndexableObject) and lhs.info and lhs.info.class_ent == cls:
        return True
    elif isinstance(lhs, ConstantInstance) and lhs.info and lhs.info.class_ent == cls:
        return True
    else:
        return False


def distill_object_of_type(lhs_slot: ObjectSlot, cls: Class) -> Iterable[HeapObject]:
    ret: List[HeapObject] = []
    # for obj in lhs_slot:
    #     if is_object_of_type(cls, obj):
    #         ret.append(obj)
    ret = list(filter(functools.partial(is_object_of_type, cls), lhs_slot))
    return ret


def distill_object_of_type_and_invoke_site(lhs_slot: ObjectSlot,
                                           cls: Class,
                                           invoke: Invoke) -> Iterable[InstanceObject]:
    ret = []
    for obj in lhs_slot:
        if isinstance(obj, InstanceObject) and obj.class_obj.class_ent == cls and obj.invoke == invoke:
            ret.append(obj)
    return ret


def distill_list_of_creation_site(lst_slot: ObjectSlot, expr: ast.expr) -> Iterable[IndexableObject]:
    ret = []
    for obj in lst_slot:
        if isinstance(obj, IndexableObject) and obj.expr == expr:
            ret.append(obj)
    return ret


class Resolver:
    scene: Scene

    module_object_dict: Dict[ModuleSummary, HeapObject]

    def __init__(self, scene: Scene) -> None:
        self.scene = scene
        self.module_object_dict = dict()
        self.work_list: List[ModuleSummary] = scene.summaries.copy()
        self.call_graph = CallGraph()
        self.current_module: Optional[Entity] = None
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
        self.current_module = module.get_ent()
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
        elif isinstance(rule, AddList):
            cls = rule.info.cls
            cls_obj: Optional[ClassObject]
            if cls is not None:
                obj_temp = self.scene.summary_map[cls].get_object()
                assert isinstance(obj_temp, ClassObject)
                cls_obj = obj_temp
            else:
                cls_obj = None
            return self.resolve_add_list(rule.lst, cls_obj, rule.expr, obj)
        else:
            assert False, f"unsupported rule type {rule.__class__}, object type {obj.__class__}"

    def resolve_function(self, summary: FunctionSummary) -> None:
        for rule in summary.rules:
            self.resolve_rule_in_singleton_object(rule, summary.get_object())

    def resolve_value_flow_namespace(self, rule: ValueFlow, namespace: NameSpace) -> bool:
        already_satisfied = True
        match rule.lhs:
            case VariableLocal() | Temporary() | ParameterLocal() as lhs:
                self.resolve_flow_into_object_slot(rule.rhs, namespace, namespace[lhs.name()])
            case VariableOuter() as lhs:
                lhs_object_slot = self.scene.summary_map[lhs.scope].get_namespace()[lhs.name()]
                self.resolve_flow_into_object_slot(rule.rhs, namespace, lhs_object_slot)

        match rule.lhs, rule.rhs:
            case (FieldAccess() as field_access, VariableLocal() | Temporary() | ParameterLocal() as rhs):
                already_satisfied = already_satisfied and self.abstract_store_field(field_access, namespace,
                                                                                    namespace[rhs.name()])

            case (FieldAccess() as field_access, FuncConst() as fc):
                already_satisfied = already_satisfied and self.abstract_store_field(field_access, namespace,
                                                                                    {self.get_const_object(fc)})
            case (IndexAccess() as index_access, VariableLocal() | Temporary() | ParameterLocal() as rhs):
                already_satisfied = already_satisfied and self.abstract_store_index(index_access.target, namespace,
                                                                                    namespace[rhs.name()])
            case (IndexAccess() as index_access, FuncConst() as fc):
                already_satisfied = already_satisfied and self.abstract_store_index(index_access.target, namespace,
                                                                                    {self.get_const_object(fc)})
        return already_satisfied

    def resolve_flow_into_object_slot(self, rhs_store: StoreAble, current_namespace: NameSpace,
                                      object_slot: ObjectSlot) -> bool:
        already_satisfied = True
        match rhs_store:
            case VariableLocal() | Temporary() | ParameterLocal() as rhs:
                """
                simple assignment
                """
                already_satisfied = already_satisfied and update_if_not_contain_all(object_slot,
                                                                                    current_namespace[rhs.name()])
            case VariableOuter() as rhs:
                rhs_object_slot = self.scene.summary_map[rhs.scope].get_namespace()[rhs.name()]
                already_satisfied = already_satisfied and update_if_not_contain_all(object_slot, rhs_object_slot)
            case Invoke() as invoke:
                """
                invoke function
                """
                target = invoke.target
                args = invoke.args
                already_satisfied = already_satisfied and self.abstract_call(invoke, target, args, current_namespace,
                                                                             object_slot)
            case FieldAccess() as field_access:
                already_satisfied = already_satisfied and update_if_not_contain_all(object_slot,
                                                                                    self.abstract_load(field_access,
                                                                                                       current_namespace))
            case IndexAccess() as index_access:
                already_satisfied = already_satisfied and \
                                    update_if_not_contain_all(object_slot,
                                                              self.abstract_load_index(index_access, current_namespace))
            case FuncConst() as fc:
                already_satisfied = already_satisfied and update_if_not_contain_all(object_slot,
                                                                                    {self.get_const_object(fc)})
            case Constant() as c:
                if cls := c.constant_cls:
                    cls_obj = self.scene.summary_map[cls].get_object()
                    assert isinstance(cls_obj, ClassObject)
                    same_type_obj = distill_object_of_type(object_slot, cls)
                    if not same_type_obj:
                        constant_instance: HeapObject = ConstantInstance(cls_obj, c.constant)
                        return update_if_not_contain_all(object_slot,
                                                         {constant_instance})
                already_satisfied = already_satisfied and update_if_not_contain_all(object_slot,
                                                                                    {})
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
                    already_satisfied = cls_obj.add_base(base_cls_obj) and already_satisfied
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

    def abstract_store_field(self, field_access: FieldAccess, namespace: NameSpace, rhs_slot: ObjectSlot) -> bool:
        objs = self.get_store_able_value(field_access.target, namespace)
        field = field_access.field
        already_satisfied = True
        for obj in objs:
            already_satisfied = already_satisfied and obj.write_field(field, rhs_slot)
        return already_satisfied

    def abstract_store_index(self, access_target: StoreAble, namespace: NameSpace, rhs_slot: ObjectSlot) -> bool:
        objs = self.get_store_able_value(access_target, namespace)
        return self.abstract_store_index_to_objects(objs, rhs_slot)

    def abstract_store_index_to_objects(self,
                                        objs: ReadOnlyObjectSlot,
                                        rhs_slot: ReadOnlyObjectSlot) -> bool:
        already_satisfied = True
        for obj in objs:
            if isinstance(obj, IndexableObject):
                already_satisfied = already_satisfied and update_if_not_contain_all(obj.list_contents, rhs_slot)
        return already_satisfied

    def resolve_return(self, rule: Return, obj: FunctionObject) -> bool:
        ret_value = self.get_store_able_value(rule.ret_value, obj.namespace)
        return update_if_not_contain_all(obj.return_slot, ret_value)

    def abstract_call(self,
                      invoke: Invoke,
                      target: StoreAble,
                      args: Arguments,
                      namespace: NameSpace,
                      lhs_slot: ObjectSlot) -> bool:
        positional_args_slot: Sequence[ReadOnlyObjectSlot] = \
            list(map(lambda x: self.get_store_able_value(x, namespace), args.args))
        keyword_args = list(map(lambda x: (x[0], self.get_store_able_value(x[1], namespace)), args.kwargs))
        match target:
            case FuncConst() as fc:
                func_obj = self.scene.summary_map[fc.func].get_object()
                assert isinstance(func_obj, FunctionObject)
                return update_if_not_contain_all(lhs_slot,
                                                 self.abstract_function_object_call(func_obj,
                                                                                    positional_args_slot,
                                                                                    keyword_args))
            case VariableLocal() | Temporary() | ParameterLocal() as v:
                all_satisfied = True
                for func in namespace[v.name()]:
                    all_satisfied = all_satisfied and self.abstract_object_call(lhs_slot, invoke, func,
                                                                                positional_args_slot, keyword_args,
                                                                                namespace)
                return all_satisfied
            case ClassConst() as cc:
                cls_obj = self.scene.summary_map[cc.cls].get_object()
                assert isinstance(cls_obj, ClassObject)
                if not distill_object_of_type_and_invoke_site(lhs_slot, cc.cls, invoke):
                    # if not contain instance of class, create new instance
                    return update_if_not_contain_all(lhs_slot,
                                                     {self.abstract_class_call(invoke, cls_obj, positional_args_slot,
                                                                               keyword_args, namespace)})
                else:
                    # if already contain instance of class, call initializer
                    # return True because no new instance is created, if an object is changed, the function changing the
                    # object responsible for adding dependencies to worklist
                    for obj in lhs_slot:
                        if isinstance(obj, InstanceObject):
                            if obj.class_obj.class_ent == cc.cls:
                                self.call_initializer_on_instance(obj.class_obj, obj, positional_args_slot,
                                                                  keyword_args, namespace)
                    return True

            case FieldAccess() as field_access:
                all_satisfied = True
                for func in self.abstract_load(field_access, namespace):
                    all_satisfied = all_satisfied and \
                                    self.abstract_object_call(lhs_slot, invoke, func, positional_args_slot,
                                                              keyword_args, namespace)
                return all_satisfied
            case ClassAttributeAccess() as class_attribute_access:
                class_ent = class_attribute_access.class_attribute.class_ent
                class_obj = self.scene.summary_map[class_ent].get_object()
                assert isinstance(class_obj, ClassObject)
                class_namespace = class_obj.get_namespace()
                all_satisfied = True
                for func in class_namespace[class_attribute_access.class_attribute.longname.name]:
                    all_satisfied = all_satisfied and self.abstract_object_call(lhs_slot, invoke, func,
                                                                                positional_args_slot, keyword_args,
                                                                                namespace)
                return all_satisfied
            case VariableOuter() as v:
                targets = self.scene.summary_map[v.scope].get_namespace()[v.name()]
                all_satisfied = True
                for func in targets:
                    all_satisfied = all_satisfied and self.abstract_object_call(lhs_slot, invoke, func,
                                                                                positional_args_slot, keyword_args,
                                                                                namespace)
                return all_satisfied
            case _:
                raise NotImplementedError(target.__class__.__name__)

    def abstract_object_call(self,
                             return_slot: ObjectSlot,
                             invoke: Invoke,
                             func: HeapObject,
                             args: Sequence[ReadOnlyObjectSlot],
                             kwargs: Sequence[Tuple[str, ReadOnlyObjectSlot]],
                             namespace: NameSpace) -> bool:
        return_values: Iterable[HeapObject]
        match func:
            case FunctionObject() as f:
                return_values = self.abstract_function_object_call(f, args, kwargs)
            case InstanceMethodReference() as ref:
                instance: HeapObject = ref.from_obj
                first_arg: List[ReadOnlyObjectSlot] = [{instance}]
                args_slots: List[ReadOnlyObjectSlot] = first_arg + list(args)
                return_values = self.abstract_function_object_call(ref.func_obj, args_slots, kwargs)
            case ClassObject() as c:
                if not (objs := distill_object_of_type_and_invoke_site(return_slot, c.class_ent, invoke)):
                    # create new object if the return slot doesn't contain object of same type and invoke site
                    return_values = {self.abstract_class_call(invoke, c, args, kwargs, namespace)}
                else:
                    # just invoke initializer on the object with same type and invoke site
                    for obj in objs:
                        self.call_initializer_on_instance(obj.class_obj, obj, args, kwargs, namespace)
                    return_values = {}
            case InstanceObject(i):
                # todo: call __call__
                return_values = []
            case IndexableObject():
                return_values = []
            case _:
                raise NotImplementedError(func.__class__.__name__)
        return update_if_not_contain_all(return_slot, return_values)

    def abstract_function_object_call(self,
                                      func_obj: FunctionObject,
                                      args: Sequence[ReadOnlyObjectSlot],
                                      kwargs: Sequence[Tuple[str, ReadOnlyObjectSlot]]) -> Iterable[HeapObject]:
        self.call_graph.add_call(self.current_module, func_obj.func_ent)
        target_summary = func_obj.summary
        # todo: pull parameter passing out, and add packing semantic in parameter passing
        if len(args) > len(target_summary.positional_para_list):
            return func_obj.return_slot
        next_index = 0
        while next_index < len(target_summary.positional_para_list) and next_index < len(args):
            # passing all positional argument
            parameter_name = target_summary.positional_para_list[next_index]
            arg = args[next_index]
            update_if_not_contain_all(func_obj.namespace[parameter_name], arg)
            next_index += 1

        while next_index < len(target_summary.positional_para_list):
            parameter_name = target_summary.positional_para_list[next_index]
            non_matched_kwargs = list(filter(lambda x: x[0] != parameter_name, kwargs))
            matched_kwargs = list(filter(lambda x: x[0] == parameter_name, kwargs))
            if matched_kwargs:
                kwargs = non_matched_kwargs
                update_if_not_contain_all(func_obj.namespace[parameter_name], matched_kwargs[0][1])
                next_index += 1
            else:
                break

        if func_obj.summary.var_para:
            var_para_objs = func_obj.namespace[func_obj.summary.var_para]
            while next_index < len(args):
                arg = args[next_index]
                self.abstract_store_index_to_objects(var_para_objs, arg)
                next_index += 1

        if func_obj.summary.kwarg:
            kw_para_objs = func_obj.namespace[func_obj.summary.kwarg]
            for key, arg in kwargs:
                self.abstract_store_index_to_objects(kw_para_objs, arg)

        self.handle_indexable_object_modify(func_obj, args)
        return func_obj.return_slot

    def handle_indexable_object_modify(self, func: FunctionObject, args: Sequence[ReadOnlyObjectSlot]) -> bool:
        if is_dict_update(func) and len(args) == 2:
            for container, in_coming_container in itertools.product(args[0], args[1]):
                if isinstance(container, IndexableObject) and isinstance(in_coming_container, IndexableObject):
                    return update_if_not_contain_all(container.list_contents, in_coming_container.list_contents)
        elif is_list_append(func) and len(args) == 2:
            for container, new_element in itertools.product(args[0], args[1]):
                if isinstance(container, IndexableObject):
                    return update_if_not_contain_all(container.list_contents, {new_element})
        return True

    def abstract_class_call(self, invoke: Invoke, cls: ClassObject, args: Sequence[ReadOnlyObjectSlot],
                            kwargs: Sequence[Tuple[str, ReadOnlyObjectSlot]],
                            namespace: NameSpace) -> HeapObject:
        self.call_graph.add_call(self.current_module, cls.class_ent)
        target_summary = cls.summary
        cls_obj = target_summary.get_object()
        instance: HeapObject = InstanceObject(cls_obj, defaultdict(set), invoke)
        self.call_initializer_on_instance(cls_obj, instance, args, kwargs, namespace)
        return instance

    def call_initializer_on_instance(self, cls_obj: ClassObject, instance: HeapObject,
                                     args: Sequence[ReadOnlyObjectSlot],
                                     kwargs: Sequence[Tuple[str, ReadOnlyObjectSlot]], namespace: NameSpace) -> None:
        initializer = cls_obj.namespace["__init__"]
        first_arg: List[ReadOnlyObjectSlot] = [{instance}]
        args_slots: List[ReadOnlyObjectSlot] = first_arg + list(args)
        for obj in initializer:
            if isinstance(obj, FunctionObject):
                self.abstract_function_object_call(obj, args_slots, kwargs)

    def add_all_dependencies(self, module: ModuleSummary) -> None:
        for dep in module.get_object().depend_by:
            if dep not in self.work_list:
                self.work_list.append(dep)

    def resolve_add_list(self, lst: StoreAble, cls: Optional[ClassObject], expr: ast.expr, obj: HeapObject) -> bool:
        match lst:
            case VariableLocal() | Temporary() | ParameterLocal() as v:
                lhs_slot = obj.namespace[v.name()]
                if distill_list_of_creation_site(lhs_slot, expr):
                    return True
                else:
                    lst_instance = IndexableObject(cls, expr)
                    return update_if_not_contain_all(lhs_slot, [lst_instance])
            case _:
                return True

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

    def get_store_able_value(self, store: StoreAble, namespace: NameSpace) -> Iterable[HeapObject]:
        match store:
            case VariableLocal() | Temporary() | ParameterLocal() as v:
                return namespace[v.name()]
            case VariableOuter() as v:
                return self.scene.summary_map[v.scope].get_namespace()[v.name()]
            case FuncConst() as fc:
                return {self.get_const_object(fc)}
            case ClassConst() as cc:
                return {self.get_const_object(cc)}
            case FieldAccess() as field_access:
                return self.abstract_load(field_access, namespace)
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
            case ClassAttributeAccess() as class_attribute_access:
                return self.get_class_attribute(class_attribute_access)
            case Constant():
                return set()
            case IndexAccess() as index_access:
                return self.abstract_load_index(index_access, namespace)
            case _:
                raise NotImplementedError(f"{store.__class__.__name__}")

    def abstract_load(self, field_access: FieldAccess, namespace: NameSpace) -> Iterable[HeapObject]:
        field = field_access.field
        match field_access.target:
            case VariableLocal() | Temporary() | ParameterLocal() as v:
                ret: Set[HeapObject] = set()
                for obj in namespace[v.name()]:
                    obj.get_member(field, ret)
                return ret
            case VariableOuter() as v:
                ret = set()
                for obj in self.scene.summary_map[v.scope].get_namespace()[v.name()]:
                    obj.get_member(field, ret)
                return ret
            case ClassConst() as cc:
                ret = set()
                self.scene.summary_map[cc.cls].get_object().get_member(field, ret)
                return ret
            case ModuleConst() as mod:
                if not isinstance(mod.mod, UnknownModule):
                    ret = set()
                    self.scene.summary_map[mod.mod].get_object().get_member(field, ret)
                    return ret
                else:
                    # todo: handle unknown module
                    return []
            case PackageConst() as p:
                # todo: handle package const
                return []
            case ClassAttributeAccess() as class_attribute_access:
                ret = set()
                class_ent = class_attribute_access.class_attribute.class_ent
                class_obj = self.scene.summary_map[class_ent].get_object()
                assert isinstance(class_obj, ClassObject)
                class_namespace = class_obj.get_namespace()
                for obj in class_namespace[class_attribute_access.class_attribute.longname.name]:
                    obj.get_member(field, ret)
                return ret
            case FuncConst() as f:
                return set()
            case Constant():
                return set()
            case _:
                raise NotImplementedError(f"{field_access.target.__class__.__name__}")

    def get_class_attribute(self, class_attribute_access: ClassAttributeAccess) -> Iterable[HeapObject]:
        class_ent = class_attribute_access.class_attribute.class_ent
        class_obj = self.scene.summary_map[class_ent].get_object()
        attribute_name = class_attribute_access.class_attribute.longname.name
        assert isinstance(class_obj, ClassObject)
        class_namespace = class_obj.get_namespace()
        return class_namespace[attribute_name]

    def abstract_load_index(self, index_access: IndexAccess, namespace: NameSpace) -> Iterable[HeapObject]:
        target_slot = self.get_store_able_value(index_access.target, namespace)
        return self.get_index_of_object_slot(target_slot)

    def get_index_of_object_slot(self, obj_slot: ReadOnlyObjectSlot) -> ReadOnlyObjectSlot:
        ret = set()
        for obj in obj_slot:
            if isinstance(obj, IndexableObject):
                ret.update(obj.list_contents)
            elif isinstance(obj, InstanceObject):
                next_methods: "ObjectSlot" = set()
                obj.get_member("__next__", next_methods)
                for method in next_methods:
                    if isinstance(method, InstanceMethodReference):
                        ret.update(self.abstract_function_object_call(method.func_obj, [[obj]], []))
                iter_methods: "ObjectSlot" = set()
                obj.get_member("__iter__", iter_methods)
                for method in iter_methods:
                    if isinstance(method, InstanceMethodReference):
                        self.abstract_function_object_call(method.func_obj, [[obj]], [])
        return ret
