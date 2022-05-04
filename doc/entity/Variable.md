# Entity: Variable
A Variable is a reserved memory location for storing data values. 

## Supported pattern
```yaml
name: VariableDefinition
```

### Syntax: VariableDefinition
```yaml
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

### Examples
- Global Variable Definition

```python
// test_global_variable.py
x = 1

y: int = 1


t1, t2 = 1, 2
(t3 := 1)
```

```yaml
entities:
  exact: false
  items:
  - category: Variable
    longname: test_global_variable.x
    name: x
  - category: Variable
    longname: test_global_variable.y
    name: y
  - category: Variable
    longname: test_global_variable.t1
    name: t1
  - category: Variable
    longname: test_global_variable.t2
    name: t2
  - category: Variable
    longname: test_global_variable.t3
    name: t3
```

- Local Variable Definition

```python
// test_local_variable.func.py
def func(p1, p2):
    x = 1

    y: int = 1

    t1, t2 = 1, 2

    (t3 := 1)

```

```yaml
entities:
  exact: false
  items:
  - category: Function
    longname: test_local_variable.func
    name: func
  - category: Parameter
    longname: test_local_variable.func.p1
    name: p1
  - category: Parameter
    longname: test_local_variable.func.p2
    name: p2
  - category: Variable
    longname: test_local_variable.func.x
    name: x
  - category: Variable
    longname: test_local_variable.func.y
    name: y
  - category: Variable
    longname: test_local_variable.func.t1
    name: t1
  - category: Variable
    longname: test_local_variable.func.t2
    name: t2
  - category: Variable
    longname: test_local_variable.func.t3
    name: t3
```

- Iteration Variable

```python
// test_iteration_variable.py
x = []

for a, b in x:
    ...
```

```yaml
entities:
  exact: false
  items:
  - category: Variable
    longname: test_iteration_variable.a
    name: a
  - category: Variable
    longname: test_iteration_variable.b
    name: b
```


