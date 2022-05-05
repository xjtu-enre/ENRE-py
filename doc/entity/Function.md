# Entity: Function
A Function entity in python is a a wrapper around  executable code.

## Syntax: FunctionDefinition
```
funcdef                   : [decorators] "def" funcname "(" [parameter_list] ")"
                            ["->" expression] ":" suite
decorators                : decorator+
decorator                 : "@" assignment_expression NEWLINE
parameter_list            : defparameter ("," defparameter)* "," "/" ["," [parameter_list_no_posonly]]
                              | parameter_list_no_posonly
parameter_list_no_posonly : defparameter ("," defparameter)* ["," [parameter_list_starargs]]
                            | parameter_list_starargs
parameter_list_starargs   : "*" [parameter] ("," defparameter)* ["," ["**" parameter [","]]]
                            | "**" parameter [","]
parameter                 : identifier [":" expression]
defparameter              : parameter ["=" expression]
funcname                  : identifier
```

### Examples
- Global Function Definition

```python
// test_global_function.py
def func1():
    return 0
```

```yaml
name: GlobalFunctionDefinition
entity:
  exact: false
  items:
  - category: Function
    longname: test_global_function.func1
    name: func1
  - category: Parameter
    longname: test_global_function.func1.x
    name: x
```
- Class Method Definition
```python
// test_method_definition.py
class ClassA:
    def method(self):
        ...

class ClassB:
    def method(self):
        ...

class InheritClassA(ClassA):
    def method(self):
        ...
```
```yaml
name: ClassMethodDefinition
entity:
  exact: false
  items:
  - category: Class
    longname: test_method_definition.ClassA
    name: ClassA
  - category: Function
    longname: test_method_definition.ClassA.method
    name: method
  - category: Class
    longname: test_method_definition.ClassB
    name: ClassB
  - category: Function
    longname: test_method_definition.ClassB.method
    name: method
  - category: Class
    longname: test_method_definition.ClassB
    name: ClassB
  - category: Function
    longname: test_method_definition.InheritClassA.method
    name: method
```

- Nested Function Definition
```python
def func():
    def inner():

        def inner_inner():
            func()

        func()
        inner_inner()

    inner()

```

```yaml
name: NestedFunctionDefinition
entity:
  exact: false
  items:
  - category: Function
    longname: test_nested_function.func
    name: func
  - category: Function
    longname: test_nested_function.func.inner
    name: inner
  - category: Function
    longname: test_nested_function.func.inner_inner
    name: inner_inner
name: TBA
```