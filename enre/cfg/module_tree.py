import itertools
from abc import abstractmethod, ABC
from dataclasses import dataclass
from typing import List
from typing import TypeAlias, Set, Dict, Optional, Sequence

from enre.cfg.AbstractObject import AbstractObject
from enre.ent.entity import Class, Entity, Parameter, Module, NameSpaceEntity, UnknownVar, \
    ClassAttribute, Package, Alias, ModuleAlias
from enre.ent.entity import Function, Variable

ObjectSlot: TypeAlias = Set[AbstractObject]


class ModuleSummary(ABC):
    @property
    @abstractmethod
    def rules(self) -> "List[Rule]":
        ...

    @property
    @abstractmethod
    def module_head(self) -> "str":
        ...

    def __str__(self) -> str:
        ret = "{}\n".format(self.module_head)
        for rule in self.rules:
            ret += "\t{}\n".format(str(rule))
        return ret


class FileSummary(ModuleSummary):
    def __init__(self, module_ent: Module):
        self.module = module_ent
        self._rules: "List[Rule]" = []

    @property
    def module_head(self) -> "str":
        return f"File Summary of {self.module.longname.longname}"

    @property
    def rules(self) -> "List[Rule]":
        return self._rules


class ClassSummary(ModuleSummary):
    @property
    def module_head(self) -> "str":
        return f"Class Summary of {self.cls.longname.longname}"

    def __init__(self, cls: Class):
        self.cls = cls
        self._rules: "List[Rule]" = []

    @property
    def rules(self) -> "List[Rule]":
        return self._rules


class FunctionSummary(ModuleSummary):
    variable_slots: Dict[str, ObjectSlot]

    parameter_slots: Dict[str, ObjectSlot]

    def __init__(self, func: Function) -> None:
        self.func = func
        self._rules: List[Rule] = []

    @property
    def module_head(self) -> "str":
        return f"Function Summary of {self.func.longname.longname}"

    @property
    def rules(self) -> "List[Rule]":
        return self._rules


class StoreAble(object):
    ...


StoreAbles: TypeAlias = Sequence[StoreAble]


class Temporary(StoreAble):
    """
    Temporary is not corresponding to any variable entity of source code, just a temporary
    """

    def __init__(self, name: str) -> None:
        self._name = name

    def name(self) -> str:
        return self._name

    def __str__(self) -> str:
        return f"temporary: {self._name}"


class VariableLocal(StoreAble):
    def __init__(self, variable: Variable) -> None:
        self._variable = variable
        self._parent_func = None

    def name(self) -> str:
        return self._variable.longname.name

    def __str__(self) -> str:
        return f"local variable: {self.name()}"


class ParameterLocal(StoreAble):
    def __init__(self, parameter: Parameter) -> None:
        self._parameter = parameter

    def name(self) -> str:
        return self._parameter.longname.name

    def __str__(self) -> str:
        return f"parameter: {self.name()}"


class VariableOuter(StoreAble):
    def __init__(self, parameter: Parameter) -> None:
        self._parameter = parameter

    def name(self) -> str:
        return self._parameter.longname.name

    def __str__(self) -> str:
        return self.name()


@dataclass(frozen=True)
class FieldAccess(StoreAble):
    target: StoreAble
    field: str

    def name(self) -> str:
        return "attribute {} of {}".format(self.field, self.target)

    def __str__(self) -> str:
        return self.name()


@dataclass(frozen=True)
class FuncConst(StoreAble):
    func: Function

    def __str__(self) -> str:
        return f"functional value {self.func.longname}"


@dataclass(frozen=True)
class ClassConst(StoreAble):
    cls: Class

    def __str__(self) -> str:
        return f"class value {self.cls.longname.longname}"


@dataclass(frozen=True)
class ModuleConst(StoreAble):
    mod: Module

    def __str__(self) -> str:
        return f"module {self.mod.longname}"


