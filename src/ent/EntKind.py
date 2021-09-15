from enum import Enum


class RefKind(Enum):
    SetKind = "Set"
    UseKind = "Use"
    CallKind = "Call"
    DefineKind = "Define"
    InheritKind = "Inherit"
    ImportKind = "Import"


class EntKind(Enum):
    Package = "Package"
    Module = "Module"
    ModuleAlias = "Module Alias"
    Alias = "Alias"
    Function = "Function"
    Variable = "Variable"
    Class = "Class"
    Parameter = "Parameter"
    UnknownVar = "Unknown Variable"
    UnknownModule = "Unknown Module"
    ClassAttr = "Class Attribute"
    UnresolvedAttr = "Unresolved Attribute"
    ReferencedAttr = "Referenced Attribute"

    Anonymous = "Anonymous"

# KindSet is a kind for `Set` relation
# like
#
# def fun():
#     a = b
#
# Then fun set `Variable`(Entity) a
