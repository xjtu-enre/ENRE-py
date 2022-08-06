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
###### Module Level Definition
```python
//// test_module_level_define.py

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
  items:
  - type: Define
    to: Class:'test_module_level_define.Base'
    loc: '2:6'
    from: Module:'test_module_level_define'
  - type: Define
    to: Class:'test_module_level_define.Inherit'
    loc: '6:6'
    from: Module:'test_module_level_define'
  - type: Inherit
    to: Class:'test_module_level_define.Base'
    loc: '6:0'
    from: Class:'test_module_level_define.Inherit'
  - type: Define
    to: Function:'test_module_level_define.func1'
    loc: '11:4'
    from: Module:'test_module_level_define'
  - type: Define
    to: Variable:'test_module_level_define.x'
    loc: '15:0'
    from: Module:'test_module_level_define'
  - type: Define
    to: Variable:'test_module_level_define.y'
    loc: '18:0'
    from: Module:'test_module_level_define'
  - type: Define
    to: Variable:'test_module_level_define.t1'
    loc: '21:0'
    from: Module:'test_module_level_define'
  - type: Define
    to: Variable:'test_module_level_define.t2'
    loc: '21:4'
    from: Module:'test_module_level_define'
  - type: Define
    to: Variable:'test_module_level_define.t3'
    loc: '26:1'
    from: Module:'test_module_level_define'
```


###### Local Definition

```python
//// test_nested_define.py

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
  items:
  - type: Define
    to: Function:'test_nested_define.func'
    loc: '2:4'
    from: Module:'test_nested_define'
  - type: Define
    to: Function:'test_nested_define.func.inner'
    loc: '5:8'
    from: Function:'test_nested_define.func'
  - type: Define
    to: Function:'test_nested_define.func.inner.inner_inner'
    loc: '8:12'
    from: Function:'test_nested_define.func'
  - type: Define
    to: Variable:'test_nested_define.func2.x'
    loc: '22:4'
    from: Function:'test_nested_define.func2'
  - type: Define
    to: Variable:'test_nested_define.func2.y'
    loc: '25:4'
    from: Function:'test_nested_define.func2'
  - type: Define
    to: Variable:'test_nested_define.func2.t1'
    loc: '28:4'
    from: Function:'test_nested_define.func2'
  - type: Define
    to: Variable:'test_nested_define.func2.t2'
    loc: '28:8'
    from: Function:'test_nested_define.func2'
  - type: Define
    to: Variable:'test_nested_define.func2.t3'
    loc: '33:5'
    from: Function:'test_nested_define.func2'
```


###### Parameter Definition

```python
//// test_parameter_define.py

def func(x0, y0, z0):


    def inner(x0, y0, z0):


        def inner_inner(x0, y0, z0):
            ...
        ...
    ...

```

```yaml
name: ParameterDefinition
relation:
  items:
  - type: Define
    to: Function:'test_parameter_define.func'
    loc: '2:4'
    from: Module:'test_parameter_define'
  - type: Define
    to: Function:'test_parameter_define.func.inner'
    loc: '5:8'
    from: Function:'test_parameter_define.func'
  - type: Define
    to: Function:'test_parameter_define.func.inner.inner_inner'
    loc: '8:12'
    from: Function:'test_parameter_define.func'
  - type: Define
    to: Parameter:'test_parameter_define.func.x0'
    from: Function:'test_parameter_define.func'
    loc: '2:9'
  - type: Define
    to: Parameter:'test_parameter_define.func.y0'
    from: Function:'test_parameter_define.func'
    loc: '2:13'
  - type: Define
    to: Parameter:'test_parameter_define.func.z0'
    from: Function:'test_parameter_define.func'
    loc: '2:17'
  - type: Define
    to: Parameter:'test_parameter_define.func.inner.x0'
    from: Function:'test_parameter_define.func.inner'
    loc: '5:14'
  - type: Define
    to: Parameter:'test_parameter_define.func.inner.y0'
    from: Function:'test_parameter_define.func.inner'
    loc: '5:18'
  - type: Define
    to: Parameter:'test_parameter_define.func.inner.z0'
    from: Function:'test_parameter_define.func.inner'
    loc: '5:22'
  - type: Define
    to: Parameter:'test_parameter_define.func.inner.inner_inner.x0'
    from: Function:'test_parameter_define.func.inner.inner_inner'
    loc: '8:24'
  - type: Define
    to: Parameter:'test_parameter_define.func.inner.inner_inner.y0'
    from: Function:'test_parameter_define.func.inner.inner_inner'
    loc: '8:28'
  - type: Define
    to: Parameter:'test_parameter_define.func.inner.inner_inner.z0'
    from: Function:'test_parameter_define.func.inner.inner_inner'
    loc: '8:32'
```