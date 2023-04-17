from pathlib import Path
from typing import List, Union

from enre.analysis.analyze_typeshed import NameInfoVisitor
from enre.analysis.env import EntEnv
from enre.analysis.value_info import PackageType
from enre.ent.EntKind import RefKind
from enre.ent.entity import Entity, Class, ClassAttribute, Module


def get_class_attr(ent: Class, attr: str) -> List[Entity]:
    return ent.names[attr]


def get_file_level_ent(manager, m: Module, name: str) -> List[Entity]:
    ret = []
    for ref in m.refs():
        if ref.ref_kind == RefKind.DefineKind or ref.ref_kind == RefKind.ContainKind or ref.ref_kind == RefKind.ImportKind:
            if ref.target_ent.longname.name == name:
                ret.append(ref.target_ent)
    if not ret:
        ret = get_stub_or_unknown_file_level_ent(manager, m, name)

    return ret


def get_stub_or_unknown_file_level_ent(manager, m: Entity, name: str) -> List[Entity]:
    module_path = Path(m.longname.name + '.py')
    module_db = manager.root_db.tree[module_path] if module_path in manager.root_db.tree else None
    ret = []
    if module_db:
        env = module_db._env
        get_stub = module_db._get_stub
        stub_file = module_db._stub_file if module_db._stub_file else module_path
        bv = NameInfoVisitor(name, get_stub, manager, module_db,
                             env, stub_file)
        if get_stub:
            attr_info = get_stub.get(name)  # typeshed
        else:
            attr_info = None  # unknown
        ent = bv.generic_analyze(name, attr_info)
        ret.append(ent)
    return ret
