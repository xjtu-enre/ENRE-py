import argparse
import json
import sys
import time
from pathlib import Path

from enre.analysis.analyze_manager import AnalyzeManager
from enre.vis.representation import DepRepr


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root path", type=str,
                        help="root package path")
    parser.add_argument("--profile", action="store_true", help="output consumed time in json format")
    parser.add_argument("--compatible", action="store_true", help="output compatible with enre java")
    config = parser.parse_args()
    root_path = Path(sys.argv[1])
    start = time.time()
    manager = enre_wrapper(root_path, config)
    end = time.time()
    if config.profile:
        time_in_json = json.dumps({
            "analyzed files": len(manager.root_db.tree),
            "analysing time": end - start})
        print(time_in_json)
        # print(f"analysing time: {end - start}s")


def enre_wrapper(root_path: Path, config: argparse.Namespace) -> AnalyzeManager:
    project_name = root_path.name
    manager = AnalyzeManager(root_path)
    manager.work_flow()
    out_path = Path(f"{project_name}-report-enre.json")
    with open(out_path, "w") as file:
        if config.compatible:
            repr_compatible = DepRepr.from_package_db(manager.root_db).to_json_1()
            json.dump(repr_compatible, file, indent=4)
        else:
            repr_readable = DepRepr.from_package_db(manager.root_db).to_json()
            json.dump(repr_readable, file, indent=4)
    return manager


if __name__ == '__main__':
    main()
