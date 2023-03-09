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
from enre.vis.summary_repr import from_summaries


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root path", type=str, nargs='?',
                        help="root package path")
    parser.add_argument("--profile", action="store_true", help="output consumed time in json format")
    parser.add_argument("--cfg", action="store_true",
                        help="run control flow analysis and output module summaries")
    parser.add_argument("--compatible", action="store_true")
    parser.add_argument("--version", action="store_true")
    config = parser.parse_args()
    root_path = Path(sys.argv[1])

    start = time.time()
    manager = enre_wrapper(root_path, None, None)
    end = time.time()

    if config.profile:
        time_in_json = json.dumps({
            "analyzed files": len(manager.root_db.tree),
            "analysing time": end - start})
        print(time_in_json)
        # print(f"analysing time: {end - start}s")


def enre_wrapper(root_path: Path, compatible_format: bool, need_cfg: bool) -> AnalyzeManager:
    project_name = root_path.name
    manager = AnalyzeManager(root_path)
    manager.work_flow()
    out_path = Path(f"{project_name}-report-enre.json")
    if need_cfg:
        print("dependency analysis finished, now running control flow analysis")
        cfg_wrapper(root_path, manager.scene)
        print("control flow analysis finished")
        aggregate_cfg_info(manager.root_db, manager.scene)

    with open(out_path, "w") as file:
        if not compatible_format:
            json.dump(DepRepr.from_package_db(manager.root_db).to_json_1(), file, indent=4)
        else:
            repr = DepRepr.from_package_db(manager.root_db).to_json()
            json.dump(repr, file, indent=4)

    return manager


def cfg_wrapper(root_path: Path, scene: Scene) -> None:
    resolver = Resolver(scene)
    resolver.resolve_all()
    out_path = Path(f"{root_path.name}-report-cfg.txt")
    with open(out_path, "w") as file:
        summary_repr = from_summaries(scene.summaries)
        file.write(summary_repr)


if __name__ == '__main__':
    main()
