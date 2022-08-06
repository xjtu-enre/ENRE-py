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
// test_module_level_use.py
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
    to: test_module_level_use.Base
    from: test_module_level_use
  - type: Define
    to: test_module_level_use.Inherit
    from: test_module_level_use
  - type: Inherit
    to: test_module_level_use.Base
    from: test_module_level_use.Inherit
  - type: Define
    to: test_module_level_use.func1
    from: test_module_level_use
  - type: Define
    to: test_module_level_use.x
    from: test_module_level_use
  - type: Define
    to: test_module_level_use.y
    from: test_module_level_use
  - type: Define
    to: test_module_level_use.t1
    from: test_module_level_use
  - type: Define
    to: test_module_level_use.t2
    from: test_module_level_use
  - type: Define
    to: test_module_level_use.t3
    from: test_module_level_use
  - type: Define
    to: test_module_level_use.a
    from: test_module_level_use
  - type: Define
    to: test_module_level_use.b
    from: test_module_level_use
  - type: Use
    to: test_module_level_use.a
    from: test_module_level_use
  - type: Use
    to: test_module_level_use.b
    from: test_module_level_use
  - type: Use
    to: test_module_level_use.Base
    from: test_module_level_use
  - type: Use
    to: test_module_level_use.Inherit
    from: test_module_level_use
  - type: Use
    to: test_module_level_use.func1
    from: test_module_level_use
  - type: Use
    to: test_module_level_use.x
    from: test_module_level_use
  - type: Use
    to: test_module_level_use.y
    from: test_module_level_use
  - type: Use
    to: test_module_level_use.t1
    from: test_module_level_use
  - type: Use
    to: test_module_level_use.t2
    from: test_module_level_use
  - type: Use
    to: test_module_level_use.t3
    from: test_module_level_use
```


###### Use Local Definition

```python
// test_local_use.py
def func():

    def inner():

        def inner_inner():
            print(func)

        print(func)
        print(inner_inner)

    print(inner)

def func2():

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

```

```yaml
name: UseLocalDefinition
relation:
  items:
  - type: Use
    to: test_local_use.func
    from: test_local_use.func.inner_inner
  - type: Use
    to: test_local_use.func
    from: test_local_use.func.inner
  - type: Use
    to: test_local_use.func.inner_inner
    from: test_local_use.func.inner
  - type: Use
    to: test_local_use.func.inner
    from: test_local_use.func
  - type: Use
    to: test_local_use.func2.a
    from: test_local_use.func2
  - type: Use
    to: test_local_use.func2.b
    from: test_local_use.func2
  - type: Use
    to: test_local_use.func2.x
    from: test_local_use.func2
  - type: Use
    to: test_local_use.func2.y
    from: test_local_use.func2
  - type: Use
    to: test_local_use.func2.t1
    from: test_local_use.func2
  - type: Use
    to: test_local_use.func2.t2
    from: test_local_use.func2
  - type: Use
    to: test_local_use.func2.t3
    from: test_local_use.func2
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

