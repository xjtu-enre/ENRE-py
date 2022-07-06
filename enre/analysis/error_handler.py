import ast
from typing import Optional, TYPE_CHECKING

from enre.analysis.analyze_expr import ExprAnalyzer
from enre.analysis.analyze_stmt import AnalyzeContext
from enre.analysis.assign_target import assign_semantic, flatten_bindings
from enre.analysis.value_info import ConstructorType, ValueInfo
from enre.ent.entity import UnknownVar, AbstractValue, NewlyCreated, Span

if TYPE_CHECKING:
    from enre.analysis.env import Bindings

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


def handler_semantic(name: Optional[str], error_expr: ast.Expr, ctx: "AnalyzeContext") -> None:
    return
    use_avaler = ExprAnalyzer(ctx.manager, ctx.package_db, ctx.current_db)
    err_constructor = use_avaler.aval(error_expr.value, ctx.env)
    if name is not None:
        abstract_capture(name, err_constructor, ctx)
