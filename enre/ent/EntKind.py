from enum import Enum


class RefKind(Enum):
    SetKind = "Set"
    UseKind = "Use"
    CallKind = "Call"
    ContainKind = "Contain"
    DefineKind = "Define"
    InheritKind = "Inherit"
    ImportKind = "Import"
    AliasTo = "Alias"
    Annotate = "Annotate"
    Except = "Except"
    Raise = "Raise"
    PossibleKind = "Possible"
    ChildOfKind = "ChildOf"
    OverloadKind = "Overload"
    OverrideKind = "Override"


class EntKind(Enum):
    Package = "Package"
    Module = "Module"
    ModuleAlias = "ModuleAlias"
    Alias = "Alias"
    Function = "Function"
    Method = "Method"
    AnonymousFunction = "AnonymousFunction"
    LambdaParameter = "LambdaParameter"
    Variable = "Variable"
    Class = "Class"
    Parameter = "Parameter"
    UnknownVar = "UnknownVar"
    UnknownModule = "UnknownModule"
    ClassAttribute = "ClassAttribute"
    Attribute = "Attribute"
    UnresolvedAttr = "UnresolvedAttribute"
    ReferencedAttr = "ReferencedAttribute"
    Anonymous = "Anonymous"
    Subscript = "Subscript"


# KindSet is a kind for `Set` relation
# like
#
# def fun():
#     a = b
#
# Then fun set `Variable`(Entity) a
