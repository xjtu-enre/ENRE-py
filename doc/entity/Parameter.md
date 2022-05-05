# Entity: Parameter
A parameter is the variable listed inside the parentheses in the function definition. 

## Supported pattern
```yaml
name: ParameterDefinition
```
### Syntax: ParameterDefinition

```
parameter_list            :  defparameter ("," defparameter)* "," "/" ["," [parameter_list_no_posonly]]
                               | parameter_list_no_posonly
parameter_list_no_posonly :  defparameter ("," defparameter)* ["," [parameter_list_starargs]]
                             | parameter_list_starargs
parameter_list_starargs   :  "*" [parameter] ("," defparameter)* ["," ["**" parameter [","]]]
                             | "**" parameter [","]
parameter                 :  identifier [":" expression]
```

### Examples

- Parameter Definition

```python
// test_parameter.py
def func1(x):
    ...

def func2(x: int):
    ...

def func3(x, *y, **z):
    ...

def func4(x: int=1):
    ...

lambda t: t

```

```yaml
name: ParameterDefinition
entity:
  exact: false
  items:
  - category: Function
    longname: test_parameter.func1
    name: func1
    r:
        d: 
        e:
        s:.
        u:
  - category: Parameter
    longname: test_parameter.func1.x
    name: x
    r:
        d: 
        e:
        s:x
        u:
  - category: Function
    longname: test_parameter.func2
    name: func2
    r:
        d: 
        e:
        s:.
        u:
  - category: Parameter
    longname: test_parameter.func2.x
    name: x
    r:
        d: 
        e:
        s:x
        u:
  - category: Function
    longname: test_parameter.func3
    name: func3
    r:
        d: 
        e:
        s:.
        u:
  - category: Parameter
    longname: test_parameter.func3.x
    name: x
    r:
        d: 
        e:
        s:x
        u:
  - category: Parameter
    longname: test_parameter.func3.y
    name: y
    r:
        d: 
        e:
        s:x
        u:
  - category: Parameter
    longname: test_parameter.func3.z
    name: z
    r:
        d: 
        e:
        s:x
        u:
  - category: Function
    longname: test_parameter.func4
    name: func4
    r:
        d: 
        e:
        s:.
        u:
  - category: Parameter
    longname: test_parameter.func4.x
    name: x
    r:
        d: 
        e:
        s:x
        u:
  - category: AnonymousFunction
    longname: test_parameter.func4.(32)
    name: null
    r:
        d: 
        e:
        s:x
        u:
  - category: Lambda Parameter
    longname: test_parameter.func4.(32).t
    name: t
    r:
        d: 
        e:
        s:x
        u:

```