from pathlib import Path
from typing import List, Union

from enre.analysis.analyze_manager import ModuleDB
from enre.analysis.env import EntEnv
from enre.pyi.visitor import NameInfoVisitor
from enre.ent.EntKind import RefKind
from enre.ent.entity import Entity, Class, Module, Location, ReferencedAttribute, _Nil_Span
from enre.ref.Ref import Ref


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
    assert isinstance(m, Module)
    module_path = Path(m.longname.name + '.py') if m.typeshed_module else m.module_path
    module_db = manager.root_db.tree[module_path] if module_path in manager.root_db.tree else None
    ret = []
    assert isinstance(module_db, ModuleDB)
    # create Entity in typeshed module Env, do not add any no use Entities
    env: EntEnv = module_db.env
    stub_names = module_db.typeshed_stub_names
    ent = NameInfoVisitor.analyze_wrapper(manager, module_path, env, stub_names, name)
    ret.append(ent) if ent else ...
    if not ret:  # typing.TYPE_CHECKING
        location = m.location.append(name, _Nil_Span, None)
        referenced_attr = ReferencedAttribute(location.to_longname(), location)
        # print(referenced_attr.longname.longname)
        module_db.add_ent(referenced_attr)
        m.add_ref(Ref(RefKind.DefineKind, referenced_attr, -1, -1, False, None))
        bindings = [(name, [(referenced_attr, referenced_attr.direct_type())])]
        env.get_scope().add_continuous(bindings)
        ret.append(referenced_attr)
    return ret
