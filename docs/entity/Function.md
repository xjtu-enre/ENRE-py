## Entity: Function
A Function entity in python is a a wrapper around  executable code.

### Supported Patterns

```yaml
name: FunctionDefinition
```

#### Syntax: FunctionDefinition
```text
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

##### Examples
###### Global Function Definition

```python
//// test_global_function.py
def func1():
    return 0
```

```yaml
name: GlobalFunctionDefinition
entity:
  type: Function
  extra: false
  items:
  - type: Function
    qualified: test_global_function.func1
    name: func1
    loc: '1:4'
```
###### Class Method Definition
```python
//// test_method_definition.py
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
  type: Function
  extra: False
  items:
  - type: Function
    qualified: test_method_definition.ClassA.method
    name: method
    loc: '2:8'
  - type: Function
    qualified: test_method_definition.ClassB.method
    name: method
    loc: '6:8'
  - type: Function
    qualified: test_method_definition.InheritClassA.method
    name: method
    loc: '10:8'
```

###### Nested Function Definition
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
  type: Function
  extra: false
  items:
  - type: Function
    qualified: test_nested_function.func
    name: func
    loc: '1:4'
  - type: Function
    qualified: test_nested_function.func.inner
    name: inner
    loc: '2:8'
  - type: Function
    qualified: test_nested_function.func.inner.inner_inner
    name: inner_inner
    loc: '4:12'
```

###### Abstract Function Definition
```python
//// test_abstract_function.py
from abc import ABC, abstractmethod


class Foo(ABC):
    @abstractmethod
    def foo1(self):
        pass

    @abstractmethod
    def foo2(self):
        pass

    def foo3(self):
        ...

```
```yaml
name: AbstractFunctionDefinition
entity:
  type: Function
  extra: false
  items:
  - type: Function
    qualified: test_abstract_function.foo1
    name: foo1
    loc: '6:8'
    abstract: true
  - type: Function
    qualified: test_abstract_function.foo2
    name: foo2
    loc: '10:8'
    abstract: true
  - type: Function
    qualified: test_abstract_function.foo3
    name: foo3
    loc: '13:8'
```

### Properties

| Name | Description | Type | Default |
|---|---|:---:|:---:|
| isAbstract | Indicates whether the class or function is abstract. | `boolean` | `false` |