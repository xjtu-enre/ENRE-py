from typing import List

from ent.EntKind import RefKind
from ent.entity import Entity, Class, ClassAttribute, Module


def get_class_attr(ent: Class, attr: str) -> List[ClassAttribute]:
    ret: List[ClassAttribute] = []
    for ref in ent.refs():
        if ref.ref_kind == RefKind.DefineKind:
            if isinstance(ref.target_ent, ClassAttribute) and ref.target_ent.longname.name == attr:
                ret.append(ref.target_ent)
    return ret


def get_module_level_ent(m: Module, name: str) -> List[Entity]:
    ret = []
    for ref in m.refs():
        if ref.ref_kind == RefKind.DefineKind:
            if ref.target_ent.longname.name == name:
                ret.append(ref.target_ent)
    return ret
