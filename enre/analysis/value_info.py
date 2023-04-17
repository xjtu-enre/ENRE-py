from abc import abstractmethod, ABC
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from enre.ent.entity import Class, Entity, NamespaceType, Attribute, Function


class ValueInfo:
    """ValueInfo contain the part of analyze result of an expression.

    ValueInfo of an expression could be changed during analyzing,
    when the analyzed expression corresponds to an entity whose
    analyze progress haven't finished.
    """

    @classmethod
    def get_any(cls) -> "AnyType":
        return _any_type

    @abstractmethod
    def join(self, rhs: "ValueInfo") -> "ValueInfo":
        pass

    @staticmethod
    def type_name_remove_builtins_prefix(name: str) -> str:
        if name.startswith("builtins."):
            return name.removeprefix("builtins.")
        else:
            return name
    @staticmethod
    def type_name(t: "ValueInfo") -> str:
        # try:
        #     if isinstance(t, InstanceType):
        #         return ValueInfo.type_name_remove_builtins_prefix(t.get_class_ent().longname.longname)
        #     elif isinstance(t, ConstructorType):
        #         return ValueInfo.type_name_remove_builtins_prefix(t.to_class_type().get_class_ent().longname.longname)
        #     elif isinstance(t, AttributeType):
        #         return ValueInfo.type_name_remove_builtins_prefix(t.attr_ent.longname.longname)
        #     elif isinstance(t, AttrInstanceType):
        #         return ValueInfo.type_name_remove_builtins_prefix(t.attr_ent.longname.longname)
        #     elif isinstance(t, FunctionType) or isinstance(t, MethodType):
        #         return ValueInfo.type_name_remove_builtins_prefix(t.func_ent.longname.longname)
        #     elif isinstance(t, DictType):  # dict[str, str | int]
        #         temp = "dict["
        #         key = t.key
        #         value = t.value
        #         temp = temp + ValueInfo.type_name(key) + ", " + ValueInfo.type_name(value)
        #         temp += "]"
        #         return temp
        #     elif isinstance(t, UnionType):
        #         temp = "("
        #         types = list(t.types)
        #         for i in range(len(types)):
        #             if i > 0:
        #                 temp += " | "
        #             temp = temp + ValueInfo.type_name(types[i])
        #         temp += ")"
        #         return temp
        #     elif isinstance(t, TupleType):
        #         temp = "tuple["
        #         types = t.positional
        #         for i in range(len(types)):
        #             if i != 0:
        #                 temp = temp + ", "
        #             temp = temp + ValueInfo.type_name(
        #                 types[i]
        #             )
        #         temp = temp + "]"
        #         return temp
        #     elif isinstance(t, ListType):
        #         temp = "list["
        #         types = t.positional
        #         for i in range(len(types)):
        #             if i != 0:
        #                 temp = temp + ", "
        #             temp = temp + ValueInfo.type_name(
        #                 types[i]
        #             )
        #         temp = temp + "]"
        #         return temp
        #     elif isinstance(t, AnyType):
        #         return "Any"
        #     else:
        #         return "Unknown"
        # except RecursionError:
        #     return "Any"
        ...

    def __str__(self):
        return "Unknown"


class InstanceType(ValueInfo):
    def __init__(self, class_ent: "Class"):
        self.class_ent = class_ent

    def lookup_attr(self, attr: str) -> List["Entity"]:
        return self.class_ent.get_attribute(attr)

    def join(self, rhs: "ValueInfo") -> "ValueInfo":
        return UnionType.union(self, rhs)

    def get_class_ent(self):
        return self.class_ent

    def __str__(self):
        return ValueInfo.type_name_remove_builtins_prefix(self.class_ent.longname.longname)


class AttrInstanceType(ValueInfo):
    def __init__(self, attr_ent: "Attribute"):
        self.attr_ent = attr_ent

    def lookup_attr(self, attr: str) -> List["Entity"]:
        return self.attr_ent.get_attribute(attr)

    def join(self, rhs: "ValueInfo") -> "ValueInfo":
        return UnionType.union(self, rhs)

    def get_attr_ent(self):
        return self.attr_ent

    def __str__(self):
        return ValueInfo.type_name_remove_builtins_prefix(self.attr_ent.longname.longname)


