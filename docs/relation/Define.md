## Relation: Define
A entity `A` define another entity `B` when `B` is created in `A`'s namespace.


### Supported Patterns
```yaml
name: Define
```

#### Semantic: 

```text
```

##### Examples
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
    loc: '2:6'
    src: test_module_level_define
  - category: Define
    dest: test_module_level_define.Inherit
    loc: '6:6'
    src: test_module_level_define
  - category: Inherit
    dest: test_module_level_define.Base
    loc: '6:0'
    src: test_module_level_define.Inherit
  - category: Define
    dest: test_module_level_define.func1
    loc: '11:4'
    src: test_module_level_define
  - category: Define
    dest: test_module_level_define.x
    loc: '15:0'
    src: test_module_level_define
  - category: Define
    dest: test_module_level_define.y
    loc: '18:0'
    src: test_module_level_define
  - category: Define
    dest: test_module_level_define.t1
    loc: '21:0'
    src: test_module_level_define
  - category: Define
    dest: test_module_level_define.t2
    loc: '21:4'
    src: test_module_level_define
  - category: Define
    dest: test_module_level_define.t3
    loc: '26:1'
    src: test_module_level_define
```


- Local Definition

```python
// test_nested_define.py

def func():


    def inner():


        def inner_inner():


            func()

        func()


        inner_inner()

    inner()

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
    loc: '2:4'
    src: test_nested_define
  - category: Define
    dest: test_nested_define.func.inner
    loc: '5:8'
    src: test_nested_define.func
  - category: Define
    dest: test_nested_define.func.inner_inner
    loc: '8:12'
    src: test_nested_define.func
  - category: Define
    dest: test_nested_define.func2.x
    loc: '22:4'
    src: test_nested_define.func2
  - category: Define
    dest: test_nested_define.func2.y
    loc: '25:4'
    src: test_nested_define.func2
  - category: Define
    dest: test_nested_define.func2.t1
    loc: '28:4'
    src: test_nested_define.func2
  - category: Define
    dest: test_nested_define.func2.t2
    loc: '28:8'
    src: test_nested_define.func2
  - category: Define
    dest: test_nested_define.func2.t3
    loc: '33:5'
    src: test_nested_define.func2
```
