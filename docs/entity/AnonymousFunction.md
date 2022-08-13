## Entity: AnonymousFunction
In python, an anonnymous function can be created by lambda expression.

### Supported Patterns
```yaml
name: AnonymousFunction
```

#### Syntax: AnonymousFunction
```text
```

##### Examples
###### Lambda Expression
```python
//// test_anonymous.py
lambda t: t

```
```yaml
name: AnonymousFunctionDefinition
entity:
  extra: false
  items:
  - type: AnonymousFunction
    longname: test_anonymous
    name: ''
    loc: '1:0'
```