class AttributeType(ValueInfo):
    def __init__(self, attr_ent: "Attribute"):
        self.attr_ent = attr_ent

    def lookup_attr(self, attr: str) -> List["Entity"]:
        return self.attr_ent.get_attribute(attr)

    def to_attr_type(self) -> AttrInstanceType:
        return AttrInstanceType(self.attr_ent)

    def join(self, rhs: "ValueInfo") -> "ValueInfo":
        return UnionType.union(self, rhs)

    def __str__(self):
        return ValueInfo.type_name_remove_builtins_prefix(self.attr_ent.longname.longname)


class FunctionType(ValueInfo):
    def __init__(self, func_ent: "Function"):
        self.func_ent = func_ent

    def join(self, rhs: "ValueInfo") -> "ValueInfo":
        return UnionType.union(self, rhs)

    def __str__(self):
        return ValueInfo.type_name_remove_builtins_prefix(self.func_ent.longname.longname)


class MethodType(ValueInfo):
    def __init__(self, func_ent: "Function"):
        self.func_ent = func_ent

    def join(self, rhs: "ValueInfo") -> "ValueInfo":
        return UnionType.union(self, rhs)

    def __str__(self):
        return ValueInfo.type_name_remove_builtins_prefix(self.func_ent.longname.longname)


class ConstructorType(ValueInfo):
    def __init__(self, class_ent: "Class"):
        self.class_ent = class_ent

    def lookup_attr(self, attr: str) -> List["Entity"]:
        return self.class_ent.get_attribute(attr)

    def to_class_type(self) -> InstanceType:
        return InstanceType(self.class_ent)

    def join(self, rhs: "ValueInfo") -> "ValueInfo":
        if isinstance(rhs, ConstructorType) and rhs.class_ent == self.class_ent:
            return self
        else:
            return UnionType.union(self, rhs)

    def __str__(self):
        return ValueInfo.type_name_remove_builtins_prefix(self.class_ent.longname.longname)


class ModuleType(ValueInfo):

    def __init__(self, names: "NamespaceType"):
        self._names = names

    @property
    def namespace(self) -> "NamespaceType":
        return self._names

    def join(self, rhs: "ValueInfo") -> "ValueInfo":
        return ValueInfo.get_any()

    def __str__(self):
        return "Module"


class PackageType(ValueInfo):
    def __init__(self, names: "NamespaceType"):
        self._names = names

    @property
    def namespace(self) -> "NamespaceType":
        return self._names

    def join(self, rhs: "ValueInfo") -> "ValueInfo":
        return ValueInfo.get_any()

    def __str__(self):
        return "Package"


class DictType(ValueInfo):
    def __init__(self, dict_type: "ValueInfo"):
        self.key: "ValueInfo" = ValueInfo.get_any()
        self.value: "ValueInfo" = ValueInfo.get_any()
        self.dict_type: "ValueInfo" = dict_type
        self.dict_dict = dict()
        self.str_ing = False

    def join(self, rhs: "ValueInfo") -> "ValueInfo":
        return UnionType.union(self, rhs)

    def add(self, key: "ValueInfo", value: "ValueInfo"):
        self.key = UnionType.union(self.key, key)
        self.value = UnionType.union(self.value, value)

    def get_dict_type(self):
        return self.dict_type

    def __str__(self):
        if self.str_ing:
            return "Any"
        self.str_ing = True
        temp = "dict["
        key_str = self.key.__str__()
        value_str = self.value.__str__()
        temp += key_str
        temp += ", "
        temp += value_str
        temp += "]"
        self.str_ing = False
        return temp


class ListType(ValueInfo):
    def __init__(self, positional: List[ValueInfo], list_type: "ValueInfo"):
        self.list_type: "ValueInfo" = list_type
        self.positional: List[ValueInfo] = positional
        self.str_ing = False

    def join(self, rhs: "ValueInfo") -> "ValueInfo":
        return UnionType.union(self, rhs)

    def get(self, index: int) -> "ValueInfo":
        return self.positional[index]

    def __eq__(self, other):
        if isinstance(other, ListType):
            if len(self.positional) == len(other.positional):
                _this = self.__str__()
                _other = other.__str__()
                if _this == _other:
                    return True
                else:
                    return False
            else:
                return False
        else:
            return False

    def __hash__(self):
        for i in range(len(self.positional)):
            if self.positional[i] == self:
                self.positional[i] = ValueInfo.get_any()
        return hash(tuple(self.positional))

    def __str__(self):
        if self.str_ing:
            return "Any"
        self.str_ing = True
        temp = "list["
        types = self.positional
        for i in range(len(types)):
            if i != 0:
                temp = temp + ", "
            typ_str = types[i].__str__()
            temp += typ_str
        temp = temp + "]"
        self.str_ing = False
        return temp


