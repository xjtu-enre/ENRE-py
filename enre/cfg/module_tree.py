import ast
import datetime
import itertools
import typing
from abc import abstractmethod, ABC
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from typing import List, Iterable, Tuple
from typing import TypeAlias, Dict, Optional, Sequence

from enre.cfg.HeapObject import HeapObject, ClassObject, FunctionObject, ModuleObject, NameSpace
from enre.ent.entity import Class, Entity, Parameter, Module, UnknownVar, \
    ClassAttribute, Package, Alias, ModuleAlias, PackageAlias
from enre.ent.entity import Function, Variable

if typing.TYPE_CHECKING:
    from enre.analysis.analyze_expr import ExpressionContext

SyntaxNameSpace: TypeAlias = Dict[ast.expr, str]


class ModuleSummary:

    @abstractmethod
    def get_namespace(self) -> NameSpace:
        ...

    @abstractmethod
    def get_ent(self) -> Entity:
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

    @abstractmethod
    def get_syntax_namespace(self) -> SyntaxNameSpace:
        ...

    def __str__(self) -> str:
        ret = "{}\n".format(self.module_head)
        for rule in self.rules:
            ret += "\t{}\n".format(str(rule))
        return ret

    @abstractmethod
    def get_object(self) -> HeapObject:
        pass

    def get_invokes(self) -> "Iterable[Invoke]":
        rules = self.rules
        invokes = set()
        for r in rules:
            if isinstance(r, ValueFlow) and isinstance(r.rhs, Invoke):
                invokes.add(r.rhs)
            elif isinstance(r, Return) and isinstance(r.ret_value, Invoke):
                invokes.add(r.ret_value)
            elif isinstance(r, AddBase):
                for base in r.bases:
                    if isinstance(base, Invoke):
                        invokes.add(base)
        return invokes


class FileSummary(ModuleSummary):
    def __init__(self, module_ent: Module):
        self.module = module_ent
        self._rules: "List[Rule]" = []
        self._children: "List[ModuleSummary]" = []
        self.namespace: NameSpace = defaultdict(set)
        self._correspond_obj: Optional[ModuleObject] = None
        self._syntax_namespace: SyntaxNameSpace = dict()

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

    def get_ent(self) -> Entity:
        return self.module

    def get_object(self) -> ModuleObject:
        if self._correspond_obj:
            return self._correspond_obj
        else:
            namespace = defaultdict(set)
            for child in self._children:
                namespace[child.name()].add(child.get_object())
            new_obj = ModuleObject(self.module, self, namespace)
            self._correspond_obj = new_obj
            return new_obj

    def get_namespace(self) -> NameSpace:
        return self.get_object().get_namespace()

    def get_syntax_namespace(self) -> SyntaxNameSpace:
        return self._syntax_namespace

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
        self._syntax_namespace: SyntaxNameSpace = dict()

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

    def get_ent(self) -> Entity:
        return self.cls

    def get_namespace(self) -> NameSpace:
        return self.get_object().get_namespace()

    def get_syntax_namespace(self) -> SyntaxNameSpace:
        return self._syntax_namespace

    def __hash__(self) -> int:
        return id(self)


class FunctionSummary(ModuleSummary):

    def __init__(self, func: Function) -> None:
        self.func = func
        self._rules: List[Rule] = []
        self.positional_para_list: List[str] = list()
        self.var_para: Optional[str] = None
        self.kwarg: Optional[str] = None
        self._correspond_obj: Optional[FunctionObject] = None
        self._syntax_namespace: SyntaxNameSpace = dict()

    def get_object(self) -> FunctionObject:
        if self._correspond_obj:
            return self._correspond_obj
        else:
            from enre.cfg.HeapObject import IndexableObject
            new_obj = FunctionObject(self.func, self)
            self._correspond_obj = new_obj
            if self.var_para:
                new_obj.namespace[self.var_para].add(IndexableObject(None, None))
            if self.kwarg:
                new_obj.namespace[self.kwarg].add(IndexableObject(None, None))
            return new_obj

    def get_ent(self) -> Entity:
        return self.func

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

    def get_syntax_namespace(self) -> SyntaxNameSpace:
        return self._syntax_namespace

    def __hash__(self) -> int:
        return id(self)


class Scene:

    def __init__(self) -> None:
        self.summaries: List[ModuleSummary] = []
        self.summary_map: Dict[Entity, ModuleSummary] = dict()


class StoreAble(object):
    ...


