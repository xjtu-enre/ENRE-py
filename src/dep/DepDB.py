import typing as ty
from ent.EntKind import RefKind
from ent.entity import Entity, Class, Module, EntLongname, ModuleAlias
from ref.Ref import Ref


class DepDB:
    def __init__(self):
        self.ents: ty.List[Entity] = []

    def add_ent(self, ent: Entity):
        self.ents.append(ent)


    def _get_define_entities(self, ent_longname: EntLongname, ent_name: str) -> ty.List[Entity]:
        ret: ty.List[Entity] = []
        for ent_1 in self.ents:
            if ent_1.longname == ent_longname:
                refs = ent_1.refs()
                for ref in refs:
                    if ref.ref_kind == RefKind.DefineKind and ref.target_ent.longname.name == ent_name:
                        ret.append(ref.target_ent)

        return ret

    def get_class_attributes(self, ent: Class, attribute: str) -> ty.List[Entity]:
        defined_attributes = ent.get_attribute(attribute)
        return defined_attributes
        # return self._get_define_entities(ent.longname, attribute)

    def get_module_attributes(self, ent: ty.Union[Module, ModuleAlias], attribute: str) -> ty.List[Entity]:
        return self._get_define_entities(ent.module_longname, attribute)

    def remove(self, target: Entity):
        try:
            self.ents.remove(target)
        except ValueError:
            pass
