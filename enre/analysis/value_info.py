from abc import abstractmethod, ABC
from typing import TYPE_CHECKING, List, Set

if TYPE_CHECKING:
    from enre.ent.entity import Class, Entity, NamespaceType, Function, UnknownVar, ReferencedAttribute


class ValueInfo:
    """ValueInfo contain the part of analyze result of an expression.

    ValueInfo of an expression could be changed during analyzing,
    when the analyzed expression corresponds to an entity whose
    analyze progress haven't finished.
    """

    def __init__(self):
        self.paras: List["ValueInfo"] = []

    @classmethod
    def get_any(cls) -> "AnyType":
        return _any_type

    @classmethod
    def get_none(cls) -> "NoneType":
        return _none_type

    @abstractmethod
    def join(self, rhs: "ValueInfo") -> "ValueInfo":
        pass

    @abstractmethod
    def type_equals(self, other: "ValueInfo") -> bool:
        pass

    @staticmethod
    def type_name_remove_builtins_prefix(name: str) -> str:
        if name.startswith("builtins."):
            return name.removeprefix("builtins.")
        else:
            return name

    def __str__(self):
        return "Unknown"


class InstanceType(ValueInfo):
    def __init__(self, class_ent: "Class"):
        self.class_ent = class_ent
        super().__init__()

    def lookup_attr(self, attr: str, manager) -> List["Entity"]:
        return self.class_ent.get_attribute(attr, manager)

    def join(self, rhs: "ValueInfo") -> "ValueInfo":
        return UnionType.union(self, rhs)

    def get_class_ent(self):
        return self.class_ent

    def type_equals(self, other):
        if isinstance(other, (ConstructorType, InstanceType)):
            return self.__str__() == other.__str__()
        else:
            return False

    def __str__(self):
        return ValueInfo.type_name_remove_builtins_prefix(self.class_ent.longname.longname)


class ReferencedAttrType(ValueInfo):
    def __init__(self, referenced_attr_ent: "ReferencedAttribute"):
        self.referenced_attr_ent = referenced_attr_ent
        super().__init__()

    def lookup_attr(self, attr: str) -> List["Entity"]:
        return self.referenced_attr_ent.get_attribute(attr)

    def join(self, rhs: "ValueInfo") -> "ValueInfo":
        return UnionType.union(self, rhs)

    def type_equals(self, other):
        if isinstance(other, ReferencedAttrType):
            return self.__str__() == other.__str__()
        else:
            return False

    def __str__(self):
        return ValueInfo.type_name_remove_builtins_prefix(self.referenced_attr_ent.longname.longname)


class UnknownVarType(ValueInfo):
    def __init__(self, unknown_var_ent: "UnknownVar"):
        self.unknown_var_ent = unknown_var_ent
        super().__init__()

    def lookup_attr(self, attr: str) -> List["Entity"]:
        return self.unknown_var_ent.get_attribute(attr)

    def join(self, rhs: "ValueInfo") -> "ValueInfo":
        return UnionType.union(self, rhs)

    def type_equals(self, other):
        if isinstance(other, UnknownVarType):
            return self.__str__() == other.__str__()
        else:
            return False

    def __str__(self):
        if not self.paras:
            return ValueInfo.type_name_remove_builtins_prefix(self.unknown_var_ent.longname.longname)
        else:
            temp = ValueInfo.type_name_remove_builtins_prefix(self.unknown_var_ent.longname.longname)
            temp += "["
            for i in range(len(self.paras)):
                if i != 0:
                    temp += ", "
                temp += self.paras[i].__str__()
            temp += "]"
            return temp


class FunctionType(ValueInfo):
    def __init__(self, func_ent: "Function"):
        self.func_ent = func_ent
        super().__init__()

    def join(self, rhs: "ValueInfo") -> "ValueInfo":
        return UnionType.union(self, rhs)

    def type_equals(self, other):
        if isinstance(other, FunctionType):
            return self.__str__() == other.__str__()
        else:
            return False

    def __str__(self):
        return ValueInfo.type_name_remove_builtins_prefix(self.func_ent.longname.longname)


class MethodType(ValueInfo):
    def __init__(self, func_ent: "Function"):
        self.func_ent = func_ent
        super().__init__()

    def join(self, rhs: "ValueInfo") -> "ValueInfo":
        return UnionType.union(self, rhs)

    def type_equals(self, other):
        if isinstance(other, MethodType):
            return self.__str__() == other.__str__()
        else:
            return False

    def __str__(self):
        return ValueInfo.type_name_remove_builtins_prefix(self.func_ent.longname.longname)


