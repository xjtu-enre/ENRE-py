import json
from pathlib import Path

from interp.manager_interp import InterpManager
from vis.representation import DepRepr


def entry():
    root_path = Path("../test/test.py")
    manager = InterpManager(root_path)
    manager.work_flow()
    package_db = manager.package_db
    out_path = Path("test-report.json")
    with open(out_path, "w") as file:
        representation = DepRepr.from_package_db(package_db).to_json()
        json.dump(representation, file, indent=4)
    print()


if __name__ == '__main__':
    entry()
