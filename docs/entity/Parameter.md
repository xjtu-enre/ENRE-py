## Entity: Parameter
A parameter is the variable listed inside the parentheses in the function definition. 

### Supported Patterns
```yaml
name: ParameterDefinition
```
#### Syntax: ParameterDefinition

```text
parameter_list            :  defparameter ("," defparameter)* "," "/" ["," [parameter_list_no_posonly]]
                               | parameter_list_no_posonly
parameter_list_no_posonly :  defparameter ("," defparameter)* ["," [parameter_list_starargs]]
                             | parameter_list_starargs
parameter_list_starargs   :  "*" [parameter] ("," defparameter)* ["," ["**" parameter [","]]]
                             | "**" parameter [","]
parameter                 :  identifier [":" expression]
```

##### Examples

###### Parameter Definition

```python
//// test_parameter.py
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
  type: Parameter
  extra: false
  items:
  - type: Parameter
    qualified: test_parameter.func1.x
    name: x
    loc: '1:10'
  - type: Parameter
    qualified: test_parameter.func2.x
    name: x
    loc: '4:10'
  - type: Parameter
    qualified: test_parameter.func3.x
    name: x
    loc: '7:10'
  - type: Parameter
    qualified: test_parameter.func3.y
    name: y
    loc: '7:14'
  - type: Parameter
    qualified: test_parameter.func3.z
    name: z
    loc: '7:19'
  - type: Parameter
    qualified: test_parameter.func4.x
    name: x
    loc: '10:10'
  - type: Parameter
    qualified: 'test_parameter.func4.(13).t'
    name: t
    loc: '13:7'
```

### Properties

| Name | Description | Type | Default |
|---|---|:---:|:---:|