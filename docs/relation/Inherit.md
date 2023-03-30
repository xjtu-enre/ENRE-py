## Relation: Inherit
Add class object to the attribute `__base__` indicates a inherit dependency.

### Supported Patterns
```yaml
name: Inherit
```

#### Semantic: 

##### Examples

###### Class Inherit
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
  items:
  - type: Inherit
    to: Class:'Base'
    from: Class:'Inherit'
    loc: '4:14'
  - type: Inherit
    to: Class:'Base'
    from: Class:'Inherit1'
    loc: '9:15'
  - type: Inherit
    to: Class:'Base2'
    from: Class:'Inherit1'
    loc: '9:21'
  - type: Inherit
    to: Class:'Base'
    from: Class:'LocalInherit'
    loc: '13:23'
  - type: Inherit
    to: Class:'Base'
    from: Class:'LocalInherit2'
    loc: '16:24'
  - type: Inherit
    to: Class:'Base2'
    from: Class:'LocalInherit2'
    loc: '16:30'
```
###### VariableInherit
```python
//// test_variable_inherit.py
def mixin(c, d):
    class Mixed(c, d):
        ...
```

```yaml
name: VariableInherit
relation:
  items:
  - type: Inherit
    to: Parameter:'c'
    from: Class:'Mixed'
    loc: '2:16'
  - type: Inherit
    to: Parameter:'d'
    from: Class:'Mixed'
    loc: '2:19'
```

###### FirstClassClassInherit
```python
//// test_first_order_class_inherit.py

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
  items:
  - type: Inherit
    to: Variable:'cls'
    loc: '14:15'
    from: Class:'SubClass'
  - type: Inherit
    to: Class:'Difficult'
    loc: '14:0'
    from: Class:'SubClass'
```
