import argparse
import json
import sys
import time
from pathlib import Path

from enre.analysis.analyze_manager import AnalyzeManager
from enre.vis.representation import DepRepr
from enre.vis.summary_repr import from_summaries


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root path", type=str,
                        help="root package path")
    parser.add_argument("--profile", action="store_true", help="output consumed time in json format")
    args = parser.parse_args()
    root_path = Path(sys.argv[1])
    start = time.time()
    manager = enre_wrapper(root_path)
    end = time.time()
    if args.profile:
        time_in_json = json.dumps({
            "analyzed files": len(manager.root_db.tree),
            "analysing time": end - start})
        print(time_in_json)
        # print(f"analysing time: {end - start}s")


def enre_wrapper(root_path: Path) -> AnalyzeManager:
    project_name = root_path.name
    manager = AnalyzeManager(root_path)
    manager.work_flow()
    out_path = Path(f"{project_name}-report-enre.json")
    with open(out_path, "w") as file:
        repr = DepRepr.from_package_db(manager.root_db).to_json()
        json.dump(repr, file, indent=4)

    summary_out_path = Path(f"{project_name}-report-enre-summary.txt")
    with open(summary_out_path, "w") as file:
        summary_repr = from_summaries(manager.scene.summaries)
        file.write(summary_repr)

    return manager


if __name__ == '__main__':
    main()
