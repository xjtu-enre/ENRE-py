import ast
from abc import ABC
from collections import defaultdict
from dataclasses import dataclass
from typing import List, Tuple, Callable, Optional, TYPE_CHECKING, Dict, Set, Iterable

from enre.analysis.value_info import ValueInfo
from enre.cfg.module_tree import StoreAbles, SummaryBuilder, get_named_store_able
from enre.ent.EntKind import RefKind
from enre.ent.entity import AbstractValue, MemberDistiller, Function
from enre.ent.entity import Entity, Variable, Parameter, UnknownVar, UnresolvedAttribute, ClassAttribute, Class, Span, \
    get_anonymous_ent, SetContextValue, NewlyCreated
from enre.ref.Ref import Ref

if TYPE_CHECKING:
    from enre.analysis.env import Bindings
    from enre.analysis.analyze_stmt import AnalyzeContext


class PatternBuilder:

    def visit(self, node: ast.expr) -> "Target":
        method = 'visit_' + node.__class__.__name__
        visitor: Callable[[ast.expr], "Target"] = getattr(self, method, self.visit_Lvalue)
        return visitor(node)

    def visit_Attribute(self, node: ast.Attribute) -> "LvalueTar":
        return LvalueTar(node)

    def visit_Lvalue(self, node: ast.expr) -> "LvalueTar":
        return LvalueTar(node)

    def visit_List(self, node: ast.List) -> "ListTar":
        tar_list: List[Target] = []
        for e in node.elts:
            tar_list.append(self.visit(e))
        return ListTar(tar_list)

    def visit_Tuple(self, node: ast.Tuple) -> "TupleTar":
        tar_list: List[Target] = []
        for e in node.elts:
            tar_list.append(self.visit(e))
        return TupleTar(tar_list)

    def visit_Starred(self, node: ast.Starred) -> "StarTar":
        return StarTar(self.visit(node.value))


class Target(ABC):
    ...


# `Tar` stands for target
@dataclass
class TupleTar(Target):
    tar_list: List[Target]


@dataclass
class LvalueTar(Target):
    lvalue_expr: ast.expr


@dataclass
class ListTar(Target):
    tar_list: List[Target]


@dataclass
class StarTar(Target):
    target: Target


def build_target(tar_expr: ast.expr) -> Target:
    return PatternBuilder().visit(tar_expr)


def dummy_unpack(_: AbstractValue) -> MemberDistiller:
    def wrapper(_: int) -> AbstractValue:
        return [(get_anonymous_ent(), ValueInfo.get_any())]

    return wrapper


def dummy_iter(_: AbstractValue) -> AbstractValue:
    # return [(get_anonymous_ent(), ValueInfo.get_any())]
    return _


def dummy_iter_store(iterables: StoreAbles, builder: SummaryBuilder, expr: ast.expr) -> StoreAbles:
    return builder.load_index_rvalues(iterables, expr)


def assign_semantic(target: Tuple[Entity, ValueInfo] | NewlyCreated,
                    value_type: ValueInfo,
                    new_bindings: List[Tuple[str, List[Tuple[Entity, ValueInfo]]]],
                    ctx: "AnalyzeContext") -> Entity:
    """
    Depends on which kind of the context entity is, define/set/use variable entity of the environment or
    the current.
    Add the new bindings names to the new_bindings, if it creates.
    :param tar_ent: the target entity by look up
    :param value_type: value information about the assigned target entity
    :param new_bindings: newly created bindings by this assignment
    :param ctx: analyze context
    """
    if isinstance(target, tuple):
        tar_ent, _ = target
        return assign_known_target(tar_ent, value_type, new_bindings, ctx)
    elif isinstance(target, NewlyCreated):
        return newly_define_semantic(target, value_type, new_bindings, ctx)


