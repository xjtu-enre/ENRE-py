## Entity: Variable
A Variable is a reserved memory location for storing data values. 

### Supported Patterns
```yaml
name: VariableDefinition
```

#### Syntax: VariableDefinition
```text
assignment_stmt :  (target_list =)+ (starred_expression | yield_expression)
target_list     :  target ("," target)* [","]
target          :  identifier
                   | "(" [target_list] ")"
                   | "[" [target_list] "]"
                   | attributeref
                   | subscription
                   | slicing
                   | "*" target
```

##### Examples
###### Global Variable Definition

```python
//// test_global_variable.py
x = 1

y: int = 1


t1, t2 = 1, 2
(t3 := 1)
```

```yaml
name: GlobalVariableDefinition
entity:
  type: Variable
  extra: false
  items:
  - type: Variable
    qualified: test_global_variable.x
    name: x
    loc: '1:0'
  - type: Variable
    qualified: test_global_variable.y
    name: y
    loc: '3:0'
  - type: Variable
    qualified: test_global_variable.t1
    name: t1
    loc: '6:0'
  - type: Variable
    qualified: test_global_variable.t2
    name: t2
    loc: '6:4'
  - type: Variable
    qualified: test_global_variable.t3
    name: t3
    loc: '7:1'
```

###### Local Variable Definition

```python
//// test_local_variable.py
def func(p1, p2):
    x = 1

    y: int = 1

    t1, t2 = 1, 2

    (t3 := 1)
    def inner():
        x = 1

        y: int = 1

        t1, t2 = 1, 2

        (t3 := 1)



```

```yaml
name: LocalVariableDefinition
entity:
  type: Variable
  extra: false
  items:
  - type: Variable
    qualified: test_local_variable.func.x
    name: x
    loc: '2:4'
  - type: Variable
    qualified: test_local_variable.func.y
    name: y
    loc: '4:4'
  - type: Variable
    qualified: test_local_variable.func.t1
    name: t1
    loc: '6:4'
  - type: Variable
    qualified: test_local_variable.func.t2
    name: t2
    loc: '6:8'
  - type: Variable
    qualified: test_local_variable.func.t3
    name: t3
    loc: '8:5'
  - type: Variable
    qualified: test_local_variable.func.inner.x
    name: x
    loc: '10:8'
  - type: Variable
    qualified: test_local_variable.func.inner.y
    name: y
    loc: '12:8'
  - type: Variable
    qualified: test_local_variable.func.inner.t1
    name: t1
    loc: '14:8'
  - type: Variable
    qualified: test_local_variable.func.inner.t2
    name: t2
    loc: '14:12'
  - type: Variable
    qualified: test_local_variable.func.inner.t3
    name: t3
    loc: '16:9'
```

###### Iteration Variable

```python
//// test_iteration_variable.py
x = []

for a, b in x:
    ...

def func():
    for c, d in x:
      ...

```

```yaml
name: IterationVariable
entity:
  type: Variable
  extra: false
  items:
  - type: Variable
    qualified: test_iteration_variable.a
    name: x
    loc: '1:0'
  - type: Variable
    qualified: test_iteration_variable.a
    name: a
    loc: '3:4'
  - type: Variable
    qualified: test_iteration_variable.b
    name: b
    loc: '3:7'
  - type: Variable
    qualified: test_iteration_variable.func.c
    name: c
    loc: '7:8'
  - type: Variable
    qualified: test_iteration_variable.func.d
    name: d
    loc: '7:11'
```

### Properties

| Name | Description | Type | Default |
|---|---|:---:|:---:|