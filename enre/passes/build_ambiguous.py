from collections import defaultdict
from typing import Dict, List, Optional

from enre.analysis.analyze_manager import RootDB
from enre.analysis.value_info import ValueInfo
from enre.ent.EntKind import RefKind
from enre.ent.entity import Entity, Class, AmbiguousAttribute, ReferencedAttribute, NamespaceType, UnresolvedAttribute
from enre.passes.entity_pass import DepDBPass
from enre.ref.Ref import Ref


class BuildAmbiguous(DepDBPass):
    """Build ambiguous attribute dictionary,
    An attribute would be seen as ambiguous when there's
    another attribute with the same name.
    """

    def __init__(self, package_db: RootDB):
        self._package_db = package_db

    @property
    def package_db(self) -> RootDB:
        return self._package_db

    def execute_pass(self) -> None:
        self._build_ambiguous_attributes()

    def build_attr_map(self) -> Dict[str, List[Entity]]:
        """
        :return: the attribute map which map attribute name to the
            attribute entities
        """
        attr_map: Dict[str, List[Entity]] = defaultdict(list)
        for _, module_db in self.package_db.tree.items():
            for ent in module_db.dep_db.ents:
                if isinstance(ent, Class):
                    for attr_name, attr_ent in ent.names.items():
                        attr_map[attr_name].extend(attr_ent)
        return attr_map

    def build_ambiguous_dict(self, attr_map: Dict[str, List[Entity]]) -> "NamespaceType":
        """
        if the name corresponds to more than one class attribute, the
        attribute would be seen has ambiguous
        :param attr_map: the attribute map maps the attribute name to
            attribute entities
        :return: the attribute map maps the attribute name to ambiguous
            attribute entities
        """
        ambiguous_dict: Dict[str, List[Entity]] = defaultdict(list)
        for name, ents in attr_map.items():
            if len(ents) > 1:
                ambiguous_dict[name].extend(ents)
        return ambiguous_dict

    def resolve_referenced_attr(self, attr_map: Dict[str, List[Entity]],
                                ambiguous_ent_dict: Dict[str, Optional[AmbiguousAttribute]]) -> None:
        for _, module_db in self.package_db.tree.items():
            for ent in module_db.dep_db.ents:
                for ref in ent.refs():
                    self.rebuild_ref(ent, ref, attr_map, ambiguous_ent_dict)

    def _build_ambiguous_attributes(self) -> None:
        attr_map = self.build_attr_map()
        ambiguous_dict = self.build_ambiguous_dict(attr_map)
        ambiguous_ent_dict = self.build_ambiguous_ents(ambiguous_dict)
        self.resolve_referenced_attr(attr_map, ambiguous_ent_dict)

    def build_ambiguous_ents(self, ambiguous_dict: Dict[str, List[Entity]]) -> Dict[str, Optional[AmbiguousAttribute]]:
        ambiguous_ents_dict: Dict[str, Optional[AmbiguousAttribute]] = defaultdict(lambda: None)
        for name, ents in ambiguous_dict.items():
            ambiguous_ent = AmbiguousAttribute(name)
            ambiguous_ents_dict[name] = ambiguous_ent
            self._package_db.global_db.add_ent(ambiguous_ent)
            for tar_ent in ents:
                tar_ent.add_ref(Ref(RefKind.HasambiguousKind, ambiguous_ent, -1, -1, False, None))
        return ambiguous_ents_dict


    def rebuild_ref(self, ent: Entity, ref: Ref,
                    definite_attr_dict: Dict[str, List[Entity]],
                    ambiguous_ent_dict: Dict[str, Optional[AmbiguousAttribute]]) -> None:
        """
        If the target of a reference is an referenced attribute, rebuild the relation
        to the resolved attribute entities.

        If the name of the target referenced attribute in the ambiguous dictionary,
        build the relation to the ambiguous entity(AmbiguousAttribute).

        If the name not in the ambiguous dictionary, build the relation to the
        relation to the attribute entity directly.

        If can't find the name at any attribute dictionary, create an unresolved attribute
        in place, and create the relation the relation to that.

        :param ent: the src entity which need to rebuild relation
        :param ref: the reference to the target attribute
        :param definite_attr_dict: the dictionary maps name to list of attribute entities,
            if there's  no attribute named that, it maps to empty list.
        :param ambiguous_ent_dict: the dictionary maps name to attribute ambiguous
            entities
        :return:
        """
        target_ent = ref.target_ent
        if not isinstance(target_ent, ReferencedAttribute):
            return
        attr_name = target_ent.longname.name
        ambiguous_ent = ambiguous_ent_dict[attr_name]
        if ambiguous_ent is not None:
            ent.add_ref(Ref(ref.ref_kind, ambiguous_ent, ref.lineno, ref.col_offset, ref.in_type_ctx, ref.expr))
            return
        elif definite_attr := definite_attr_dict[attr_name]:
            for attr_ent in definite_attr:
                ent.add_ref(Ref(ref.ref_kind, attr_ent, ref.lineno, ref.col_offset, ref.in_type_ctx, ref.expr))
        else:
            # referenced attribute is an unresolved attribute
            unresolved = UnresolvedAttribute(target_ent.longname, target_ent.location, ValueInfo.get_any())
            self.package_db.add_ent_global(unresolved)
            ent.add_ref(Ref(ref.ref_kind, unresolved, ref.lineno, ref.col_offset, ref.in_type_ctx, ref.expr))
