from typing import List

from dep.DepDB import DepDB
from ent.entity import ReferencedAttribute, Entity, ClassAttribute, Class
from ref.Ref import Ref


class EntityPass:
    def __init__(self, dep_db: DepDB):
        self.progress = 0
        self.dep_db = dep_db

    def resolve_referenced_attribute(self):
        def resolve(ent: Entity):
            print(f"progress: {self.progress}")
            self.progress += 1
            print(ent)
            if isinstance(ent, ReferencedAttribute):
                return ent
            new_refs: List[Ref] = []
            for ref in ent.refs():
                if isinstance(ref.target_ent, ReferencedAttribute):
                    same_name_attrs = get_same_attr(ref.target_ent)
                    if same_name_attrs:
                        new_refs.extend(
                            [Ref(ref.ref_kind, same_name, ref.lineno, ref.col_offset) for same_name in same_name_attrs])
                    else:
                        new_refs.extend([ref])
                else:
                    new_refs.append(ref)

            ent.set_refs(new_refs)
            return ent

        def get_same_attr(target: Entity) -> List[Entity]:
            ret = []
            for ent in self.dep_db.ents:
                if isinstance(ent, Class):
                    for ref in ent.refs():
                        if ref.target_ent.longname.name == target.longname.name:
                            ret.append(ref.target_ent)

            return ret

        print("now resolve all possible referenced attribute")
        print(f"entities: {len(self.dep_db.ents)}")
        self.dep_db.ents = [resolve(ent) for ent in self.dep_db.ents]