class NonConstStoreAble(object):
    @abstractmethod
    def get_syntax_location(self) -> ast.expr:
        ...


StoreAbles: TypeAlias = Sequence[StoreAble]


class Temporary(StoreAble, NonConstStoreAble):
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

    def get_syntax_location(self) -> ast.expr:
        return self._expr


class VariableLocal(StoreAble, NonConstStoreAble):
    __match_args__ = ("_variable",)

    def __init__(self, variable: Variable, expr: ast.expr) -> None:
        self._variable = variable
        self._parent_func = None
        self._expr = expr

    def name(self) -> str:
        return self._variable.longname.name

    def __str__(self) -> str:
        return f"local variable: {self.name()}"

    def get_syntax_location(self) -> ast.expr:
        return self._expr


class ParameterLocal(StoreAble, NonConstStoreAble):
    __match_args__ = ("_parameter",)

    def __init__(self, parameter: Parameter, expr: ast.expr) -> None:
        self._parameter = parameter
        self._expr = expr

    def name(self) -> str:
        return self._parameter.longname.name

    def __str__(self) -> str:
        return f"parameter: {self.name()}"

    def get_syntax_location(self) -> ast.expr:
        return self._expr


class VariableOuter(StoreAble):
    def __init__(self, variable: Variable, scope: Entity) -> None:
        self._varialbe = variable
        self.scope = scope

    def name(self) -> str:
        return self._varialbe.longname.name

    def __str__(self) -> str:
        return f"outer variable: {self.name()}"


@dataclass(frozen=True)
class FieldAccess(StoreAble, NonConstStoreAble):
    target: StoreAble
    field: str
    expr: ast.expr

    def name(self) -> str:
        return "attribute {} of {}".format(self.field, self.target)

    def __str__(self) -> str:
        return self.name()

    def get_syntax_location(self) -> ast.expr:
        return self.expr


@dataclass(frozen=True)
class IndexAccess(StoreAble, NonConstStoreAble):
    target: StoreAble
    expr: ast.expr

    def name(self) -> str:
        return "index accessing {}[*]".format(self.target)

    def __str__(self) -> str:
        return self.name()

    def get_syntax_location(self) -> ast.expr:
        return self.expr


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
class Constant(StoreAble):
    constant: ast.Constant | ast.Str
    constant_cls: "Optional[Class]"

    def __str__(self) -> str:
        return f"Constant {self.constant}"


@dataclass(frozen=True)
class Arguments:
    args: Sequence[StoreAble]
    kwargs: Tuple[Tuple[str, StoreAble], ...]


@dataclass(frozen=True)
class Invoke(StoreAble, NonConstStoreAble):
    target: StoreAble
    args: Arguments
    expr: ast.expr

    def __str__(self) -> str:
        return f"function invoke: {self.target}({', '.join(str(arg) for arg in self.args.args)})"

    def get_syntax_location(self) -> ast.expr:
        return self.expr


@dataclass(frozen=True)
class ClassAttributeAccess(StoreAble):
    class_attribute: ClassAttribute

    def __str__(self) -> str:
        return f"class attribute: {self.class_attribute.longname}"


class IndexableKind(Enum):
    dct = "dict"
    lst = "list"
    tpl = "tuple"


@dataclass(frozen=True)
class IndexableInfo:
    kind: IndexableKind
    cls: Optional[Class]


class ConstantKind(Enum):
    integer = "int"
    string = "str"


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

    def __str__(self) -> str:
        return f"{self.cls} is derived from [{', '.join(str(base) for base in self.bases)}]"


@dataclass(frozen=True)
class AddList(Rule):
    info: IndexableInfo
    lst: StoreAble
    expr: ast.expr

    def __str__(self) -> str:
        return f"{self.lst} contains a list object"


