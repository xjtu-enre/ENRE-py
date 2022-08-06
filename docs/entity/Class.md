## Entity: Class
Classes provide a means of bundling data and functionality together. Creating a new class creates a new type of object, allowing new instances of that type to be made.

### Supported Patterns
```yaml
name: ClassDefinition
```
#### Syntax: ClassDefinition

```text
classdef    :  [decorators] "class" classname [inheritance] ":" suite
inheritance :  "(" [argument_list] ")"
classname   :  identifier
```

##### Examples
- Global Class Definition

```python
// test_global_class.py
class Base:
    ...
```

```yaml
name: GlobalClassDefinition
entity:
  exact: false
  items:
  - type: Class
    longname: test_global_class.Base
    name: Base
    loc: '1:6'
```

- Inherit Global Class Definition

```python

class Base:
    ...


class Inherit(Base):
    ...

```
```yaml
name: InheritGlobalClassDefinition
entity:
  exact: false
  items:
  - type: Class
    longname: test_inherit_global_class.Base
    name: Base
    loc: '2:6'
  - type: Class
    longname: test_inherit_global_class.Inherit
    name: Inherit
    loc: '6:6'
```

- Nested Class Definition 
```python
class Out:
    class Inner1:
        ...
    ...

def out_func():
    class Inner2:
        class Inner3:
            ...
        ...
    ...
```

```yaml
name: NestedClassDefinition
entity:
  exact: false
  items:
  - type: Class
    longname: test_nested_class.Out
    name: Out
    loc: '1:6'
  - type: Class
    longname: test_nested_class.Out.Inner1
    name: Inner1
    loc: '2:10'
  - type: Function
    longname: test_nested_class.out_func
    name: out_func
    loc: '5:14'
  - type: Class
    longname: test_nested_class.out_func.Inner2
    name: Inner2
    loc: '6:10'
  - type: Class
    longname: test_nested_class.out_func.Inner2.Inner3
    name: Inner3
    loc: '7:14'
```

- Abstract Class Defination

```python
// test_abstract_class.py
class A(ABC):
    ...


class B:
    class Inner:
        def __init__(self):
            if self.__class__.__name__ == "inner":
                raise NotImplementedError("You can't instantiate this abstract class. Derive it, please.")

        def __new__(self):
            if self.__class__.__name__ == "inner":
                raise NotImplementedError("You can't instantiate this abstract class. Derive it, please.")

        def func1(self):
            raise NotImplementedError("You can't instantiate this abstract class. Derive it, please.")

        def func2(self):
            a = 1
            raise NotImplementedError("You can't instantiate this abstract class. Derive it, please.")

    @abstractmethod
    def func3(self):
        ...
```

```yaml
name: AbstractClassDefination
entity:
  exact: false
  items:
    - type: Class
      longname: test_abstract_class.A
      name: A
      loc: '1:6'
      abstract_class: True
      abstract_method_list: None
    - type: Class
      longname: test_abstract_class.B
      name: B
      loc: '5:6'
      abstract_class: True
      abstract_method_list: func3
    - type: Class
      longname: test_abstract_class.B.Inner
      name: Inner
      loc: '6:10'
      abstract_class: True
      abstract_method_list: __init__, __new__, func1
    - type: Function
      longname: test_abstract_class.B.Inner.__init__
      name: __init__
      loc: '7:12'
      method_kind: Abstract Constructor
    - type: Function
      longname: test_abstract_class.B.Inner.__new__
      name: __new__
      loc: '11:12'
      method_kind: Abstract Constructor
    - type: Function
      longname: test_abstract_class.B.Inner.func1
      name: func1
      loc: '14:12'
      method_kind: Abstract Method
    - type: Function
      longname: test_abstract_class.B.Inner.func2
      name: func2
      loc: '17:12'
      method_kind: None
    - type: Function
      longname: test_abstract_class.B.func3
      name: func3
      loc: '22:8'
      method_kind: Abstract Method
```