def newly_define_semantic(newly_created: NewlyCreated,
                          value_type: ValueInfo,
                          new_bindings: List[Tuple[str, List[Tuple[Entity, ValueInfo]]]],
                          ctx: "AnalyzeContext") -> Entity:
    location = ctx.env.get_scope().get_location()
    location = location.append(newly_created.unknown_ent.longname.name, newly_created.span, None)
    ctx_ent = ctx.env.get_ctx()
    target_lineno, target_col_offset = ctx.coordinate
    tar_ent = newly_created.unknown_ent
    if isinstance(tar_ent, UnknownVar):
        if isinstance(ctx_ent, Class) and not ctx.is_generator_expr:

            # ClassAttribute
            class_attr = ClassAttribute(ctx_ent, location.to_longname(), location)
            new_bindings.append((class_attr.longname.name, [(class_attr, class_attr.direct_type())]))
            class_attr.exported = False if class_attr.longname.name.startswith("__") else ctx_ent.exported

            ctx.current_db.add_ent(class_attr)
            ctx_ent.add_ref(Ref(RefKind.DefineKind, class_attr, target_lineno, target_col_offset, False, None))
            ctx_ent.add_ref(Ref(RefKind.SetKind, class_attr, target_lineno, target_col_offset, False, None))
            class_attr.add_ref(Ref(RefKind.ChildOfKind, ctx_ent, -1, -1, False, None))
            return class_attr
        else:
            # newly defined variable
            new_var = Variable(location.to_longname(), location)
            # add type to this newly variable
            new_var.add_type(value_type)

            exported = True if ctx.env.get_ctx().exported \
                               and not isinstance(ctx.env.get_ctx(), Function) else False
            new_var.exported = exported
            new_binding = (new_var.longname.name, [(new_var, new_var.type)])
            new_bindings.append(new_binding)
            ctx.current_db.add_ent(new_var)

            ctx.env.get_ctx().add_ref(Ref(RefKind.DefineKind, new_var, target_lineno, target_col_offset, False, None))
            ctx.env.get_ctx().add_ref(Ref(RefKind.SetKind, new_var, target_lineno, target_col_offset, False, None))

            ctx.env.get_scope()

            # record the target assign to target entity
            # do nothing if target is not a variable, record the possible Set relation in add_ref method of DepDB
            return new_var
    elif isinstance(tar_ent, UnresolvedAttribute):
        # unreachable
        ...


def assign_known_target(tar_ent: Entity,
                        value_type: ValueInfo,
                        new_bindings: List[Tuple[str, List[Tuple[Entity, ValueInfo]]]],
                        ctx: "AnalyzeContext") -> Entity:
    target_lineno, target_col_offset = ctx.coordinate

    if isinstance(tar_ent, Variable) or isinstance(tar_ent, Parameter):

        # Union type to this known variable
        tar_ent.add_type(value_type)
        # new_bindings.append((tar_ent.longname.name, [(tar_ent, tar_ent.type)]))
        ctx.env.get_scope().reset_binding_value(tar_ent.longname.name, tar_ent.type)
        ctx.env.get_ctx().add_ref(Ref(RefKind.SetKind, tar_ent, target_lineno, target_col_offset, False, None))
    elif isinstance(tar_ent, Function):
        tar_ent.add_type(value_type)
        new_bindings.append((tar_ent.longname.name, [(tar_ent, tar_ent.type)]))

        ctx.env.get_ctx().add_ref(Ref(RefKind.SetKind, tar_ent, target_lineno, target_col_offset, False, None))
    elif isinstance(tar_ent, UnresolvedAttribute):
        ...
    else:
        ctx.env.get_ctx().add_ref(Ref(RefKind.SetKind, tar_ent, target_lineno, target_col_offset, False, None))
    return tar_ent


def compress_abstract_value(entities: AbstractValue) -> AbstractValue:
    new_entities_dict: Dict[Entity, Set[ValueInfo]] = defaultdict(set)
    for ent, ent_type in entities:
        if isinstance(ent_type, list):
            ent_type = ValueInfo.get_any()
        new_entities_dict[ent].add(ent_type)
    new_entities: AbstractValue = []
    for ent, ent_types in new_entities_dict.items():
        for ent_type in ent_types:
            new_entities.append((ent, ent_type))
    return new_entities


