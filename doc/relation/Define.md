# Relation: Define

## Supported Pattern
```yaml
name: Define
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
name: ModuleLevelDefine
relation:
  exact: false
  items:
  - category: Define
    dest: test_module_level_define.Base
    src: test_module_level_define
    r:
    	s:o/Concept
  - category: Define
    dest: test_module_level_define.Inherit
    src: test_module_level_define
    r:
    	s:o/Concept
  - category: Define
    dest: test_module_level_define.func1
    src: test_module_level_define
    r:
    	s:o/Concept
  - category: Define
    dest: test_module_level_define.x
    src: test_module_level_define
    r:
    	s:o/Concept
  - category: Define
    dest: test_module_level_define.y
    src: test_module_level_define
    r:
    	s:o/Concept
  - category: Define
    dest: test_module_level_define.t1
    src: test_module_level_define
    r:
    	s:o/Concept
  - category: Define
    dest: test_module_level_define.t2
    src: test_module_level_define
    r:
    	s:o/Concept
  - category: Define
    dest: test_module_level_define.t3
    src: test_module_level_define
    r:
    	s:o/Concept
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
name: LocalDefinition
relation:
  exact: false
  items:
  - category: Define
    dest: test_nested_define.func
    src: test_nested_define
    r:
    	s:o/Concept
  - category: Define
    dest: test_nested_define.func.inner
    src: test_nested_define.func
    r:
   		s:o/Concept
  - category: Define
    dest: test_nested_define.func.inner.inner_inner
    src: test_nested_define.func.inner
    r:
    	s:o/Concept
  - category: Define
    dest: test_nested_define.func2.x
    src: test_nested_define.func2
    r:
    	s:x
  - category: Define
    dest: test_nested_define.func2.y
    src: test_nested_define.func2
    r:
    	s:x
  - category: Define
    dest: test_nested_define.func2.t1
    src: test_nested_define.func2
    r:
    	s:x
  - category: Define
    dest: test_nested_define.func2.t2
    src: test_nested_define.func2
    r:
    	s:x
  - category: Define
    dest: test_nested_define.func2.t3
    src: test_nested_define.func2
    r:
    	s:x

```

