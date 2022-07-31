import ast
import itertools
import typing
from abc import abstractmethod, ABC
from collections import defaultdict
from dataclasses import dataclass
from typing import List
from typing import TypeAlias, Dict, Optional, Sequence

from enre.cfg.HeapObject import HeapObject, ClassObject, FunctionObject, ModuleObject, NameSpace
from enre.ent.entity import Class, Entity, Parameter, Module, UnknownVar, \
    ClassAttribute, Package, Alias, ModuleAlias, PackageAlias
from enre.ent.entity import Function, Variable

if typing.TYPE_CHECKING:
    from enre.analysis.analyze_expr import ExpressionContext


class ModuleSummary:

    @abstractmethod
    def get_namespace(self) -> NameSpace:
        ...

    @property
    @abstractmethod
    def rules(self) -> "List[Rule]":
        ...

    @property
    @abstractmethod
    def module_head(self) -> "str":
        ...

    @abstractmethod
    def add_child(self, child: "ModuleSummary") -> None:
        ...

    @abstractmethod
    def name(self) -> str:
        ...

    def __str__(self) -> str:
        ret = "{}\n".format(self.module_head)
        for rule in self.rules:
            ret += "\t{}\n".format(str(rule))
        return ret

    @abstractmethod
    def get_object(self) -> HeapObject:
        pass


class FileSummary(ModuleSummary):
    def __init__(self, module_ent: Module):
        self.module = module_ent
        self._rules: "List[Rule]" = []
        self._children: "List[ModuleSummary]" = []
        self.namespace: NameSpace = defaultdict(set)
        self._correspond_obj: Optional[ModuleObject] = None

    @property
    def module_head(self) -> "str":
        return f"File Summary of {self.module.longname.longname}"

    def name(self) -> str:
        return self.module.longname.name

    @property
    def rules(self) -> "List[Rule]":
        return self._rules

    def add_child(self, child: "ModuleSummary") -> None:
        self._children.append(child)

    def get_object(self) -> ModuleObject:
        if self._correspond_obj:
            return self._correspond_obj
        else:
            new_obj = ModuleObject(self.module, self, defaultdict(set))
            self._correspond_obj = new_obj
            return new_obj

    def get_namespace(self) -> NameSpace:
        return self.get_object().get_namespace()

    def __hash__(self) -> int:
        return id(self)


class ClassSummary(ModuleSummary):
    @property
    def module_head(self) -> "str":
        return f"Class Summary of {self.cls.longname.longname}"

    def name(self) -> str:
        return self.cls.longname.name

    def __init__(self, cls: Class):
        self.cls = cls
        self._rules: "List[Rule]" = []
        self._children: "List[ModuleSummary]" = []
        self.namespace: NameSpace = defaultdict(set)
        self._correspond_obj: Optional[ClassObject] = None

    @property
    def rules(self) -> "List[Rule]":
        return self._rules

    def add_child(self, child: "ModuleSummary") -> None:
        self._children.append(child)

    def get_object(self) -> ClassObject:
        if self._correspond_obj:
            return self._correspond_obj
        else:
            namespace = defaultdict(set)
            for child in self._children:
                namespace[child.name()].add(child.get_object())
            new_obj = ClassObject(self.cls, self, namespace)
            self._correspond_obj = new_obj
            return new_obj

    def get_namespace(self) -> NameSpace:
        return self.get_object().get_namespace()

    def __hash__(self) -> int:
        return id(self)


class FunctionSummary(ModuleSummary):

    def __init__(self, func: Function) -> None:
        self.func = func
        self._rules: List[Rule] = []
        self.parameter_list: List[str] = list()
        self._correspond_obj: Optional[FunctionObject] = None

    def get_object(self) -> FunctionObject:
        if self._correspond_obj:
            return self._correspond_obj
        else:
            new_obj = FunctionObject(self.func, self)
            self._correspond_obj = new_obj
            return new_obj

    def add_child(self, child: "ModuleSummary") -> None:
        return
        # todo: remove this method in the future

    def name(self) -> str:
        return self.func.longname.name

    def get_namespace(self) -> NameSpace:
        return self.get_object().get_namespace()

    @property
    def module_head(self) -> "str":
        return f"Function Summary of {self.func.longname.longname}"

    @property
    def rules(self) -> "List[Rule]":
        return self._rules

    def __hash__(self) -> int:
        return id(self)


class Scene:

    def __init__(self) -> None:
        self.summaries: List[ModuleSummary] = []
        self.summary_map: Dict[Entity, ModuleSummary] = dict()


