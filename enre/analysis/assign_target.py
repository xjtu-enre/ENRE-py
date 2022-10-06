import ast
from abc import ABC
from collections import defaultdict
from dataclasses import dataclass
from typing import List, Tuple, Callable, Optional, TYPE_CHECKING, Dict, Set, Iterable

from enre.analysis.value_info import ValueInfo, InstanceType
from enre.cfg.module_tree import StoreAbles, SummaryBuilder, get_named_store_able
from enre.ent.EntKind import RefKind
from enre.ent.entity import AbstractValue, MemberDistiller
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
    return [(get_anonymous_ent(), ValueInfo.get_any())]


def dummy_iter_store(iterables: StoreAbles, builder: SummaryBuilder, expr: ast.expr) -> StoreAbles:
    return builder.load_index_rvalues(iterables, expr)


def assign_semantic(target: Tuple[Entity, ValueInfo] | NewlyCreated,
                    value_type: ValueInfo,
                    new_bindings: List[Tuple[str, List[Tuple[Entity, ValueInfo]]]],
                    ctx: "AnalyzeContext") -> None:
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
        assign_known_target(tar_ent, value_type, new_bindings, ctx)
    elif isinstance(target, NewlyCreated):
        newly_define_semantic(target, value_type, new_bindings, ctx)


def newly_define_semantic(newly_created: NewlyCreated,
                          value_type: ValueInfo,
                          new_bindings: List[Tuple[str, List[Tuple[Entity, ValueInfo]]]],
                          ctx: "AnalyzeContext") -> None:
    location = ctx.env.get_scope().get_location()
    location = location.append(newly_created.unknown_ent.longname.name, newly_created.span, None)
    ctx_ent = ctx.env.get_ctx()
    target_lineno, target_col_offset = ctx.coordinate
    tar_ent = newly_created.unknown_ent
    if isinstance(tar_ent, UnknownVar):
        if isinstance(ctx_ent, Class) and not ctx.is_generator_expr:
            new_attr = ClassAttribute(ctx_ent, location.to_longname(), location)
            new_bindings.append((new_attr.longname.name, [(new_attr, value_type)]))
            ctx.current_db.add_ent(new_attr)
            ctx_ent.add_ref(Ref(RefKind.DefineKind, new_attr, target_lineno, target_col_offset, False, None))
            ctx_ent.add_ref(Ref(RefKind.SetKind, new_attr, target_lineno, target_col_offset, False, None))
        else:
            # newly defined variable
            new_var = Variable(ctx.env.get_ctx(), location.to_longname(), location)
            new_bindings.append((new_var.longname.name, [(new_var, value_type)]))
            ctx.current_db.add_ent(new_var)
            ctx.env.get_ctx().add_ref(Ref(RefKind.DefineKind, new_var, target_lineno, target_col_offset, False, None))
            ctx.env.get_ctx().add_ref(Ref(RefKind.SetKind, new_var, target_lineno, target_col_offset, False, None))
            # record the target assign to target entity
            # do nothing if target is not a variable, record the possible Set relation in add_ref method of DepDB
    elif isinstance(tar_ent, UnresolvedAttribute):
        if isinstance(tar_ent.receiver_type, InstanceType):
            receiver_class = tar_ent.receiver_type.class_ent
            new_location = receiver_class.location.append(tar_ent.longname.name, Span.get_nil(), location.file_path)
            new_attr = ClassAttribute(receiver_class, new_location.to_longname(), new_location)
            ctx.current_db.add_ent(new_attr)
            receiver_class.add_ref(
                Ref(RefKind.DefineKind, new_attr, target_lineno, target_col_offset, False, None))
            ctx.env.get_ctx().add_ref(Ref(RefKind.SetKind, new_attr, target_lineno, target_col_offset, False, None))


def assign_known_target(tar_ent: Entity,
                        value_type: ValueInfo,
                        new_bindings: List[Tuple[str, List[Tuple[Entity, ValueInfo]]]],
                        ctx: "AnalyzeContext") -> None:
    target_lineno, target_col_offset = ctx.coordinate
    # target should be the entity which the target_expr could possibl   y eval to
    if isinstance(tar_ent, Variable) or isinstance(tar_ent, Parameter):
        # if target entity is a defined variable or parameter, just add the target new type to the environment
        # env.add(target, value_type)
        new_bindings.append((tar_ent.longname.name, [(tar_ent, value_type)]))
        # add_target_var(target, value_type, env, self.dep_db)
        # self.dep_db.add_ref(env.get_ctx(), Ref(RefKind.DefineKind, target, target_expr.lineno, target_expr.col_offset))
        ctx.env.get_ctx().add_ref(Ref(RefKind.SetKind, tar_ent, target_lineno, target_col_offset, False, None))
        # record the target assign to target entity
    elif isinstance(tar_ent, UnresolvedAttribute):
        assert False
        if isinstance(tar_ent.receiver_type, InstanceType):
            receiver_class = tar_ent.receiver_type.class_ent
            new_location = receiver_class.location.append(tar_ent.longname.name, Span.get_nil())
            new_attr = ClassAttribute(new_location.to_longname(), new_location)
            ctx.current_db.add_ent(new_attr)
            receiver_class.add_ref(
                Ref(RefKind.DefineKind, new_attr, target_lineno, target_col_offset))
            ctx.env.get_ctx().add_ref(Ref(RefKind.SetKind, new_attr, target_lineno, target_col_offset))
    else:
        ctx.env.get_ctx().add_ref(Ref(RefKind.SetKind, tar_ent, target_lineno, target_col_offset, False, None))


def compress_abstract_value(entities: AbstractValue) -> AbstractValue:
    new_entities_dict: Dict[Entity, Set[ValueInfo]] = defaultdict(set)
    for ent, ent_type in entities:
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
                    ctx: "AnalyzeContext") -> StoreAbles:
    new_bindings: "Bindings" = []
    for _, value_type in rvalue:
        for target in lvalue:
            assign_semantic(target, value_type, new_bindings, ctx)
    new_bindings = flatten_bindings(new_bindings)
    ctx.env.get_scope().add_continuous(new_bindings)

    lhs_store_ables = []
    for n, target_ents in new_bindings:
        for tar, _ in target_ents:
            lhs_store_able = get_named_store_able(ctx.env.get_ctx(), tar, assigned_expr)
            if lhs_store_able:
                lhs_store_ables.append(lhs_store_able)
    return lhs_store_ables


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

    return map(lambda v: v[0], set_avaler.aval(target)[1])


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
