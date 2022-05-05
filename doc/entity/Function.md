# Entity: Function
A Function entity in python is a a wrapper around  executable code.

## Supported pattern

```yaml
name: FunctionDefinition
```

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
    r:
        d: . 
        e: .
        s: .
        u: .
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
    r:
        d: Type 
        e: .
        s: .
        u: .
  - category: Function
    longname: test_method_definition.ClassA.method
    name: method
    r:
        d: . 
        e: .
        s: .
        u: .
  - category: Class
    longname: test_method_definition.ClassB
    name: ClassB
    r:
        d: Type 
        e: .
        s: .
        u: .
  - category: Function
    longname: test_method_definition.ClassB.method
    name: method
    r:
        d: . 
        e: .
        s: .
        u: .
  - category: Class
    longname: test_method_definition.InheritClassA
    name: InheritClassA
    r:
        d: Type 
        e: .
        s: .
        u: .
  - category: Function
    longname: test_method_definition.InheritClassA.method
    name: method
    r:
        d: . 
        e: .
        s: .
        u: .
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
    r:
        d: . 
        e: .
        s: .
        u: .
  - category: Function
    longname: test_nested_function.func.inner
    name: inner
    r:
        d: . 
        e: .
        s: .
        u: .
  - category: Function
    longname: test_nested_function.func.inner.inner_inner
    name: inner_inner
    r:
        d: .  
        e: .
        s: .
        u: .
```