# ENRE-python

ENRE-python is an entity relationship extractor for python.

## Entity Categories

### Python

| Entity Name                  | Definition                                                                                                                                               |
|------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------|
| [Package](entity/package.md) | A package is a collection of modules or sub-packages. There are two types of packages in Python: regular package and namespace package. A regular package requires an __init__.py file, while a namespace package doesn't. |
| [Module](entity/Module.md) | A object that serves as an organizational unit of Python code. Modules have a namespace containing arbitrary Python objects. Definition within a module can be imported by import statement.|
| [Variable](entity/Variable.md)   | A `Variable Entity` is a reserved memory location for storing data values.|
| [Function](entity/Function.md)   | A `Function Entity` in python is a a wrapper around executable code.|
| [Parameter](entity/parameter.md) | A `Parameter Entity` is a variable defined either as function's formal parameter or in a `catch` clause. |
| [Class](entity/class.md)| A `Class` is a template of object containing properties and methods defined by keyword `class`.                           |
| [Attribute](entity/Attribute.md) |An `Attribute` is a field of class object or a field of class instance which can be infered from the class definition. |
| [Alias](entity/Alias.md) | An `Alias` created by import statement with `as`. |
| [AnonymousFunction](entity/AnonymousFunction.md)   | In python, an anonnymous function can be created by lambda expression.|

## Relation Categories

### Python

| Relation Name                      | Definition |
|-|-|
| [Define](relation/Define.md)           | A entity A define another entity B when B is created in A's namespace. |
| [Use](relation/Use.md) | A Use dependency indicates some object was referenced.  |
|[Set](relation/Set.md) |  A Set dependency indicates some object's binding in a namespace was overwritten.|
| [Import](relation/Import.md)     | A Import dependency indicates a python module was imported, locally or globally.|
| [Call](relation/Call.md)         | Calling a callable object indicates a call dependency. |
| [Inherit](relation/Inherit.md)| Add class object to the attribute __base__ indicates a inherit dependency.|
| [Contain](relation/Contain.md)| A package contains modules and sub-packages.|
| [Annotate](relation/Annotate.md)| An entity x annotate with entity y, when y used for type annotating entity x.|
| [Alias](relation/Alias.md)| An `Alias` relation created by import statement with `as`. |
