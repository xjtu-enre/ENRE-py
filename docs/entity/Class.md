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
  type: Class
  extra: false
  items:
  - type: Class
    qualified: test_global_class.Base
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
  type: Class
  extra: false
  items:
  - type: Class
    qualified: test_inherit_global_class.Base
    name: Base
    loc: '2:6'
  - type: Class
    qualified: test_inherit_global_class.Inherit
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
  type: Class
  extra: false
  items:
  - type: Class
    qualified: test_nested_class.Out
    name: Out
    loc: '1:6'
  - type: Class
    qualified: test_nested_class.Out.Inner1
    name: Inner1
    loc: '2:10'
  - type: Class
    qualified: test_nested_class.out_func.Inner2
    name: Inner2
    loc: '7:10'
  - type: Class
    qualified: test_nested_class.out_func.Inner2.Inner3
    name: Inner3
    loc: '8:14'
```

###### Abstract Class Definition

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
name: AbstractClassDefinition
entity:
  type: Class
  extra: false
  items:
    - type: Class
      qualified: test_abstract_class.A
      name: A
      loc: '4:6'
      abstract: true
    - type: Class
      qualified: test_abstract_class.B
      name: B
      loc: '8:6'
      abstract: true
    - type: Class
      qualified: test_abstract_class.B.Inner
      name: Inner
      loc: '9:10'
      abstract: true
```

### Properties

| Name | Description | Type | Default |
|---|---|:---:|:---:|
| isAbstract | Indicates whether the class or function is abstract. | `boolean` | `false` |