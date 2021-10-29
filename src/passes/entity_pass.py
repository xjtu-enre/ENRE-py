from collections import defaultdict
from typing import List, Dict

from ent.EntKind import RefKind
from ent.entity import ReferencedAttribute, Entity, UnresolvedAttribute
from interp.enttype import EntType
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
                        same_name_attr_refs = [Ref(ref.ref_kind, e, ref.lineno, ref.col_offset) for e in
                                               self.attribute_dict[ref.target_ent.longname.name]]
                        # todo: make referenced attribute reference as unresolved
                        # if same_name_attr_refs == []:
                        #     unresolved = UnresolvedAttribute(ref.target_ent.longname, ref.target_ent.location,
                        #                                      EntType.get_bot())
                        #
                        #     same_name_attr_refs.append()
                        new_refs.extend(same_name_attr_refs)
                    else:
                        new_refs.append(ref)
                ent.set_refs(new_refs)

    def build_attribute_dict(self):
        for _, module_db in self.package_db.tree.items():
            for ent in module_db.dep_db.ents:
                for ref in ent.refs():
                    if ref.ref_kind == RefKind.DefineKind:
                        self.attribute_dict[ref.target_ent.longname.lvalueexpr].append(ref.target_ent)
