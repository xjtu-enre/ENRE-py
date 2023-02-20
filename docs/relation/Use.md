## Relation: Use

A Use dependency indicates some object was referenced.

### Supported Patterns
```yaml
name: Use
```

#### Semantic: 

##### Examples
###### Use Module Level Definition
```python
//// test_module_level_use.py
class Base:
    ...

class Inherit(Base):
    ...

def func1():
    print(Base)
    return 0
x = []

y: int = 1

t1, t2 = 1, 2

(t3 := 1)
for a, b in x:
    print(a)
    print(b)

print(Base)
print(Inherit)
print(func1)
print(x)
print(y)

print(t1)

print(t2)

print(t3)
```

```yaml
name: UseModuleLevelDefinition
relation:
  items:
  - type: Define
    to: Class:'test_module_level_use.Base'
    from: Module:'test_module_level_use'
    loc: '1:6'
  - type: Define
    to: Class:'test_module_level_use.Inherit'
    from: Module:'test_module_level_use'
    loc: '4:6'
  - type: Define
    to: Function:'test_module_level_use.func1'
    from: Module:'test_module_level_use'
    loc: '7:4'
  - type: Use
    to: Class:'test_module_level_use.Base'
    from: Function:'test_module_level_use.func1'
    loc: '8:10'
  - type: Define
    to: Variable:'test_module_level_use.x'
    from: Module:'test_module_level_use'
    loc: '10:0'
  - type: Define
    to: Variable:'test_module_level_use.y'
    from: Module:'test_module_level_use'
    loc: '12:0'
  - type: Define
    to: Variable:'test_module_level_use.t1'
    from: Module:'test_module_level_use'
    loc: '14:0'
  - type: Define
    to: Variable:'test_module_level_use.t2'
    from: Module:'test_module_level_use'
    loc: '14:4'
  - type: Define
    to: Variable:'test_module_level_use.t3'
    from: Module:'test_module_level_use'
    loc: '16:1'
  - type: Define
    to: Variable:'test_module_level_use.a'
    from: Module:'test_module_level_use'
    loc: '17:4'
  - type: Define
    to: Variable:'test_module_level_use.b'
    from: Module:'test_module_level_use'
    loc: '17:7'
  - type: Use
    to: Variable:'test_module_level_use.a'
    from: Module:'test_module_level_use'
    loc: '18:10'
  - type: Use
    to: Variable:'test_module_level_use.b'
    from: Module:'test_module_level_use'
    loc: '19:10'
  - type: Use
    to: Class:'test_module_level_use.Base'
    from: Module:'test_module_level_use'
    loc: '21:6'
  - type: Use
    to: Class:'test_module_level_use.Inherit'
    from: Module:'test_module_level_use'
    loc: '22:6'
  - type: Use
    to: Function:'test_module_level_use.func1'
    from: Module:'test_module_level_use'
    loc: '23:6'
  - type: Use
    to: Variable:'test_module_level_use.x'
    from: Module:'test_module_level_use'
    loc: '24:6'
  - type: Use
    to: Variable:'test_module_level_use.y'
    from: Module:'test_module_level_use'
    loc: '25:6'
  - type: Use
    to: Variable:'test_module_level_use.t1'
    from: Module:'test_module_level_use'
    loc: '27:6'
  - type: Use
    to: Variable:'test_module_level_use.t2'
    from: Module:'test_module_level_use'
    loc: '29:6'
  - type: Use
    to: Variable:'test_module_level_use.t3'
    from: Module:'test_module_level_use'
    loc: '31:6'
```


###### Use Local Definition

```python
//// test_local_use.py
def func():

    def inner():

        def inner_inner():
            print(func)

        print(func)
        print(inner_inner)

    print(inner)

def func2(p):

    x = 1

    y: int = 1

    t1, t2 = 1, 2

    (t3 := 1)

    for a, b in x:
        print(a)
        print(b)

    print(x)

    print(y)
    print(t1)

    print(t2)
    print(t3)

    print(p)
```

