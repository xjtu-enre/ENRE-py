import ast
from typing import Optional, TYPE_CHECKING

from enre.analysis.analyze_expr import ExprAnalyzer, UseContext
from enre.analysis.analyze_stmt import AnalyzeContext
from enre.analysis.assign_target import assign_semantic, flatten_bindings
from enre.analysis.value_info import ConstructorType, ValueInfo
from enre.ent.EntKind import RefKind
from enre.ent.entity import UnknownVar, AbstractValue, NewlyCreated, Span, Alias, get_syntactic_span
from enre.ref.Ref import Ref

if TYPE_CHECKING:
    from enre.analysis.env import Bindings

DefaultAsHeadLen = 4


def abstract_capture(name: str, err_constructor: AbstractValue, ctx: "AnalyzeContext") -> None:
    frame_entities: AbstractValue = []
    new_bindings: "Bindings" = []
    new_var_ent = UnknownVar(name)
    newly_create = NewlyCreated(Span.get_nil(), new_var_ent)
    for ent, ent_type in err_constructor:
        if isinstance(ent_type, ConstructorType):
            assign_semantic(newly_create, ent_type.to_class_type(), new_bindings, ctx)
        else:
            assign_semantic(newly_create, ValueInfo.get_any(), new_bindings, ctx)
    new_bindings = flatten_bindings(new_bindings)
    ctx.env.get_scope().add_continuous(new_bindings)


def handler_except_alias(name: Optional[str], error_expr: ast.Expr, ctx: "AnalyzeContext") -> None:
    # TODO: Alias error_expr(Exception type) to name(Alias name)
    env = ctx.env
    use_avaler = ExprAnalyzer(ctx.manager, ctx.package_db, ctx.current_db, None, UseContext(),
                 env.get_scope().get_builder(), env)
    excep, excep_info = use_avaler.aval(error_expr.value)

    if name is not None and excep_info:
        as_name = name
        len_of_as_name = len(str(as_name))
        alias_span = get_syntactic_span(error_expr.value)

        alias_span.span_offset(DefaultAsHeadLen)
        alias_span.span_offset(len_of_as_name)

        location = env.get_scope().get_location().append(as_name, alias_span, None)
        alias_ent = Alias(location.to_longname(), location, [excep_info[0][0]])
        alias_ent.type = alias_ent.direct_type()
        ctx.current_db.add_ent(alias_ent)
        alias_binding = as_name, [(alias_ent, alias_ent.direct_type())]
        env.get_scope().add_continuous([alias_binding])

    if excep_info:
        except_ent = excep_info[0][0]
        current_ctx = env.get_ctx()
        current_ctx.add_ref(Ref(RefKind.Except, except_ent, ctx.coordinate[0], ctx.coordinate[1], False, None))