class UnionType(ValueInfo):
    def __init__(self, *tys):
        self.types = set[ValueInfo]()
        self.str_ing = False
        for ty in tys:
            if isinstance(ty, list):
                ty = ValueInfo.get_any()
            self.types.add(ty)

    def join(self, rhs: "ValueInfo") -> "ValueInfo":
        if isinstance(rhs, UnionType):
            return UnionType.union_union(self, rhs)
        else:
            self.types.add(rhs)
        return self

    def add(self, tys: List[ValueInfo]):
        for ty in tys:
            self.types.add(ty)
    @staticmethod
    def union_tuple(u: "TupleType", v: "TupleType") -> "ValueInfo":
        values: List[ValueInfo] = []

        values.extend(u.positional)
        values.extend(v.positional)

        union = UnionType()
        union.add(values)
        return union

    @staticmethod
    def union_union(u: "UnionType", v: "UnionType") -> "UnionType":
        values: List[ValueInfo] = []

        values.extend(list(u.types))
        values.extend(list(v.types))

        union = UnionType()
        union.add(values)
        return union

    @staticmethod
    def union(u: "ValueInfo", v: "ValueInfo") -> "ValueInfo":
        if not u and not v:
            return ValueInfo.get_any()
        if u is None or v is None:
            return u if u else v
        elif u == v:
            return u
        elif isinstance(u, AnyType) and isinstance(v, AnyType):
            return u
        elif not isinstance(u, AnyType) and isinstance(v, AnyType):
            return u
        elif not isinstance(v, AnyType) and isinstance(u, AnyType):
            return v
        elif isinstance(u, TupleType) and isinstance(v, TupleType):
            return UnionType.union_tuple(u, v)
        elif isinstance(u, UnionType):
            return u.join(v)
        elif isinstance(v, UnionType):
            return v.join(u)
        else:
            return UnionType(u, v)

    def __str__(self):
        if self.str_ing:
            return "Any"
        self.str_ing = True
        temp = "("
        types = list(self.types)
        for i in range(len(types)):
            if i > 0:
                temp += " | "
            typ_str = types[i].__str__()
            temp += typ_str
        temp += ")"
        self.str_ing = False
        return temp


class TupleType(ValueInfo):
    def __init__(self, tuple_type: "ValueInfo"):
        self.positional: List[ValueInfo] = []
        self.tuple_type: "ValueInfo" = tuple_type
        self.str_ing = False

    def join(self, rhs: "ValueInfo") -> "ValueInfo":
        return UnionType.union(self, rhs)

    def add(self, tys: List[ValueInfo]):
        # but actually, tuple is not mutable
        # here, we just make tuple rather than change tuple
        for ty in tys:
            self.positional.append(ty)

    def add_single(self, ty: ValueInfo):
        self.positional.append(ty)

    def __str__(self):
        if self.str_ing:
            return "Any"
        self.str_ing = True
        temp = "tuple["
        types = self.positional
        for i in range(len(types)):
            if i != 0:
                temp = temp + ", "
            typ_str = types[i].__str__()
            temp += typ_str
        temp = temp + "]"
        self.str_ing = False
        return temp


class AnyType(ValueInfo):
    def join(self, rhs: "ValueInfo") -> "ValueInfo":
        if not isinstance(rhs, AnyType):
            return rhs
        else:
            return self

    def __str__(self):
        return "Any"


class CallType:
    def __init__(self, args_type: "ValueInfo", return_type: "ValueInfo" = AnyType()):
        self.args_type = args_type
        self.return_type = return_type

    def set_return_type(self, return_type: "ValueInfo"):
        self.return_type = UnionType.union(self.return_type, return_type)


_any_type = AnyType()
