import ast
from pathlib import Path

from ent.entity import Module
from interp.checker import AInterp
from interp.env import EntEnv, ScopeEnv


def entry():
    import sys
    module_path = Path(sys.argv[1])
    root_path = Path("../test")
    module_ent = Module(module_path.relative_to(root_path.parent))

    checker = AInterp(module_ent, _)
    with open(module_path, "r") as file:
        checker.interp_top_stmts(ast.parse(file.read()).body,
                                 EntEnv(ScopeEnv(module_ent, module_ent.location)))

        dep_db = checker.dep_db

    out_path = Path("report.txt")
    with open(out_path, "w") as file:
        for ent in dep_db.ents:
            file.write(f"{ent.longname.longname} [{ent.kind().value}]" + "\n")
            for ref in ent.refs():
                file.write(f"    {ref.ref_kind.value} -> {ref.target_ent.longname.longname}\n")

    print()


if __name__ == '__main__':
    entry()
