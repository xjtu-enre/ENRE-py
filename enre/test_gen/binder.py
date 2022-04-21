import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import TypeAlias, Dict, List, Sequence, TypedDict
import re
import enre.ent.entity
from dep.DepDB import DepDB

EntityPattern = re.compile("E: (.*)-\\$(.*)=(.*)@(.*)")
DependencyPattern = re.compile("D: (.*)-\\$(.*)->\\$(.*)@(.*)")
CommentPattern = re.compile(" *# *(.*)")

EdgeTy = TypedDict("EdgeTy", {"src": int,
                              "src_name": str,
                              "dest": int,
                              "dest_name": str,
                              "kind": str,
                              "lineno": int,
                              "col_offset": int
                              })

NodeTy = TypedDict("NodeTy", {"id": int, "longname": str, "ent_type": str,
                              "start_line": int, "start_col": int})

DepTy = TypedDict("DepTy", {"Entities": List[NodeTy], "Dependencies": List[EdgeTy]})


class DepRepr:
    def __init__(self) -> None:
        self.node_list: List[NodeTy] = []
        self.edge_list: List[EdgeTy] = []

    def add_node(self, n: NodeTy) -> None:
        self.node_list.append(n)

    def add_edge(self, e: EdgeTy) -> None:
        self.edge_list.append(e)

    def to_json(self) -> DepTy:
        ret: DepTy = {"Entities": [], "Dependencies": []}
        for n in self.node_list:
            ret["Entities"].append(n)
        for e in self.edge_list:
            ret["Dependencies"].append(e)
        return ret

@dataclass
class HostLine:
    lineno: int
    line_text: str

    def get_col(self, format: str) -> int:
        return self.line_text.find(format)


Bind: TypeAlias = Dict[str, NodeTy]


_index = 0


def get_index() -> int:
    global _index
    _index += 1
    return _index


def interp_line(comment_line: str, dep: DepRepr, bind: Bind, host: HostLine) -> None:
    if matches := re.match(EntityPattern, comment_line):
        ent_kind = matches[1]
        var_name = matches[2]
        ent_longname = matches[3]
        ent_longname = ent_longname.replace("$line", str(host.lineno))
        location_format = matches[4]
        node: NodeTy = {"id": get_index(), "longname": ent_longname, "ent_type": ent_kind,
                "start_line": host.lineno, "start_col": host.get_col(location_format)}
        dep.add_node(node)
        if var_name != "":
            bind[var_name] = node
    elif matches := re.match(DependencyPattern, comment_line):
        dep_kind = matches[1]
        src_var = matches[2]
        dest_var = matches[3]
        location_format = matches[4]
        src_node = bind[src_var]
        dest_node = bind[dest_var]

        dep.add_edge({"src": src_node["id"], "src_name": src_node["longname"],
                      "dest": dest_node["id"], "dest_name": dest_node["longname"],
                      "kind": dep_kind, "lineno": host.lineno, "col_offset": host.get_col(location_format)})

@dataclass
class CommentBlock:
    related_line: HostLine
    comment_lines: Sequence[str]

    def write_dependencies(self, dep: DepRepr, bind: Bind):
        for line in self.comment_lines:
            interp_line(line, dep, bind, self.related_line)


def build_comment_blocks(file_path: Path) -> Sequence[CommentBlock]:
    file_content = file_path.read_text()
    lines = file_content.split("\n")
    lineno = 0
    comment_blocks = []
    while lineno < len(lines):
        line = lines[lineno]
        host_lineno = lineno
        comment_lines = []
        for i in range(1, len(lines) - lineno):
            maybe_comment_line = lines[lineno + i]
            if "#" in maybe_comment_line:
                comment_line = re.match(CommentPattern, maybe_comment_line)[1]
                comment_lines.append(comment_line)
            else:
                lineno += i - 1
                break
        lineno += 1
        if comment_lines:
            host_line = HostLine(host_lineno + 1, line)
            comment_blocks.append(CommentBlock(host_line, comment_lines))
    return comment_blocks


def gen_test_case_for(file_path: Path) -> DepRepr:
    dep = DepRepr()
    bind = {}
    comment_blocks = build_comment_blocks(file_path)
    for block in comment_blocks:
        block.write_dependencies(dep, bind)
    return dep

def dump_meta_data(dep: DepRepr, ent_count, dep_count):
    for node in dep.node_list:
        ent_count["all entity"] += 1
        ent_count[node["ent_type"]] += 1

    for edge in dep.edge_list:
        dep_count["all dependency"] += 1
        dep_count[edge["kind"]] += 1


def gen_test_case_dir(dir: Path) -> None:
    test_case_dep_meta_data = defaultdict(int)
    test_case_ent_meta_data = defaultdict(int)
    for file_path in dir.iterdir():
        if file_path.name.endswith(".py"):
            test_case_name = file_path.name.removesuffix(".py")
            dep = gen_test_case_for(file_path)
            dump_meta_data(dep, test_case_ent_meta_data, test_case_dep_meta_data)
            with open(f"{test_case_name}.json", "w") as file:
                json.dump(dep.to_json(), file, indent=4)

    with open("test_case_meta_data.json", "w") as file:
        meta_data = {"Entity":test_case_ent_meta_data, "Dependency": test_case_dep_meta_data}
        json.dump(meta_data, file, indent=4)

if __name__ == '__main__':
    gen_test_case_dir(Path("."))

