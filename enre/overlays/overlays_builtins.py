from enre.analysis.value_info import InstanceType, UnionType, ConstructorType, ValueInfo, ListType, SetType, TupleType, \
    DictType
from enre.util.common import builtins_path


class OverlaysBuiltins:
    def __init__(self, manager):
        self.manager = manager
        self.builtins_env = None

    def builtins(self, value: InstanceType | ConstructorType):
        if not self.builtins_env:
            self.builtins_env = self.manager.root_db.tree[builtins_path].env
        class_name = value.class_ent.longname.name
        method = '_handle_builtins_' + class_name
        visitor = getattr(self, method, self._miss_type)
        return visitor(value)

    def _miss_type(self, value):
        class_name = value.class_ent.longname.name
        method = 'miss _handle_builtins_' + class_name
        # print(method)
        return value

    def _handle_builtins_dict(self, value):
        if isinstance(value, InstanceType):
            builtins_dict_ent = self.builtins_env["dict"].found_entities[0][0]
            dic = DictType(builtins_dict_ent)
            dic.paras = value.paras
            return dic
        else:
            return value

    def _handle_builtins_range(self, value):
        if isinstance(value, InstanceType):
            builtins_int = self.builtins_env["int"].found_entities[0][1]
            return builtins_int.to_class_type()
        else:
            return value