def flatten_bindings(bindings: "Bindings") -> "Bindings":
    binding_dict: Dict[str, AbstractValue] = defaultdict(list)
    for name, abstract_val in bindings:
        binding_dict[name].extend(abstract_val)
    new_bindings: "Bindings" = list(binding_dict.items())
    for i in range(0, len(new_bindings)):
        new_bindings[i] = new_bindings[i][0], compress_abstract_value(new_bindings[i][1])
    return new_bindings


def abstract_assign(lvalue: SetContextValue, rvalue: AbstractValue, assigned_expr: ast.expr,
                    r_store_ables: StoreAbles,
                    builder: SummaryBuilder,
                    ctx: "AnalyzeContext") -> (StoreAbles, List[AbstractValue]):
    new_bindings: "Bindings" = []
    ents: "AbstractValue" = []
    for _, value_type in rvalue:
        for target in lvalue:
            ent = assign_semantic(target, value_type, new_bindings, ctx)
            ents.append((ent, ent.direct_type()))
    new_bindings = flatten_bindings(new_bindings)
    lhs_store_ables = []
    for n, target_ents in new_bindings:
        for tar, _ in target_ents:
            lhs_store_able = get_named_store_able(tar, assigned_expr)
            if lhs_store_able:
                lhs_store_ables.append(lhs_store_able)
    ctx.env.get_scope().add_continuous(new_bindings)
    return lhs_store_ables, ents


def unpack_semantic(target: ast.expr, rvalue: AbstractValue, r_store_ables: StoreAbles, builder: SummaryBuilder,
                    ctx: "AnalyzeContext") -> Iterable[Entity]:
    from enre.analysis.analyze_expr import ExprAnalyzer, SetContext
    set_avaler = ExprAnalyzer(ctx.manager, ctx.package_db, ctx.current_db, None,
                              SetContext(False, rvalue, r_store_ables), builder, ctx.env)
    # replace pattern match to use mypy
    # match target:
    #     case LvalueTar(lvalue_expr):
    #         lvalue: AbstractValue = set_avaler.aval(lvalue_expr, ctx.env)
    #         abstract_assign(lvalue, rvalue, ctx)
    #     case TupleTar(tar_list):
    #         unpack_list(tar_list, distiller, ctx)
    #     case ListTar(tar_list):
    #         unpack_list(tar_list, distiller, ctx)
    #     case StarTar(tar):
    #         unpack_list([tar], distiller, ctx)
    temp_map = set_avaler.aval(target)[1]
    # for var in temp_map:
    #     if isinstance(var, tuple):
    #         var = var[0] if isinstance(var[0], Variable) else var[1]
    #     if isinstance(var, Variable):
    #         for value_info in rvalue:
    #             var.add_type(value_info[1])
    return map(lambda v: v[0], temp_map)


def assign2target(target: ast.expr, rvalue_expr: Optional[ast.expr], builder: SummaryBuilder,
                  ctx: "AnalyzeContext") -> Iterable[Entity]:
    from enre.analysis.analyze_expr import ExprAnalyzer, UseContext
    rvalue: AbstractValue
    r_store_ables: StoreAbles
    if rvalue_expr is None:
        rvalue = [(get_anonymous_ent(), ValueInfo.get_any())]
        r_store_ables = []
    else:
        avaler = ExprAnalyzer(ctx.manager, ctx.package_db, ctx.current_db, None, UseContext(), builder, ctx.env)
        r_store_ables, rvalue = avaler.aval(rvalue_expr)
    return unpack_semantic(target, rvalue, r_store_ables, builder, ctx)


if __name__ == '__main__':
    tree = ast.parse("*[(x, y), y]")
    tar = build_target(tree.body[0].value)  # type: ignore
    print(tar)
