from collections import defaultdict
from typing import List, Dict

from enre.ent.EntKind import RefKind
from enre.ent.entity import ReferencedAttribute, Entity, UnresolvedAttribute
from enre.interp.enttype import EntType
from enre.interp.manager_interp import PackageDB
from enre.ref.Ref import Ref
import abc


class DepDBPass:
    @property
    @abc.abstractmethod
    def package_db(self) -> PackageDB:
        ...

    @abc.abstractmethod
    def execute_pass(self):
        ...


class EntityPass(DepDBPass):

    def __init__(self, package_db: PackageDB):
        self.progress = 0
        self._package_db: PackageDB = package_db
        self.attribute_dict: Dict[str, List[Entity]] = defaultdict(list)

    @property
    def package_db(self) -> PackageDB:
        return self._package_db

    def execute_pass(self):
        self._resolve_referenced_attribute()

    def _resolve_referenced_attribute(self):
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
                        self.attribute_dict[ref.target_ent.longname.name].append(ref.target_ent)
