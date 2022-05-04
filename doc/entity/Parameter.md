# Entity: Parameter
A parameter is the variable listed inside the parentheses in the function definition. 

## Supported pattern
```yaml
name: ParameterDefinition
```
### Syntax: ParameterDefinition

```yaml
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
  - category: Parameter
    longname: test_parameter.func1.x
    name: x
  - category: Function
    longname: test_parameter.func2
    name: func2
  - category: Parameter
    longname: test_parameter.func2.x
    name: x
  - category: Function
    longname: test_parameter.func3
    name: func3
  - category: Parameter
    longname: test_parameter.func3.x
    name: x
  - category: Parameter
    longname: test_parameter.func3.y
    name: y
  - category: Parameter
    longname: test_parameter.func3.z
    name: z
  - category: Function
    longname: test_parameter.func4
    name: func4
  - category: Parameter
    longname: test_parameter.func4.x
    name: x
  - category: AnonymousFunction
    longname: test_parameter.func4.(32)
    name: null
  - category: Lambda Parameter
    longname: test_parameter.func4.(32).t
    name: t

```