```yaml
name: UseLocalDefinition
relation:
  items:
  - type: Use
    to: Function:'test_local_use.func'
    from: Function:'test_local_use.func.inner.inner_inner'
    loc: '6:18'
  - type: Use
    to: Function:'test_local_use.func'
    from: Function:'test_local_use.func.inner'
    loc: '3:8'
  - type: Use
    to: Function:'test_local_use.func.inner.inner_inner'
    from: Function:'test_local_use.func.inner'
    loc: '9:14'
  - type: Use
    to: Function:'test_local_use.func.inner'
    from: Function:'test_local_use.func'
    loc: '11:10'
  - type: Use
    to: Variable:'test_local_use.func2.a'
    from: Function:'test_local_use.func2'
    loc: '24:14'
  - type: Use
    to: Variable:'test_local_use.func2.b'
    from: Function:'test_local_use.func2'
    loc: '25:14'
  - type: Use
    to: Variable:'test_local_use.func2.x'
    from: Function:'test_local_use.func2'
    loc: '27:10'
  - type: Use
    to: Variable:'test_local_use.func2.y'
    from: Function:'test_local_use.func2'
    loc: '29:10'
  - type: Use
    to: Variable:'test_local_use.func2.t1'
    from: Function:'test_local_use.func2'
    loc: '30:10'
  - type: Use
    to: Variable:'test_local_use.func2.t2'
    from: Function:'test_local_use.func2'
    loc: '32:10'
  - type: Use
    to: Variable:'test_local_use.func2.t3'
    from: Function:'test_local_use.func2'
    loc: '33:10'
  - type: Use
    to: Variable:'test_local_use.func2.p'
    from: Function:'test_local_use.func2'
    loc: '35:10'
```

###### Use Attribute
```python
//// test_use_class_attr.py
class Base:
    static_attr = 1
    def __init__(self):
        self.base_attribute = 1

class Inherit(Base):
    def __init__(self):

        super().__init__()

    def use_attribute(self):
        print(self.base_attribute)

        print(self.static_attr)

print(Base.static_attr)

class Foo:
    static_attr = Base.static_attr

```

```yaml
name: UseClassAttribute
relation:
  items:
  - type: Define
    to: Class:'test_use_class_attr.Base'
    from: Module:'test_use_class_attr'
    loc: '1:6'
  - type: Inherit
    to: Class:'test_use_class_attr.Base'
    from: Class:'test_use_class_attr.Inherit'
    loc: '6:14'
  - type: Define
    to: Class:'test_use_class_attr.Base'
    from: Module:'test_use_class_attr'
    loc: '6:6'
  - type: Use
    to: Attribute:'test_use_class_attr.Base.base_attribute'
    from: Function:'test_use_class_attr.Inherit.use_attribute'
    loc: '12:19'
  - type: Use
    to: Attribute:'test_use_class_attr.Base.static_attr'
    from: Function:'test_use_class_attr.Inherit.use_attribute'
    loc: '14:19'
  - type: Use
    from: Module:'test_use_class_attr'
    to: Attribute:'test_use_class_attr.Base.static_attr'
    loc: '16:11'
  - type: Use
    from: Class:'test_use_class_attr.Foo'
    to: Attribute:'test_use_class_attr.Base.static_attr'
    loc: '18:24'
```

###### Use Alias

```python
//// module_a.py
import module_b

def func():
    ...
x = 1

class ClassA:
    ...
```
```python
//// module_b.py
from module_a import func as f, x as x_b, ClassA as c
import module_a as a

print(f, x_b, c, a)

def foo():
    print(f, x_b, c, a)

class ClassB:
    print(f, x_b, c, a)
```
```yaml
name: UseAlias
relation:
    items:
    - from: Module:'module_b'
      to: Alias:'module_b.f'
      type: Use
      loc: '4:6'
    - from: Module:'module_b'
      to: Alias:'module_b.x_b'
      type: Use
      loc: '4:9'
    - from: Module:'module_b'
      to: Alias:'module_b.c'
      type: Use
      loc: '4:14'
    - from: Module:'module_b'
      to: Alias:'module_b.a'
      type: Use
      loc: '4:17'
    - from: Function:'module_b.foo'
      to: Alias:'module_b.f'
      type: Use
      loc: '7:10'
    - from: Function:'module_b.foo'
      to: Alias:'module_b.x_b'
      type: Use
      loc: '7:13'
    - from: Function:'module_b.foo'
      to: Alias:'module_b.c'
      type: Use
      loc: '7:18'
    - from: Function:'module_b.foo'
      to: Alias:'module_b.a'
      type: Use
      loc: '7:21'
    - from: Class:'module_b.ClassB'
      to: Alias:'module_b.f'
      type: Use
      loc: '10:10'
    - from: Class:'module_b.ClassB'
      to: Alias:'module_b.x_b'
      type: Use
      loc: '10:13'
    - from: Class:'module_b.ClassB'
      to: Alias:'module_b.c'
      type: Use
      loc: '10:18'
    - from: Class:'module_b.ClassB'
      to: Alias:'module_b.a'
      type: Use
      loc: '10:21'

```

### Properties

| Name | Description | Type | Default |
|---|---|:---:|:---:|