## Entity: Alias
Alias created by import statement with `as`.

### Supported Patterns
```yaml
name: AliasDefinition
```

#### Syntax: Alias Definition
```text
```
##### Examples
###### Global Alias
```python
//// module_a.py
def func():
    ...
x = 1

```
```python
//// module_b.py
from module_a import func as f, x as x_b
import module_a as a

```

```yaml
name: GlobalImport
entity:
  type: Alias
  extra: false
  items:
  - qualified: module_b.f
    name: f
    loc: 'file1:1:29'
  - qualified: module_b.x_b
    name: x_b
    loc: 'file1:1:37'
  - qualified: module_b.a
    name: a
    loc: 'file1:2:19'
```

### Properties

| Name | Description | Type | Default |
|---|---|:---:|:---:|

