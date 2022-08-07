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

###### Use Class Attribute
```python
// test_use_class_attr.py
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

```

```yaml
name: UseClassAttribute
relation:
  items:
  - type: Define
    to: test_use_class_attr.Base
    from: test_use_class_attr
  - type: Inherit
    to: test_use_class_attr.Base
    from: test_use_class_attr.Inherit
  - type: Define
    to: test_use_class_attr.Base
    from: test_use_class_attr
  - type: Use
    to: test_use_class_attr.Base.base_attribute
    from: test_use_class_attr.Inherit.use_attribute
  - type: Use
    to: test_use_class_attr.Base.static_attr
    from: test_use_class_attr.Inherit.use_attribute
```

