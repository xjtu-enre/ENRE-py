from typing import Optional, Iterable, Callable

from enre.cfg.HeapObject import HeapObject, ModuleObject, FunctionObject, ClassObject, InstanceMethodReference
from enre.analysis.analyze_manager import RootDB
from enre.cfg.module_tree import ModuleSummary, Scene, ClassSummary
from enre.ent.EntKind import RefKind
from enre.ent.entity import Module, Function, Class, Anonymous, Entity


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


def aggregate_cfg_info(root_db: "RootDB", scene: "Scene") -> None:
    for file_path, module_db in root_db.tree.items():
        for ent in module_db.dep_db.ents:
            for ref in ent.refs():
                if ref.ref_kind in [RefKind.CallKind, RefKind.UseKind]:
                    if isinstance(ent, (Class, Function, Module)):
                        summary = scene.summary_map[ent]
                        expr = ref.expr
                        if expr is not None and expr in summary.get_syntax_namespace():
                            name = summary.get_syntax_namespace()[expr]
                            resolved_objs = summary.get_object().namespace[name]
                            ref.resolved_targets.update(map_resolved_objs(resolved_objs))

                if isinstance(ent, Class) and ref.ref_kind == RefKind.InheritKind:
                    summary = scene.summary_map[ent]
                    assert isinstance(summary, ClassSummary)
                    ref.resolved_targets.update(map_resolved_objs(summary.get_object().inherits))


