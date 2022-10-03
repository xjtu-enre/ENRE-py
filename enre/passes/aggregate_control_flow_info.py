from typing import Optional, Iterable, Callable

from enre.cfg.Resolver import Resolver
from enre.cfg.HeapObject import HeapObject, ModuleObject, FunctionObject, ClassObject, InstanceMethodReference
from enre.analysis.analyze_manager import RootDB
from enre.cfg.module_tree import ModuleSummary, Scene, ClassSummary
from enre.ent.EntKind import RefKind
from enre.ent.entity import Module, Function, Class, Anonymous, Entity
from enre.ref.Ref import Ref


def get_target_ent(heap_obj: "HeapObject") -> Optional[Entity]:
    if isinstance(heap_obj, ModuleObject):
        return heap_obj.module_ent
    elif isinstance(heap_obj, FunctionObject):
        return heap_obj.func_ent
    elif isinstance(heap_obj, ClassObject):
        return heap_obj.class_ent
    elif isinstance(heap_obj, InstanceMethodReference):
        return heap_obj.func_obj.func_ent
    else:
        return None


def map_resolved_objs(heap_objs: "Iterable[HeapObject]") -> Iterable[Entity]:
    return (ent for ent in (get_target_ent(heap_obj) for heap_obj in heap_objs) if ent is not None)


def aggregate_cfg_info(root_db: "RootDB", resolver: "Resolver") -> None:
    print("aggregating cfg result to dependency")
    for file_path, module_db in root_db.tree.items():
        for ent in module_db.dep_db.ents:
            aggregated_expr = set()
            if ent in resolver.scene.summary_map:
                summary = resolver.scene.summary_map[ent]
                for ref in ent.refs():
                    if ref.ref_kind in [RefKind.CallKind, RefKind.UseKind]:
                        invoke_expr = ref.expr
                        if invoke_expr is not None and invoke_expr in summary.get_syntax_namespace():
                            aggregated_expr.add(invoke_expr)
                            name = summary.get_syntax_namespace()[invoke_expr]
                            resolved_objs = summary.get_object().namespace[name]
                            ref.resolved_targets.update(map_resolved_objs(resolved_objs))

                    if isinstance(ent, Class) and ref.ref_kind == RefKind.InheritKind:
                        assert isinstance(summary, ClassSummary)
                        ref.resolved_targets.update(map_resolved_objs(summary.get_object().inherits))

                for invoke in summary.get_invokes():
                    if not invoke.expr in aggregated_expr:
                        invoke_targets = resolver.get_store_able_value(invoke.target, summary.get_namespace())
                        for target in invoke_targets:
                            target_func: Function
                            if isinstance(target, FunctionObject):
                                target_func = target.func_ent
                            elif isinstance(target, InstanceMethodReference):
                                target_func = target.func_obj.func_ent
                            else:
                                continue
                            invoke_expr = invoke.expr
                            ent.add_ref(
                                Ref(RefKind.CallKind, target_func, invoke_expr.lineno, invoke_expr.col_offset, False, invoke_expr,
                                    set()))
