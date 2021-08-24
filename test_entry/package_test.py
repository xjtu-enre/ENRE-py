from pathlib import Path

from interp.manager_interp import InterpManager


def entry():
    root_path = Path("../src")

    manager = InterpManager(root_path)
    manager.work_flow()
    dep_db = manager.dep_db
    out_path = Path("report.txt")
    with open(out_path, "w") as file:
        for ent in dep_db.ents:
            file.write(f"{ent.longname.longname} [{ent.kind().value}]" + "\n")
            for ref in ent.refs():
                file.write(f"    {ref.ref_kind.value} {ref.lineno, ref.col_offset} -> {ref.target_ent.longname.longname}\n")

    print()


if __name__ == '__main__':
    entry()
