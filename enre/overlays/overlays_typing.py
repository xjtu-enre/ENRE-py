from enre.analysis.value_info import InstanceType, UnionType, ConstructorType, ValueInfo, ListType, SetType, TupleType, \
    DictType
from enre.util.common import builtins_path


class OverlaysTyping:
    def __init__(self, manager):
        self.manager = manager
        self.builtins_env = None

    def typing(self, value: InstanceType | ConstructorType):
        if not self.builtins_env:
            self.builtins_env = self.manager.root_db.tree[builtins_path].env
        class_name = value.class_ent.longname.name
        method = '_handle_typing_' + class_name
        visitor = getattr(self, method, self._miss_type)
        return visitor(value)

    def _miss_type(self, value):
        class_name = value.class_ent.longname.name
        method = 'miss _handle_typing_' + class_name
        # print(method)
        return value

    def _handle_typing_TypeVar(self, value):
        """first param is TypeVar name, so we don't need it"""
        u = UnionType()
        u.add(value.paras[1:])
        # print(f"Resolved {value} --> {u}")
        return u

    def _handle_typing_Union(self, value):
        u = UnionType()
        u.add(value.paras)
        # print(f"Resolved {value} --> {u}")
        return u

    def _handle_typing_Optional(self, value):
        """Optional[X] is equivalent to Union[X, None].
        TypeError: typing.Optional requires a single type. Got (<class 'str'>, <class 'int'>).
        !!! Only can provide single type.
        """
        u = UnionType()
        u.join(ValueInfo.get_none())
        u.add(value.paras)

        # print(f"Resolved {value} --> {u}")
        return u

    def _handle_typing_List(self, value):
        builtins_list = self.builtins_env["list"].found_entities[0][1]
        li = ListType(value.paras, builtins_list)

        # print(f"Resolved {value} --> {li}")

        return li

    def _handle_typing_Set(self, value):
        builtins_set = self.builtins_env["set"].found_entities[0][1]
        se = SetType(set(value.paras), builtins_set)

        # print(f"Resolved {value} --> {se}")

        return se

    def _handle_typing_Tuple(self, value):
        builtins_tuple = self.builtins_env["tuple"].found_entities[0][1]
        tu = TupleType(builtins_tuple)
        tu.add(value.paras)

        # print(f"Resolved {value} --> {tu}")

        return tu

    def _handle_typing_Dict(self, value):
        builtins_dict = self.builtins_env["dict"].found_entities[0][1]
        dic = DictType(builtins_dict)
        # length of value.paras must be 2
        if len(value.paras) != 2:
            # print("_handle_typing_Dict wrong, length of typing.Dict[paras] must be 2")
            ...
        else:
            dic.key = value.paras[0]
            dic.value = value.paras[1]
            # print(f"Resolved {value} --> {dic}")

        return dic

    def _handle_typing_TypedDict(self, value):
        builtins_dict = self.builtins_env["dict"].found_entities[0][1]
        """td1 = TypedDict('td1', {'x': int, 'y': int, 'label': str})
        we only resolve this cases right now
        """
        dic = DictType(builtins_dict)
        # length of value.paras must be 2
        if len(value.paras) == 0:  # inherit TypedDict
            # print(f"Resolved {value} --> {dic}")
            return dic
        if len(value.paras) < 2:
            # print("_handle_typing_TypedDict wrong, length of typing.TypedDict[paras] must larger or equal 2")
            ...
        else:
            # value.paras[0] should be TypedDict instance name
            # value.paras[1] should be a real dict
            para_dic = value.paras[1]
            if isinstance(para_dic, DictType):
                dic.key = para_dic.key
                dic.value = para_dic.value
                # print(f"Resolved {value} --> {dic}")

        return dic

    def _handle_typing_Sequence(self, value):
        # alias to list or tuple
        return self._handle_typing_List(value)

    def _handle_typing_Callable(self, value):
        # ignore
        return value

    def _handle_typing_TypeAlias(self, value):
        """
        from typing import TypeAlias
        Factors: TypeAlias = list[int]
        type(Factors) = <class 'types.GenericAlias'>

        TypeAlias meaningless
        """
        return ValueInfo.get_any()

    def _handle_typing_Iterable(self, value):
        return value

    def _handle_typing_Any(self, value):
        return ValueInfo.get_any()

    def _handle_typing_Iterator(self, value):
        return value

    def _handle_typing_IO(self, value):
        return value

    def _handle_typing_BinaryIO(self, value):
        return value
