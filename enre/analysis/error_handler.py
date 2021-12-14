import ast
from typing import Optional, TYPE_CHECKING

from enre.ent.entity import UnknownVar, AbstractValue
from enre.analysis.assign_target import assign_semantic, flatten_bindings
from enre.analysis.analyze_expr import UseAvaler
from enre.analysis.analyze_stmt import InterpContext
from enre.analysis.enttype import ConstructorType, EntType

if TYPE_CHECKING:
    from enre.analysis.env import Bindings

def abstract_capture(name: str, err_constructor: AbstractValue, ctx: "InterpContext") -> None:
    frame_entities: AbstractValue = []
    new_bindings: "Bindings" = []
    new_var_ent = UnknownVar.get_unknown_var(name)
    for ent, ent_type in err_constructor:
        if isinstance(ent_type, ConstructorType):
            assign_semantic(new_var_ent, ent_type.to_class_type(), new_bindings, ctx)
        else:
            assign_semantic(new_var_ent, EntType.get_bot(), new_bindings, ctx)
    new_bindings = flatten_bindings(new_bindings)
    ctx.env.get_scope().add_continuous(new_bindings)


def handler_semantic(name: Optional[str], error_expr: ast.Expr, ctx: "InterpContext") -> None:
    use_avaler = UseAvaler(ctx.package_db, ctx.current_db)
    err_constructor = use_avaler.aval(error_expr.value, ctx.env)
    if name is not None:
        abstract_capture(name, err_constructor, ctx)
