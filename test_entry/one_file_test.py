import json
import time
from pathlib import Path

from cfg.Resolver import Resolver
from enre.analysis.analyze_manager import AnalyzeManager
from vis.representation import DepRepr
from vis.summary_repr import from_summaries


def entry():
    root_path = Path("../test/test.py")
    manager = AnalyzeManager(root_path)
    manager.work_flow()
    package_db = manager.root_db
    out_path = Path("test-report.json")
    resolver = Resolver(manager.scene)
    resolver.resolve_all()
    with open(out_path, "w") as file:
        representation = DepRepr.from_package_db(package_db).to_json_1()
        json.dump(representation, file, indent=4)
    end = time.time()
    summary_out_path = Path(f"test-report-enre-summary-{end}.txt")
    with open(summary_out_path, "w") as file:
        repr = from_summaries(manager.scene.summaries)
        file.write(repr)

    print()


if __name__ == '__main__':
    entry()
