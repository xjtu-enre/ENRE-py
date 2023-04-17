from collections import defaultdict
from typing import Dict, List

from enre.analysis.analyze_manager import RootDB
from enre.analysis.value_info import ValueInfo
from enre.ent.EntKind import RefKind
from enre.ent.entity import Entity, Class, ReferencedAttribute, NamespaceType, UnresolvedAttribute
from enre.passes.entity_pass import DepDBPass
from enre.ref.Ref import Ref


class BuildPossibleCandidates(DepDBPass):
    def __init__(self, package_db: RootDB):
        self._package_db = package_db
        self.resolved_referenced_attrs = set()
        self.resolved_unresolved_attrs = set()

    @property
    def package_db(self) -> RootDB:
        return self._package_db

    def execute_pass(self) -> None:
        self._build_possible_candidates()

    def build_attr_map(self) -> Dict[str, List[Entity]]:

        attr_map: Dict[str, List[Entity]] = defaultdict(list)
        for _, module_db in self.package_db.tree.items():
            for ent in module_db.dep_db.ents:
                if isinstance(ent, Class):
                    for attr_name, attr_ent in ent.names.items():
                        attr_map[attr_name].extend(attr_ent)
        return attr_map

    def build_possible_candidates_dict(self, attr_map: Dict[str, List[Entity]]) -> "NamespaceType":

        possible_candidates_dict: Dict[str, List[Entity]] = defaultdict(list)
        for name, ents in attr_map.items():
            if len(ents) >= 1:
                possible_candidates_dict[name].extend(ents)
        return possible_candidates_dict

    def resolve_referenced_attr(self, possible_candidates_dict) -> None:
        for _, module_db in self.package_db.tree.items():
            for ent in module_db.dep_db.ents:
                for ref in ent.refs():
                    self.rebuild_ref(ent, ref, possible_candidates_dict)

    def _build_possible_candidates(self) -> None:
        attr_map = self.build_attr_map()
        possible_candidates_dict = self.build_possible_candidates_dict(attr_map)
        self.resolve_referenced_attr(possible_candidates_dict)

    def rebuild_ref(self, ent: Entity, ref: Ref, possible_candidates_dict) -> None:

        target_ent = ref.target_ent
        if not isinstance(target_ent, ReferencedAttribute) or target_ent in self.resolved_referenced_attrs:
            return
        attr_name = target_ent.longname.name
        possible_candidates = possible_candidates_dict[attr_name]
        if possible_candidates:
            if len(possible_candidates) == 1:
                ent.add_ref(Ref(ref.ref_kind, possible_candidates[0], ref.lineno, ref.col_offset, ref.in_type_ctx, ref.expr))
                ent.refs().remove(ref)

                referenced_attrs = self.package_db.global_db.referenced_attrs
                if attr_name in referenced_attrs:
                    del referenced_attrs[attr_name]
                self.package_db.global_db.remove(target_ent)
            else:
                for attr_ent in possible_candidates:
                    target_ent.add_ref(Ref(RefKind.PossibleKind, attr_ent, -1, -1, ref.in_type_ctx, ref.expr))
                self.resolved_referenced_attrs.add(target_ent)
        else:
            if target_ent.longname.longname in self.resolved_unresolved_attrs:
                return
            unresolved = UnresolvedAttribute(target_ent.longname, target_ent.location, ValueInfo.get_any())
            self.package_db.add_ent_global(unresolved)
            self.resolved_unresolved_attrs.add(unresolved.longname.longname)
            ent.add_ref(Ref(ref.ref_kind, unresolved, ref.lineno, ref.col_offset, ref.in_type_ctx, ref.expr))

            referenced_attrs = self.package_db.global_db.referenced_attrs
            if attr_name in referenced_attrs:
                del referenced_attrs[attr_name]
            self.package_db.global_db.remove(target_ent)
