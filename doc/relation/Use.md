# Relation: Use

## Supported Pattern
```yaml
name: Use
```
### Examples
- Use Module Level Definition
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
  exact: false
  items:
  - category: Define
    dest: test_module_level_use.Base
    src: test_module_level_use
    r:
    	s:o/Concept
  - category: Define
    dest: test_module_level_use.Inherit
    src: test_module_level_use
    r:
    	s:o/Concept
  - category: Inherit
    dest: test_module_level_use.Base
    src: test_module_level_use.Inherit
    r:
    	s:inheritance
  - category: Define
    dest: test_module_level_use.func1
    src: test_module_level_use
    r:
    	s:o/Concept
  - category: Define
    dest: test_module_level_use.x
    src: test_module_level_use
    r:
    	s:o/Concept
  - category: Define
    dest: test_module_level_use.y
    src: test_module_level_use
    r:
    	s:o/Concept
  - category: Define
    dest: test_module_level_use.t1
    src: test_module_level_use
    r:
    	s:o/Concept
  - category: Define
    dest: test_module_level_use.t2
    src: test_module_level_use
    r:
    	s:o/Concept
  - category: Define
    dest: test_module_level_use.t3
    src: test_module_level_use
    r:
    	s:o/Concept
  - category: Define
    dest: test_module_level_use.a
    src: test_module_level_use
    r:
    	s:o/Concept
  - category: Define
    dest: test_module_level_use.b
    src: test_module_level_use
    r:
    	s:o/Concept
  - category: Use
    dest: test_module_level_use.a
    src: test_module_level_use
    r:
    	s:.
  - category: Use
    dest: test_module_level_use.b
    src: test_module_level_use
    r:
    	s:.
  - category: Use
    dest: test_module_level_use.Base
    src: test_module_level_use
    r:
    	s:type use
  - category: Use
    dest: test_module_level_use.Inherit
    src: test_module_level_use
    r:
    	s:type use
  - category: Use
    dest: test_module_level_use.func1
    src: test_module_level_use
    r:
    	s:ambiguous use
  - category: Use
    dest: test_module_level_use.x
    src: test_module_level_use
    r:
    	s:.
  - category: Use
    dest: test_module_level_use.y
    src: test_module_level_use
    r:
    	s:.
  - category: Use
    dest: test_module_level_use.t1
    src: test_module_level_use
    r:
    	s:.
  - category: Use
    dest: test_module_level_use.t2
    src: test_module_level_use
    r:
   		s:.
  - category: Use
    dest: test_module_level_use.t3
    src: test_module_level_use
    r:
   		s:.
```


- Use Local Definition

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
  exact: false
  items:
  - category: Use
    dest: test_local_use.func
    src: test_local_use.func.inner_inner
    r:
    	s:ambiguous use
  - category: Use
    dest: test_local_use.func
    src: test_local_use.func.inner
    r:
    	s:ambiguous use
  - category: Use
    dest: test_local_use.func.inner_inner
    src: test_local_use.func.inner
    r:
    	s:x
  - category: Use
    dest: test_local_use.func.inner
    src: test_local_use.func
    r:
    	s:ambiguous use
  - category: Use
    dest: test_local_use.func2.a
    src: test_local_use.func2
    r:
    	s:x
  - category: Use
    dest: test_local_use.func2.b
    src: test_local_use.func2
    r:
    	s:x
  - category: Use
    dest: test_local_use.func2.x
    src: test_local_use.func2
    r:
    	s:x
  - category: Use
    dest: test_local_use.func2.y
    src: test_local_use.func2
    r:
    	s:x
  - category: Use
    dest: test_local_use.func2.t1
    src: test_local_use.func2
    r:
    	s:x
  - category: Use
    dest: test_local_use.func2.t2
    src: test_local_use.func2
    r:
    	s:x
  - category: Use
    dest: test_local_use.func2.t3
    src: test_local_use.func2
    r:
    	s:x
```

- Use Class Attribute
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
  exact: false
  items:
  - category: Define
    dest: test_use_class_attr.Base
    src: test_use_class_attr
    r:
    	s:o/Concept
  - category: Inherit
    dest: test_use_class_attr.Base
    src: test_use_class_attr.Inherit
    r:
    	s:inheritance
  - category: Define
    dest: test_use_class_attr.Base
    src: test_use_class_attr
    r:
    	s:o/Concept
  - category: Use
    dest: test_use_class_attr.Base.base_attribute
    src: test_use_class_attr.Inherit.use_attribute
    r:
   		s:.
  - category: Use
    dest: test_use_class_attr.Base.static_attr
    src: test_use_class_attr.Inherit.use_attribute
    r:
    	s:.
```

