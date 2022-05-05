import json
from pathlib import Path

from enre.analysis.analyze_manager import AnalyzeManager
from vis.representation import DepRepr


def entry():
    root_path = Path("../test/test.py")
    manager = AnalyzeManager(root_path)
    manager.work_flow()
    package_db = manager.root_db
    out_path = Path("test-report.json")
    with open(out_path, "w") as file:
        representation = DepRepr.from_package_db(package_db).to_json()
        json.dump(representation, file, indent=4)
    print()


if __name__ == '__main__':
    entry()
