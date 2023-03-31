## Entity: AnonymousFunction
In python, an anonymous function can be created by lambda expression.

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
  type: AnonymousFunction
  extra: false
  items:
  - type: AnonymousFunction
    name: '<Anonymous as="Function">'
    loc: '1:0'
```

### Properties

| Name | Description | Type | Default |
|---|---|:---:|:---:|