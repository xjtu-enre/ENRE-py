import json
import sys
import time
from pathlib import Path

from interp.manager_interp import InterpManager
from vis.representation import DepRepr


def main():
    root_path = Path(sys.argv[1])
    start = time.time()
    enre_wrapper(root_path)
    end = time.time()
    print(f"analysing time: {end - start}s")


def enre_wrapper(root_path):
    project_name = root_path.name
    manager = InterpManager(root_path)
    manager.work_flow()
    out_path = Path(f"{project_name}-report-enre.json")
    with open(out_path, "w") as file:
        repr = DepRepr.from_package_db(manager.package_db).to_json()
        json.dump(repr, file, indent=4)


if __name__ == '__main__':
    main()
