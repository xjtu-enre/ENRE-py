import argparse
import json
import sys
import time
from pathlib import Path

from enre.analysis.analyze_manager import AnalyzeManager
from enre.cfg.Resolver import Resolver
from enre.cfg.module_tree import Scene
from enre.passes.aggregate_control_flow_info import aggregate_cfg_info
from enre.vis.representation import DepRepr
from enre.vis.summary_repr import from_summaries, call_graph_representation


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root path", type=str, nargs='?',
                        help="root package path")
    parser.add_argument("--profile", action="store_true", help="output consumed time in json format")
    parser.add_argument("--cfg", action="store_true",
                        help="run control flow analysis and output module summaries")
    parser.add_argument("--compatible", action="store_true", help="output compatible format")
    parser.add_argument("--builtins", action="store", help="builtins module path")
    parser.add_argument("--cg", action="store_true", help="dump call graph in json")
    config = parser.parse_args()
    root_path = Path(sys.argv[1])
    start = time.time()
    manager = enre_wrapper(root_path, config.compatible, config.cfg, config.cg, config.builtins)
    end = time.time()

    if config.profile:
        time_in_json = json.dumps({
            "analyzed files": len(manager.root_db.tree),
            "analysing time": end - start})
        print(time_in_json)
        # print(f"analysing time: {end - start}s")


def dump_call_graph(project_name: str, resolver: Resolver) -> None:
    call_graph = call_graph_representation(resolver)
    out_path = f"{project_name}-call-graph-enre.json"
    with open(out_path, "w") as file:
        json.dump(call_graph, file, indent=4)


def enre_wrapper(root_path: Path, compatible_format: bool, need_cfg: bool, need_call_graph: bool,
                 builtin_module: str) -> AnalyzeManager:
    project_name = root_path.name
    builtins_path = Path(builtin_module) if builtin_module else None
    manager = AnalyzeManager(root_path, builtins_path)
    manager.work_flow()
    out_path = Path(f"{project_name}-report-enre.json")
    if need_cfg:
        print("dependency analysis finished, now running control flow analysis")
        resolver = cfg_wrapper(root_path, manager.scene)
        print("control flow analysis finished")
        aggregate_cfg_info(manager.root_db, resolver)
        if need_call_graph:
            dump_call_graph(project_name, resolver)

    with open(out_path, "w") as file:
        if not compatible_format:
            json.dump(DepRepr.from_package_db(manager.root_db).to_json_1(), file, indent=4)
        else:
            repr = DepRepr.from_package_db(manager.root_db).to_json()
            json.dump(repr, file, indent=4)


    return manager


def cfg_wrapper(root_path: Path, scene: Scene) -> Resolver:
    resolver = Resolver(scene)
    resolver.resolve_all()
    out_path = Path(f"{root_path.name}-report-cfg.txt")
    with open(out_path, "w") as file:
        summary_repr = from_summaries(scene.summaries)
        file.write(summary_repr)
    return resolver

if __name__ == '__main__':
    main()