class SummaryBuilder(object):
    _rules: List[Rule]

    def __init__(self, mod: ModuleSummary) -> None:
        self.mod = mod
        self._rules = mod.rules
        self._temporary_index = 0
        self._syntax_name_map = mod.get_syntax_namespace()

    def add_store_able(self, store_able: StoreAble) -> None:
        match store_able:
            case ParameterLocal() | VariableLocal() | Temporary() as t:
                self._syntax_name_map[t.get_syntax_location()] = t.name()

    def add_move(self, lhs: StoreAble, rhs: StoreAble) -> StoreAble:
        self.add_store_able(lhs)
        self.add_store_able(rhs)
        self._rules.append(ValueFlow(lhs, rhs))
        return lhs

    def create_temp(self, expr: ast.expr) -> Temporary:
        index = self._temporary_index
        self._temporary_index += 1
        temp = Temporary(f"___t_{index}", expr)
        return temp

    def add_move_temp(self, rhs: StoreAble, expr: ast.expr) -> Temporary:
        self.add_store_able(rhs)
        temp = self.create_temp(expr)
        self.add_move(temp, rhs)
        self.add_store_able(temp)
        return temp

    def add_invoke(self, func: StoreAbles, args: List[StoreAbles],
                   kwargs: List[Tuple[str, StoreAbles]], invoke_expr: ast.expr) -> StoreAbles:
        ret: List[StoreAble] = []
        args_stores: Sequence[StoreAble]
        func_store: StoreAble
        if not func:
            # invoke nothing if func contains no StoreAble
            return []
        kwargs1: List[List[Tuple[str, StoreAble]]] = []
        keys = list(map(lambda x: x[0], kwargs))
        arg_of_key_args = list(map(lambda x: x[1], kwargs))
        if len(arg_of_key_args)<=7:
            # todo: remove this by self implemented product
            for l in list(itertools.product(*arg_of_key_args)):
                kwargs1.append(list(zip(keys, l)))
        if not kwargs1:
            kwargs1.append([])

        for l in list(itertools.product(*([func] + args))):
            for store in l:
                self.add_store_able(store)
            func_store = l[0]
            self.add_store_able(func_store)
            args_stores = l[1:]
            for key_args in kwargs1:
                arguments = Arguments(args_stores, tuple(key_args))
                invoke = Invoke(func_store, arguments, invoke_expr)
                ret.append(self.add_move_temp(invoke, invoke_expr))
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
            field_access = FieldAccess(fa, field, expr)
            if isinstance(context, SetContext):
                self.add_move_temp(field_access, expr)
                ret.append(field_access)
            else:
                ret.append(self.add_move_temp(field_access, expr))
            # we have to return a field access here, because only this can resolve set behavior correctly
        return ret

    def load_index(self, bases: StoreAbles, context: "ExpressionContext", expr: ast.expr) -> StoreAbles:
        from enre.analysis.analyze_expr import SetContext
        ret: List[StoreAble] = []
        for base in bases:
            index_access = IndexAccess(base, expr)
            if isinstance(context, SetContext):
                self.add_move_temp(index_access, expr)
                ret.append(index_access)
            else:
                ret.append(self.add_move_temp(index_access, expr))
        return ret

    def load_index_rvalues(self, bases: StoreAbles, expr: ast.expr) -> StoreAbles:
        ret: List[StoreAble] = []
        for base in bases:
            index_access = IndexAccess(base, expr)
            ret.append(self.add_move_temp(index_access, expr))
        return ret

    def load_index_lvalue(self, base: StoreAble, expr: ast.expr) -> IndexAccess:
        index_access = IndexAccess(base, expr)
        self.add_move_temp(index_access, expr)
        return index_access

    def add_return(self, return_stores: StoreAbles, expr: ast.expr) -> None:
        assert isinstance(self.mod, FunctionSummary)
        for return_store in return_stores:
            self.add_store_able(return_store)
            self._rules.append(Return(return_store, expr))

    def create_list(self, info: IndexableInfo, expr: ast.expr) -> StoreAble:
        temp = self.create_temp(expr)
        self.add_list(info, [temp], expr)
        return temp

    def add_list(self, info: IndexableInfo, lst_stores: StoreAbles, expr: ast.expr) -> None:
        for lst_store in lst_stores:
            self.add_store_able(lst_store)
            self._rules.append(AddList(info, lst_store, expr))

    def add_child(self, summary: ModuleSummary) -> None:
        self.mod.add_child(summary)


def get_named_store_able(current_module: Entity, ent: Entity, named_node: ast.expr) -> Optional[StoreAble]:
    ret: Optional[StoreAble] = None
    match ent:
        case Variable() as v:
            if v.get_scope() == current_module:
                ret = VariableLocal(v, named_node)
            else:
                ret = VariableOuter(v, v.get_scope())
        case Class() as cls:
            ret = ClassConst(cls)
        case Module() as mod:
            ret = ModuleConst(mod)
        case Parameter() as p:
            ret = ParameterLocal(p, named_node)
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
            ret = get_named_store_able(current_module, ma.module_ent, named_node)
        case PackageAlias() as pa:
            ret = get_named_store_able(current_module, pa.package_ent, named_node)
        case _ as e:
            raise NotImplementedError(f"{e} not implemented yet")
    return ret
