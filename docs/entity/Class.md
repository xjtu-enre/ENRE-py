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
###### Global Class Definition

```python
//// test_global_class.py
class Base:
    ...
```

```yaml
name: GlobalClassDefinition
entity:
  extra: false
  items:
  - type: Class
    longname: test_global_class.Base
    name: Base
    loc: '1:6'
```

###### Inherit Global Class Definition

```python

class Base:
    ...


class Inherit(Base):
    ...

```
```yaml
name: InheritGlobalClassDefinition
entity:
  extra: false
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

###### Nested Class Definition 
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
  extra: false
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

###### Abstract Class Defination

```python
//// test_abstract_class.py
from abc import abstractmethod, ABCMeta, ABC


class A(ABC):
    ...


class B:
    class Inner:
        __metaclass__ = ABCMeta

        @abstractmethod
        def __init__(self):
            if self.__class__.__name__ == "Inner":
                raise NotImplementedError("You can't instantiate this abstract class. Derive it, please.")

        @abstractmethod
        def __new__(cls):
            if cls.__class__.__name__ == "Inner":
                raise NotImplementedError("You can't instantiate this abstract class. Derive it, please.")

        @abstractmethod
        def func1(self):
            pass

        def func2(self):
            ...

    @abstractmethod
    def func3(self):
        ...

```

```yaml
name: AbstractClassDefination
entity:
  extra: false
  items:
    - type: Class
      longname: test_abstract_class.A
      name: A
      loc: '4:6'
      abstract: true
    - type: Class
      longname: test_abstract_class.B
      name: B
      loc: '8:6'
      abstract: true
    - type: Class
      longname: test_abstract_class.B.Inner
      name: Inner
      loc: '9:10'
      abstract: true
    - type: Function
      longname: test_abstract_class.B.Inner.__init__
      name: __init__
      loc: '13:12'
      abstract: true
    - type: Function
      longname: test_abstract_class.B.Inner.__new__
      name: __new__
      loc: '18:12'
      abstract: true
    - type: Function
      longname: test_abstract_class.B.Inner.func1
      name: func1
      loc: '23:12'
      abstract: true
    - type: Function
      longname: test_abstract_class.B.Inner.func2
      name: func2
      loc: '26:12'
    - type: Function
      longname: test_abstract_class.B.func3
      name: func3
      loc: '30:8'
      abstract: true
```

### Properties

| Name | Description | Type | Default |
|---|---|:---:|:---:|
| isAbstract | Indicates whether the class or function is abstract. | `boolean` | `false` |