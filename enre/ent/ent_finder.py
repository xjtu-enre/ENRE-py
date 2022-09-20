from typing import List, Union

from enre.analysis.value_info import PackageType
from enre.ent.EntKind import RefKind
from enre.ent.entity import Entity, Class, ClassAttribute, Module


def get_class_attr(ent: Class, attr: str) -> List[Entity]:
    return ent.names[attr]


def get_file_level_ent(m: Entity, name: str) -> List[Entity]:
    ret = []
    for ref in m.refs():
        if ref.ref_kind == RefKind.DefineKind or ref.ref_kind == RefKind.ContainKind:
            if ref.target_ent.longname.name == name or name == "*":
                ret.append(ref.target_ent)
    return ret
