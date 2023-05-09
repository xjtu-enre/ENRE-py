import typing as ty
from enre.ent.EntKind import RefKind
from enre.ent.entity import Entity, Class, Module, EntLongname, ModuleAlias, UnknownVar
from enre.ref.Ref import Ref


class DepDB:
    def __init__(self) -> None:
        self.ents: ty.List[Entity] = []
        self.referenced_attrs = dict()

    def add_ent(self, ent: Entity) -> None:
        self.ents.append(ent)

    def _get_define_entities(self, ent_longname: EntLongname, ent_name: str) -> ty.List[Entity]:
        res: ty.List[Entity] = []
        for ent_1 in self.ents:
            if ent_1.longname == ent_longname:
                refs = ent_1.refs()
                for ref in refs:
                    if ref.ref_kind == RefKind.DefineKind and ref.target_ent.longname.name == ent_name:
                        res.append(ref.target_ent)

        return res

    def get_Define_ent(self):
        module_ent = None
        res = dict()
        for ent in self.ents:
            if isinstance(ent, Module):
                module_ent = ent
                break
        if not module_ent:
            return res
        else:
            for ref in module_ent.refs():
                if ref.ref_kind == RefKind.DefineKind:
                    name = ref.target_ent.longname.name
                    res[name] = ref.target_ent
        return res

    def get_UnknownVar_ent(self):
        res = dict()
        for ent in self.ents:
            if isinstance(ent, UnknownVar):
                name = ent.longname.name
                res[name] = ent
        return res

    def get_class_attributes(self, ent: Class, attribute: str, manager) -> ty.List[Entity]:
        defined_attributes = ent.get_attribute(attribute, manager)
        return defined_attributes

    def get_module_attributes(self, ent: ty.Union[Module, ModuleAlias], attribute: str) -> ty.List[Entity]:
        return self._get_define_entities(ent.module_longname, attribute)

    def remove(self, target: Entity) -> None:
        try:
            self.ents.remove(target)
        except ValueError:
            pass
