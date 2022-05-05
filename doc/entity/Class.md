# Entity: Class
Classes provide a means of bundling data and functionality together. Creating a new class creates a new type of object, allowing new instances of that type to be made.

## Supported pattern
```yaml
name: ClassDefinition
```
### Syntax: ClassDefinition

```
classdef    :  [decorators] "class" classname [inheritance] ":" suite
inheritance :  "(" [argument_list] ")"
classname   :  identifier
```

### Examples
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
  - category: Class
    longname: test_global_class.Base
    name: Base
    r:
        d:Type
        e:.
        s:.
        u:
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
  - category: Class
    longname: test_inherit_global_class.Base
    name: Base
    r:
        d:Type
        e:.
        s:.
        u:
  - category: Class
    longname: test_inherit_global_class.Inherit
    name: Inherit
    r:
        d:Type 
        e:.
        s:.
        u:
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
  - category: Class
    longname: test_nested_class.Out
    name: Out
    r:
        d:Type  
        e:.
        s:.
        u:
  - category: Class
    longname: test_nested_class.Out.Inner1
    name: Inner1
    r:
        d:Type  
        e:.
        s:.
        u:
  - category: Function
    longname: test_nested_class.out_func
    name: out_func
    r:
        d:. 
        e:.
        s:.
        u:
  - category: Class
    longname: test_nested_class.out_func.Inner2
    name: Inner2
    r:
        d:Type 
        e:.
        s:.
        u:
  - category: Class
    longname: test_nested_class.out_func.Inner2.Inner3
    name: Inner3
    r:
        d:Type 
        e:.
        s:.
        u:
```