@dataclass(frozen=True)
class PackageConst(StoreAble):
    package: Package

    def __str__(self) -> str:
        return f"package {self.package.longname}"


@dataclass(frozen=True)
class Invoke(StoreAble):
    target: StoreAble
    args: Sequence[StoreAble]

    def __str__(self) -> str:
        return f"function invoke: {self.target}({', '.join(str(arg) for arg in self.args)})"


@dataclass(frozen=True)
class ClassAttributeAccess(StoreAble):
    class_attribute: ClassAttribute

    def __str__(self) -> str:
        return f"class attribute: {self.class_attribute.longname}"


class Rule(ABC):
    ...


@dataclass(frozen=True)
class ValueFlow(Rule):
    lhs: StoreAble
    rhs: StoreAble

    def __str__(self) -> str:
        return "{} <- {}".format(str(self.lhs), str(self.rhs))


@dataclass(frozen=True)
class HasParameter(Rule):
    parameter: Parameter


@dataclass(frozen=True)
class HasInherit(Rule):
    base: StoreAble


@dataclass(frozen=True)
class Return(Rule):
    ret_value: StoreAble

    def __str__(self) -> str:
        return "return {}".format(str(self.ret_value))


class SummaryBuilder(object):
    _rules: List[Rule]

    def __init__(self, mod: ModuleSummary) -> None:
        self.mod = mod
        self._rules = mod.rules
        self._temporary_index = 0

    def add_move(self, lhs: StoreAble, rhs: StoreAble) -> StoreAble:
        self._rules.append(ValueFlow(lhs, rhs))
        return lhs

    def add_move_temp(self, rhs: StoreAble) -> Temporary:
        index = self._temporary_index
        self._temporary_index += 1
        temp = Temporary(f"___t_{index}")
        self.add_move(temp, rhs)
        return temp

    def add_invoke(self, func: StoreAbles, args: List[StoreAbles]) -> StoreAbles:
        ret: List[StoreAble] = []
        args_stores: Sequence[StoreAble]
        func_store: StoreAble
        if not func:
            # invoke nothing if func contains no StoreAble
            return []
        for l in list(itertools.product(*([func] + args))):
            func_store = l[0]
            args_stores = l[1:]
            invoke = Invoke(func_store, args_stores)
            ret.append(self.add_move_temp(invoke))
        return ret

    def load_field(self, field_accesses: StoreAbles, field: str) -> StoreAbles:
        ret: List[StoreAble] = []
        for fa in field_accesses:
            match fa:
                case (VariableLocal() | Temporary() | VariableOuter() | ParameterLocal()) as v:
                    ret.append(FieldAccess(v, field))
                case NameSpaceEntity() as mod:
                    all_member_store_able = []
                    for m in mod.names[field]:
                        if store_able := get_named_store_able(m):
                            all_member_store_able.append(store_able)
                    ret.extend(all_member_store_able)
        return ret

    def add_return(self, return_stores: StoreAbles) -> None:
        for return_store in return_stores:
            self._rules.append(Return(return_store))


def get_named_store_able(ent: Entity) -> Optional[StoreAble]:
    ret: Optional[StoreAble] = None
    match ent:
        case Variable() as v:
            ret = VariableLocal(v)
        case Class() as cls:
            ret = ClassConst(cls)
        case Module() as mod:
            ret = ModuleConst(mod)
        case Parameter() as p:
            ret = ParameterLocal(p)
        case Function() as f:
            ret = FuncConst(f)
        case UnknownVar() as v:
            ret = None
        case Package() as p:
            ret = PackageConst(p)
        case ClassAttribute() as ca:
            ret = ClassAttributeAccess(ca)
        case Alias() as a:
            ret = None
            # todo: handle alias case here
        case ModuleAlias() as ma:
            ret = get_named_store_able(ma.module_ent)
        case _ as e:
            raise NotImplementedError(f"{e} not implemented yet")
    return ret