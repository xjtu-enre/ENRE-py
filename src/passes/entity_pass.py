from collections import defaultdict
from typing import List, Dict

from dep.DepDB import DepDB
from ent.EntKind import RefKind
from ent.entity import ReferencedAttribute, Entity, ClassAttribute, Class
from interp.manager_interp import PackageDB
from ref.Ref import Ref


class EntityPass:
    def __init__(self, package_db: PackageDB):
        self.progress = 0
        self.package_db: PackageDB = package_db
        self.attribute_dict: Dict[str, List[Entity]] = defaultdict(list)

    def resolve_referenced_attribute(self):
        self.build_attribute_dict()
        for _, module_db in self.package_db.tree.items():
            for ent in module_db.dep_db.ents:
                new_refs: List[Ref] = []
                for ref in ent.refs():
                    if isinstance(ref.target_ent, ReferencedAttribute):
                        new_refs.extend([Ref(ref.ref_kind, e, ref.lineno, ref.col_offset) for e in
                                         self.attribute_dict[ref.target_ent.longname.name]])
                ent.set_refs(new_refs)

    def build_attribute_dict(self):
        for _, module_db in self.package_db.tree.items():
            for ent in module_db.dep_db.ents:
                for ref in ent.refs():
                    if ref.ref_kind == RefKind.DefineKind:
                        self.attribute_dict[ref.target_ent.longname.name].append(ref.target_ent)
