from collections import defaultdict
from typing import Sequence, Any, Dict

from enre.cfg.Resolver import Resolver
from enre.cfg.HeapObject import FunctionObject, InstanceMethodReference
from enre.cfg.module_tree import ModuleSummary, Scene
from enre.ent.entity import Function


def from_summaries(summaries: Sequence[ModuleSummary]) -> str:
    ret = ""
    for summary in summaries:
        ret += f"{str(summary)}\n"
        for name, objs in summary.get_namespace().items():
            ret += f"\t{name}: "
            ret += ",".join(str(obj.representation()) for obj in objs)
            ret += "\n"


    return ret

def call_graph_representation(resolver: Resolver) -> Dict[str, Any]:
    call_graph = defaultdict(list)
    for ent, summary in resolver.scene.summary_map.items():
        for invoke in summary.get_invokes():
            invoke_targets = resolver.get_store_able_value(invoke.target, summary.get_namespace())
            for target in invoke_targets:
                target_func: Function
                if isinstance(target, FunctionObject):
                    target_func = target.func_ent
                elif isinstance(target, InstanceMethodReference):
                    target_func = target.func_obj.func_ent
                else:
                    continue
                call_graph[ent.longname.longname].append(target_func.longname.longname)
    return call_graph