class StoreAble(object):
    ...


StoreAbles: TypeAlias = Sequence[StoreAble]


class Temporary(StoreAble):
    """
    Temporary is not corresponding to any variable entity of source code, just a temporary
    """
    __match_args__ = ("_name",)

    def __init__(self, name: str, expr: ast.expr) -> None:
        self._name: str = name
        self._expr: ast.expr = expr

    def name(self) -> str:
        return self._name

    def __str__(self) -> str:
        return f"temporary: {self._name}"


class VariableLocal(StoreAble):
    __match_args__ = ("_variable",)

    def __init__(self, variable: Variable) -> None:
        self._variable = variable
        self._parent_func = None

    def name(self) -> str:
        return self._variable.longname.name

    def __str__(self) -> str:
        return f"local variable: {self.name()}"


class ParameterLocal(StoreAble):
    __match_args__ = ("_parameter",)

    def __init__(self, parameter: Parameter) -> None:
        self._parameter = parameter

    def name(self) -> str:
        return self._parameter.longname.name

    def __str__(self) -> str:
        return f"parameter: {self.name()}"


class VariableOuter(StoreAble):
    def __init__(self, variable: VariableLocal, func: FunctionSummary) -> None:
        self._varialbe = variable

    def name(self) -> str:
        return self._varialbe.name()

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
        return f"functional value {self.func.longname.longname}"

    def name(self) -> str:
        return self.func.longname.name


@dataclass(frozen=True)
class ClassConst(StoreAble):
    cls: Class

    def __str__(self) -> str:
        return f"class value {self.cls.longname.longname}"

    def name(self) -> str:
        return self.cls.longname.name


@dataclass(frozen=True)
class ModuleConst(StoreAble):
    mod: Module

    def __str__(self) -> str:
        return f"module {self.mod.longname}"

    def name(self) -> str:
        return self.mod.longname.name


@dataclass(frozen=True)
class PackageConst(StoreAble):
    package: Package

    def __str__(self) -> str:
        return f"package {self.package.longname}"

    def name(self) -> str:
        return self.package.longname.name


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
class Return(Rule):
    ret_value: StoreAble
    expr: ast.expr

    def __str__(self) -> str:
        return "return {}".format(str(self.ret_value))


@dataclass(frozen=True)
class AddBase(Rule):
    cls: ClassConst
    bases: Sequence[StoreAble]


class SummaryBuilder(object):
    _rules: List[Rule]

    def __init__(self, mod: ModuleSummary) -> None:
        self.mod = mod
        self._rules = mod.rules
        self._temporary_index = 0

    def add_move(self, lhs: StoreAble, rhs: StoreAble) -> StoreAble:
        self._rules.append(ValueFlow(lhs, rhs))
        return lhs

    def add_move_temp(self, rhs: StoreAble, expr: ast.expr) -> Temporary:
        index = self._temporary_index
        self._temporary_index += 1
        temp = Temporary(f"___t_{index}", expr)
        self.add_move(temp, rhs)
        return temp

    def add_invoke(self, func: StoreAbles, args: List[StoreAbles], expr: ast.expr) -> StoreAbles:
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
            ret.append(self.add_move_temp(invoke, expr))
        return ret

    def add_inherit(self, cls: Class, args: List[StoreAbles]) -> None:
        cls_store = ClassConst(cls)
        for args_stores in list(itertools.product(*(args))):
            add_base = AddBase(cls_store, args_stores)
            self._rules.append(add_base)

    def load_field(self, field_accesses: StoreAbles, field: str, context: "ExpressionContext",
                   expr: ast.expr) -> StoreAbles:
        from enre.analysis.analyze_expr import SetContext
        ret: List[StoreAble] = []
        for fa in field_accesses:
            if isinstance(context, SetContext):
                ret.append(FieldAccess(fa, field))
            else:
                ret.append(self.add_move_temp(FieldAccess(fa, field), expr))
            # we have to return a field access here, because only this can resolve set behavior correctly
        return ret

    def add_return(self, return_stores: StoreAbles, expr: ast.expr) -> None:
        assert isinstance(self.mod, FunctionSummary)
        for return_store in return_stores:
            self._rules.append(Return(return_store, expr))

    def add_child(self, summary: ModuleSummary) -> None:
        self.mod.add_child(summary)


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
        case PackageAlias() as pa:
            ret = get_named_store_able(pa.package_ent)
        case _ as e:
            raise NotImplementedError(f"{e} not implemented yet")
    return ret
