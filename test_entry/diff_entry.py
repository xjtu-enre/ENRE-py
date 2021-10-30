import json
import time
from pathlib import Path

from vis.graphdiffer import GraphDiffer
from vis.und_mapping import UndMapping

base_graph_path = Path("mypy-report.json")
und_graph_path = Path("mypy-report-und.json")
base_graph = json.loads(base_graph_path.read_text())
und_graph = json.loads(und_graph_path.read_text())
root_dir = Path("../testdata/mypy/mypy")
differ = GraphDiffer(base_graph_path, und_graph_path, UndMapping(root_dir,
                                                        base_graph["Entities"],
                                                        und_graph["Entities"]))

if __name__ == '__main__':
    start = time.time()
    diff_nodes = differ.diff_nodes()

    with open("diff-nodes.json", "w") as file:
        json.dump(diff_nodes, file, indent=4)
    end = time.time()
    print(f"analysing time: {end - start}s")
    exit(0)
    diff_edges = differ.diff_edges()

    with open("diff-edges.json", "w") as file:
        json.dump(diff_edges, file, indent=4)