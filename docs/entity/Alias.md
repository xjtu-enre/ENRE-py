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
  items:
  - longname: module_b.f
    name: f
    loc: '1:29'
  - longname: module_b.x_b
    name: x_b
    loc: '1:37'
  - longname: module_a.a
    name: a
    loc: '2:19'
```

