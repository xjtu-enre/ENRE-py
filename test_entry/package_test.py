import json
import time
from pathlib import Path

from enre.analysis.analyze_manager import AnalyzeManager
from enre.vis.representation import DepRepr
from vis.summary_repr import from_summaries


def entry():
    root_path = Path("../testdata/mypy/mypy")
    start = time.time()

    manager = AnalyzeManager(root_path)
    manager.work_flow()
    out_path = Path("mypy-report-enre.json")
    with open(out_path, "w") as file:
        repr = DepRepr.from_package_db(manager.root_db).to_json()
        json.dump(repr, file, indent=4)
    summary_out_path = Path(f"mypy-report-enre-summary.txt")
    with open(summary_out_path, "w") as file:
        repr = from_summaries(manager.scene.summaries)
        file.write(repr)

    end = time.time()
    print(f"analysing time: {end - start}s")
    print()


if __name__ == '__main__':
    entry()
