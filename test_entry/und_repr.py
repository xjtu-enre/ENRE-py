import json
import os
from pathlib import Path

from interp.manager_interp import PackageDB
from vis.representation import DepRepr

os.add_dll_directory("D:\Tools\SciTools\\bin\pc-win64")
import understand



def und_representation(db) -> DepRepr:
    return DepRepr.from_und_db(db)


if __name__ == '__main__':
    udb_path = Path("../testdata/mypy.und")
    udb = understand.open(str(udb_path))
    dep_repr = und_representation(udb).to_json()
    with open("mypy-report-und.json", "w") as file:
        json.dump(dep_repr, file, indent=4)