class ConstructorType(ValueInfo):
    def __init__(self, class_ent: "Class"):
        self.class_ent = class_ent
        super().__init__()

    def lookup_attr(self, attr: str, manager) -> List["Entity"]:
        return self.class_ent.get_attribute(attr, manager)

    def to_class_type(self) -> InstanceType:
        return InstanceType(self.class_ent)

    def join(self, rhs: "ValueInfo") -> "ValueInfo":
        if isinstance(rhs, ConstructorType) and rhs.class_ent == self.class_ent:
            return self
        else:
            return UnionType.union(self, rhs)

    def __str__(self):
        return ValueInfo.type_name_remove_builtins_prefix(self.class_ent.longname.longname)
        # return self.class_ent.longname.longname

    def type_equals(self, other):
        if isinstance(other, (ConstructorType, InstanceType)):
            return self.__str__() == other.__str__()
        else:
            return False

    # def __eq__(self, other):
    #     if type(other) == type(self):
    #         return self.__str__() == other.__str__()
    #     else:
    #         return super(ConstructorType, self).__eq__(other)
    #
    # def __hash__(self):
    #     return hash(self.__str__())


class ModuleType(ValueInfo):

    def __init__(self, names: "NamespaceType"):
        self._names = names
        super().__init__()

    @property
    def namespace(self) -> "NamespaceType":
        return self._names

    def join(self, rhs: "ValueInfo") -> "ValueInfo":
        return ValueInfo.get_any()

    def type_equals(self, other):
        if isinstance(other, ModuleType):
            return True
        else:
            return False

    def __str__(self):
        return "Module"


class PackageType(ValueInfo):
    def __init__(self, names: "NamespaceType"):
        self._names = names
        super().__init__()

    @property
    def namespace(self) -> "NamespaceType":
        return self._names

    def join(self, rhs: "ValueInfo") -> "ValueInfo":
        return ValueInfo.get_any()

    def type_equals(self, other):
        if isinstance(other, PackageType):
            return True
        else:
            return False

    def __str__(self):
        return "Package"


class DictType(InstanceType):
    def __init__(self, dict_class_ent: "Class"):
        self.key: "ValueInfo" = ValueInfo.get_any()
        self.value: "ValueInfo" = ValueInfo.get_any()
        self.dict_dict = dict()
        self.str_ing = False
        super().__init__(dict_class_ent)

    def join(self, rhs: "ValueInfo") -> "ValueInfo":
        return UnionType.union(self, rhs)

    def add(self, key: "ValueInfo", value: "ValueInfo"):
        self.key = UnionType.union(self.key, key)
        self.value = UnionType.union(self.value, value)


    def type_equals(self, other):
        if isinstance(other, DictType):
            return self.key.type_equals(other.key) and self.value.type_equals(other.value)
        else:
            return False

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


class ListType(InstanceType):
    def __init__(self, positional: List[ValueInfo], list_class_ent: "Class"):
        self.positional: List[ValueInfo] = positional

        self.str_ing = False
        super().__init__(list_class_ent)

    def join(self, rhs: "ValueInfo") -> "ValueInfo":
        return UnionType.union(self, rhs)

    def get(self, index: int) -> "ValueInfo":
        return self.positional[index]

    def type_equals(self, other):
        if isinstance(other, ListType):
            if len(self.positional) == len(other.positional):
                if len(self.positional) == 0:
                    return True
                for i in range(len(self.positional)):
                    if not self.positional[i].type_equals(other.positional[i]):
                        return False
            else:
                return False
        else:
            return False

    # def __eq__(self, other):
    #     if isinstance(other, ListType):
    #         if len(self.positional) == len(other.positional):
    #             _this = self.__str__()
    #             _other = other.__str__()
    #             if _this == _other:
    #                 return True
    #             else:
    #                 return False
    #         else:
    #             return False
    #     else:
    #         return False
    #
    # def __hash__(self):
    #     for i in range(len(self.positional)):
    #         if self.positional[i] == self:
    #             self.positional[i] = ValueInfo.get_any()
    #     return hash(tuple(self.positional))

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


