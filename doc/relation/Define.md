# Relation: Define

## Supported Pattern
```yaml
Define
```
### Examples
- Module Level Definition
```python
// test_module_level_define.py

class Base:
    ...

class Inherit(Base):
    ...

def func1():
    return 0

x = 1

y: int = 1

t1, t2 = 1, 2

(t3 := 1)


```

```yaml
entity:
  exact: false
  items:
  - category: Module
    longname: test_module_level_define
    name: test_module_level_define
  - category: Class
    longname: test_module_level_define.Base
    name: Base
  - category: Class
    longname: test_module_level_define.Inherit
    name: Inherit
  - category: Function
    longname: test_module_level_define.func1
    name: func1
  - category: Variable
    longname: test_module_level_define.x
    name: x
  - category: Variable
    longname: test_module_level_define.y
    name: y
  - category: Variable
    longname: test_module_level_define.t1
    name: t1
  - category: Variable
    longname: test_module_level_define.t2
    name: t2
  - category: Variable
    longname: test_module_level_define.t3
    name: t3
relation:
  exact: false
  items:
    entity:
      exact: false
      items:
      - category: Define
        dest: test_module_level_define.Base
        src: test_module_level_define
      - category: Define
        dest: test_module_level_define.Inherit
        src: test_module_level_define
      - category: Define
        dest: test_module_level_define.func1
        src: test_module_level_define
      - category: Define
        dest: test_module_level_define.x
        src: test_module_level_define
      - category: Define
        dest: test_module_level_define.y
        src: test_module_level_define
      - category: Define
        dest: test_module_level_define.t1
        src: test_module_level_define
      - category: Define
        dest: test_module_level_define.t2
        src: test_module_level_define
      - category: Define
        dest: test_module_level_define.t3
        src: test_module_level_define

```


- Local Definition

```python
// test_nested_define.py
def func():

    def inner():

        def inner_inner():
            ...

        ...

    ...

def func2():

    x = 1
    y: int = 1

    t1, t2 = 1, 2

    (t3 := 1)

```

```yaml
entity:
  exact: false
  items:
  - category: Module
    longname: test_nested_define
    name: test_nested_define
  - category: Function
    longname: test_nested_define.func
    name: func
  - category: Function
    longname: test_nested_define.func.inner
    name: inner
  - category: Function
    longname: test_nested_define.func.inner_inner
    name: inner_inner
  - category: Function
    longname: test_nested_define.func2
    name: func2
  - category: Variable
    longname: test_nested_define.func2.x
    name: x
  - category: Variable
    longname: test_nested_define.func2.y
    name: y
  - category: Variable
    longname: test_nested_define.func2.t1
    name: t1
  - category: Variable
    longname: test_nested_define.func2.t2
    name: t2
  - category: Variable
    longname: test_nested_define.func2.t3
    name: t3
relation:
  exact: false
  items:
    entity:
      exact: false
      items:
      - category: Define
        dest: test_nested_define.func
        src: test_nested_define
      - category: Define
        dest: test_nested_define.func.inner
        src: test_nested_define.func
      - category: Define
        dest: test_nested_define.func.inner_inner
        src: test_nested_define.func
      - category: Define
        dest: test_nested_define.func2.x
        src: test_nested_define.func2
      - category: Define
        dest: test_nested_define.func2.y
        src: test_nested_define.func2
      - category: Define
        dest: test_nested_define.func2.t1
        src: test_nested_define.func2
      - category: Define
        dest: test_nested_define.func2.t2
        src: test_nested_define.func2
      - category: Define
        dest: test_nested_define.func2.t3
        src: test_nested_define.func2
```

