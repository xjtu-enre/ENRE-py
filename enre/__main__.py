import json
import sys
import time
from pathlib import Path

from enre.analysis.analyze_manager import AnalyzeManager
from enre.vis.representation import DepRepr


def main() -> None:
    root_path = Path(sys.argv[1])
    start = time.time()
    enre_wrapper(root_path)
    end = time.time()
    print(f"analysing time: {end - start}s")


def enre_wrapper(root_path: Path) -> None:
    project_name = root_path.name
    manager = AnalyzeManager(root_path)
    manager.work_flow()
    out_path = Path(f"{project_name}-report-enre.json")
    with open(out_path, "w") as file:
        repr = DepRepr.from_package_db(manager.root_db).to_json()
        json.dump(repr, file, indent=4)


if __name__ == '__main__':
    main()
