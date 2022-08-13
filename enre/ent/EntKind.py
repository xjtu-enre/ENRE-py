from enum import Enum


class RefKind(Enum):
    SetKind = "Set"
    UseKind = "Use"
    CallKind = "Call"
    ContainKind = "Contain"
    DefineKind = "Define"
    InheritKind = "Inherit"
    ImportKind = "Import"
    HasambiguousKind = "Hasambiguous"
    AliasTo = "Alias"
    Annotate = "Annotate"


class EntKind(Enum):
    Package = "Package"
    Module = "Module"
    ModuleAlias = "Module Alias"
    Alias = "Alias"
    Function = "Function"
    AnonymousFunction = "AnonymousFunction"
    LambdaParameter = "LambdaParameter"
    Variable = "Variable"
    Class = "Class"
    Parameter = "Parameter"
    UnknownVar = "Unknown Variable"
    UnknownModule = "Unknown Module"
    ClassAttr = "Attribute"
    UnresolvedAttr = "Unresolved Attribute"
    ReferencedAttr = "Referenced Attribute"
    AmbiguousAttr = "Ambiguous Attribute"
    Anonymous = "Anonymous"

# KindSet is a kind for `Set` relation
# like
#
# def fun():
#     a = b
#
# Then fun set `Variable`(Entity) a