class SetType(InstanceType):
    def __init__(self, set_set: Set["ValueInfo"], set_class_ent: "Class"):
        self.set_set = set_set

        self.str_ing = False
        super().__init__(set_class_ent)

    def join(self, rhs: "ValueInfo") -> "ValueInfo":
        if isinstance(rhs, SetType):
            self.set_set = self.set_set.union(rhs.set_set)
            return self
        else:
            return UnionType.union(self, rhs)

    def type_equals(self, other):
        if isinstance(other, SetType):
            if len(self.set_set) == len(other.set_set):
                for item in self.set_set:
                    if item not in other.set_set:
                        return False
                for item in other.set_set:
                    if item not in self.set_set:
                        return False
                return True
            else:
                return False
        else:
            return False

    def __str__(self):
        if self.str_ing:
            return "Any"
        self.str_ing = True
        temp = "set["
        types = list(self.set_set)
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

        super().__init__()

    def join(self, rhs: "ValueInfo") -> "ValueInfo":
        if isinstance(rhs, UnionType):
            return UnionType.union_union(self, rhs)
        else:
            exists = False
            for t in self.types:
                if t.type_equals(rhs):
                    exists = True
            if not exists:
                self.types.add(rhs)
        return self

    def add(self, tys: List[ValueInfo]):
        for ty in tys:
            self.types.add(ty)

    def type_equals(self, other):
        if isinstance(other, UnionType):
            if len(self.types) == len(other.types):
                for item in self.types:
                    if item not in other.types:
                        return False
                for item in other.types:
                    if item not in self.types:
                        return False
                return True
            else:
                return False
        else:
            return False

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

        for item in v.types:
            flag = False
            for t in values:
                if item.type_equals(t):
                    flag = True
                    break
            if not flag:
                values.append(item)

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
        elif u.type_equals(v):
            return v
        elif isinstance(u, AnyType) or isinstance(v, AnyType):
            return u if isinstance(v, AnyType) else v
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


class TupleType(InstanceType):
    def __init__(self, tuple_class_ent: "Class"):
        self.positional: List[ValueInfo] = []
        self.str_ing = False
        super().__init__(tuple_class_ent)

    def join(self, rhs: "ValueInfo") -> "ValueInfo":
        return UnionType.union(self, rhs)

    def add(self, tys: List[ValueInfo]):
        for ty in tys:
            self.positional.append(ty)

    def add_single(self, ty: ValueInfo):
        self.positional.append(ty)

    def type_equals(self, other):
        if isinstance(other, TupleType):
            if len(self.positional) == len(other.positional):
                for i in range(len(self.positional)):
                    if not self.positional[i].type_equals(other.positional[i]):
                        return False
            else:
                return False
        else:
            return False

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


class ConstantType(ValueInfo):
    def __init__(self, value: bool | int | str):
        self.value = value
        super().__init__()

    def join(self, rhs: "ValueInfo") -> "ValueInfo":
        pass

    def __str__(self):
        return str(self.value)

    def type_equals(self, other):
        if isinstance(other, ConstantType):
            if self.value != other.value:
                return False
            else:
                return True
        else:
            return False


class AnyType(ValueInfo):
    def join(self, rhs: "ValueInfo") -> "ValueInfo":
        if not isinstance(rhs, AnyType):
            return rhs
        else:
            return self

    def __str__(self):
        return "Any"

    # def __eq__(self, other):
    #     if type(self) == type(other):
    #         return True
    #     else:
    #         return super(AnyType, self).__eq__(other)
    #
    # def __hash__(self):
    #     return hash(self.__str__())

    def type_equals(self, other):
        if isinstance(other, AnyType):
            return True
        else:
            return False


class NoneType(ValueInfo):
    def join(self, rhs: "ValueInfo") -> "ValueInfo":
        return self

    def __str__(self):
        return "None"

    def type_equals(self, other):
        if isinstance(other, NoneType):
            return True
        else:
            return False


class CallType:
    def __init__(self, args_type: "ValueInfo", return_type: "ValueInfo" = AnyType()):
        self.args_type = args_type
        self.return_type = return_type

    def set_return_type(self, return_type: "ValueInfo"):
        self.return_type = UnionType.union(self.return_type, return_type)


# def resolve_circular_value(value: ValueInfo, visit_set: Set = None):
#     if not visit_set:
#         visit_set = set()
#     if value not in visit_set:
#         visit_set.add(value)
#     else:
#         return None
#     if isinstance(value, UnionType):
#         for t in value.types.copy():
#             r = resolve_circular_value(t, visit_set)
#             if not r:
#                 print(t)
#                 value.types.remove(t)
#     elif isinstance(value, ListType):
#         for t in value.positional:
#             r = resolve_circular_value(t, visit_set)
#             if not r:
#                 print(t)
#                 value.positional.remove(t)
#     elif isinstance(value, TupleType):
#         for t in value.positional:
#             r = resolve_circular_value(t, visit_set)
#             if not r:
#                 print(t)
#                 value.positional.remove(t)
#     elif isinstance(value, SetType):
#         for t in value.set_set.copy():
#             r = resolve_circular_value(t, visit_set)
#             if not r:
#                 print(t)
#                 value.set_set.remove(t)
#     elif isinstance(value, DictType):
#         value.key = resolve_circular_value(value.key)
#         value.value = resolve_circular_value(value.value)
#
#     return value


_any_type = AnyType()
_none_type = NoneType()
