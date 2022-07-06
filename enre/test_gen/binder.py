# type: ignore
import json
import re
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import TypeAlias, Dict, List, Sequence, TypedDict, Tuple

EntityPattern = re.compile("E: (.*)-\\$(.*)=(.*)@(.*)")
NegEntityPattern = re.compile("NE: (.*)-\\$(.*)=(.*)@(.*)")
DependencyPattern = re.compile("D: (.*)-\\$(.*)->\\$(.*)@(.*)")
NegDependencyPattern = re.compile("ND: (.*)-\\$(.*)->\\$(.*)@(.*)")
CommentPattern = re.compile(" *# *(.*)")

EdgeTy = TypedDict("EdgeTy", {"src": int,
                              "src_name": str,
                              "dest": int,
                              "dest_name": str,
                              "kind": str,
                              "lineno": int,
                              "col_offset": int
                              })

NodeTy = TypedDict("NodeTy", {"id": int, "longname": str, "ent_type": str, "name": str,
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

    def to_json(self, is_neg: bool) -> DepTy:
        ret = dict()
        entities = []
        dependencies = []
        for n in self.node_list:
            entities.append(n)
        for e in self.edge_list:
            dependencies.append(e)
        if is_neg:
            ret["Negative Entities"] = entities
            ret["Negative Dependencies"] = dependencies
        else:
            ret["Entities"] = entities
            ret["Dependencies"] = dependencies
        return ret


class CommentHost(ABC):
    @abstractmethod
    def file_path(self) -> str:
        ...

    @abstractmethod
    def line_no(self) -> int:
        ...

    @abstractmethod
    def col_no(self, name: str) -> int:
        ...


@dataclass
class HostLine(CommentHost):
    def file_path(self) -> str:
        return str(self.file)

    def line_no(self) -> int:
        return self._lineno

    def col_no(self, name: str) -> int:
        return self.get_col(name)

    _lineno: int
    line_text: str
    file: Path

    def get_col(self, format: str) -> int:
        return self.line_text.find(format)


@dataclass
class HostFile(CommentHost):
    file: Path

    def file_path(self) -> str:
        return str(self.file)

    def line_no(self) -> int:
        return -1

    def col_no(self, name: str) -> int:
        return -1


Bind: TypeAlias = Dict[str, NodeTy]

_index = 0


def get_index() -> int:
    global _index
    _index += 1
    return _index

def has_no_numbers(inputString):

    return any(not char.isdigit() for char in inputString.replace("(","").replace(")", ""))

def interp_line(comment_line: str, dep: DepRepr, neg_dep: DepRepr, bind: Bind, host: CommentHost) -> None:
    if matches := re.match(EntityPattern, comment_line):
        ent_kind = matches[1]
        var_name = matches[2]
        ent_longname_match = matches[3]
        ent_longname = ent_longname_match.replace("$line", str(host.line_no()))
        ent_name = ent_longname.split(".")[-1]
        if not has_no_numbers(ent_name):
            ent_name = None
        location_format = matches[4]
        node: NodeTy = {"id": get_index(), "longname": ent_longname, "ent_type": ent_kind, "name": ent_name,
                        "start_line": host.line_no(), "start_col": host.col_no(location_format)}
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
                      "kind": dep_kind, "lineno": host.line_no(), "col_offset": host.col_no(location_format)})


@dataclass
class CommentBlock:
    related_line: CommentHost
    comment_lines: Sequence[str]

    def write_dependencies(self, dep: DepRepr, neg_dep: DepRepr, bind: Bind) -> None:
        for line in self.comment_lines:
            interp_line(line, dep, neg_dep, bind, self.related_line)


def read_comment_block(lines: Sequence[str], start_lineno: int) -> Tuple[List[str], int]:
    comment_lines: List[str] = []
    new_lineno = start_lineno
    for offset, line in enumerate(lines[start_lineno:]):
        if str.lstrip(line).startswith("#"):
            match_result = re.match(CommentPattern, line)
            assert match_result
            comment_line = match_result[1]
            comment_lines.append(comment_line)
        elif not str.isspace(line):
            new_lineno = start_lineno + offset
            break

    return comment_lines, new_lineno


def build_comment_blocks(file_path: Path) -> Sequence[CommentBlock]:
    file_content = file_path.read_text()
    lines = file_content.split("\n")
    comment_lines, lineno = read_comment_block(lines, 0)
    comment_blocks: List[CommentBlock] = []
    if comment_lines:
        comment_blocks.append(CommentBlock(HostFile(file_path), comment_lines))
    while lineno < len(lines):
        line = lines[lineno]
        host_lineno = lineno
        lineno += 1
        comment_lines, lineno = read_comment_block(lines, lineno)
        if comment_lines:
            host_line = HostLine(host_lineno + 1, line, file_path)
            comment_blocks.append(CommentBlock(host_line, comment_lines))
    return comment_blocks


def gen_test_case_for(file_path: Path) -> Tuple[DepRepr, DepRepr]:
    dep = DepRepr()
    neg_dep = DepRepr()
    bind: Bind = {}
    comment_blocks = build_comment_blocks(file_path)
    for block in comment_blocks:
        block.write_dependencies(dep, neg_dep, bind)
    return dep, neg_dep


def dump_meta_data(dep: DepRepr, neg_dep: DepRepr, ent_count: Dict[str, int], dep_count: Dict[str, int]) -> None:
    for node in dep.node_list:
        ent_count["all entity"] += 1
        ent_count[node["ent_type"]] += 1

    for edge in dep.edge_list:
        dep_count["all dependency"] += 1
        dep_count[edge["kind"]] += 1

def merge_two_dicts(x, y):
    z = x.copy()   # start with keys and values of x
    z.update(y)    # modifies z with keys and values of y
    return z

def gen_test_case_dir(dir: Path) -> None:
    test_case_dep_meta_data: Dict[str, int] = defaultdict(int)
    test_case_ent_meta_data: Dict[str, int] = defaultdict(int)
    for file_path in dir.iterdir():
        if file_path.name.endswith(".py"):
            test_case_name = file_path.name.removesuffix(".py")
            dep, neg_dep = gen_test_case_for(file_path)
            dump_meta_data(dep, neg_dep, test_case_ent_meta_data, test_case_dep_meta_data)
            with open(f"{test_case_name}.json", "w") as file:
                json.dump(merge_two_dicts(dep.to_json(False), neg_dep.to_json(True)), file, indent=4)

    with open("test_case_meta_data.json", "w") as file:
        meta_data = {"Entity": test_case_ent_meta_data, "Dependency": test_case_dep_meta_data}
        json.dump(meta_data, file, indent=4)


if __name__ == '__main__':
    gen_test_case_dir(Path("."))
