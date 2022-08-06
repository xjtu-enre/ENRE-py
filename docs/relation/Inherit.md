## Relation: Inherit
Add class object to the attribute `__base__` indicates a inherit dependency.

### Supported Patterns
```yaml
name: Inherit
```

#### Semantic: 

##### Examples

- Class Inherit
```python

class Base:
    ...
class Inherit(Base):
    ...
class Base2:
    ...

class Inherit1(Base, Base2):
    ...

def func():
    class LocalInherit(Base):
        ...

    class LocalInherit2(Base, Base2):
        ...


```
```yaml
name: ClassInherit
relation:
  exact: false
  items:
  - type: Inherit
    to: test_inherit.Base
    from: test_inherit.Inherit
    loc: '4:14'
  - type: Inherit
    to: test_inherit.Base
    from: test_inherit.Inherit1
    loc: '9:15'
  - type: Inherit
    to: test_inherit.Base2
    from: test_inherit.Inherit1
    loc: '9:21'
  - type: Inherit
    to: test_inherit.Base
    from: test_inherit.func.LocalInherit
    loc: '13:23'
  - type: Inherit
    to: test_inherit.Base
    from: test_inherit.func.LocalInherit2
    loc: '16:24'
  - type: Inherit
    to: test_inherit.Base2
    from: test_inherit.func.LocalInherit2
    loc: '16:30'
```
- VariableInherit
```python
// test_variable_inherit.py
def mixin(c, d):
    class Mixed(c, d):
        ...
```

```yaml
name: VariableInherit
relation:
  exact: false
  items:
  - type: Inherit
    to: test_variable_inherit.Mixed.c
    from: test_variable_inherit.mixin.Mixed
    loc: '2:16'
  - type: Inherit
    to: test_variable_inherit.Mixed.d
    from: test_variable_inherit.mixin.Mixed
    loc: '2:19'
```

- FirstClassClassInherit
```python
// test_first_order_class_inherit.py

def create_class():


    class Difficult:
        ...


    return Difficult

cls = create_class()


class SubClass(cls):
    ...

```

```yaml
name: FirstClassClassInherit
relation:
  exact: false
  items:
  - type: Inherit
    to: test_first_order_class_inherit.cls
    loc: '14:15'
    from: test_first_order_class_inherit.SubClass
  - type: Inherit
    to: test_first_order_class_inherit.Difficult
    loc: '14:0'
    from: test_first_order_class_inherit.SubClass
```
