## Relation: Import
An `Alias` relation created by import statement with `as`.
### Supported Patterns
```yaml
name: Alias
```

#### Semantic: 

##### Examples

###### Global Import

```python
var = 1

def func():
    pass
    
class Clz:
    pass
```

```python
import file0 as f
from file0 import var as v, func as fu, Clz as C
```

```yaml
name: GlobalImport
relation:
  type: Alias
  extra: false
  items:
    - from: Alias:'f'
      to: Module:'file0'
      loc: file1:1:23
    - from: Alias:'v'
      to: Variable:'var'
      loc: file1:2:25
    - from: Alias:'fu'
      to: Function:'func'
      loc: file1:2:36
    - from: Alias:'C'
      to: Class:'Clz'
      loc: file1:2:47
```

###### Local Import

```python
var = 1

def func():
    pass
    
class Clz:
    pass
```

```python
def foo():
    from file0 import var as v, func as f, Clz as C

class Bar:
    from file0 import var as v1, func as f1, Clz as C1
```

```yaml
name: LocalImport
relation:
  type: Alias
  extra: false
  items:
    - from: Alias:'v'
      to: Variable:'var'
      loc: file1:2:29
    - from: Alias:'f'
      to: Function:'func'
      loc: file1:2:40
    - from: Alias:'C'
      to: Class:'Clz'
      loc: file1:2:50
    - from: Alias:'v1'
      to: Variable:'var'
      loc: file1:5:29
    - from: Alias:'f1'
      to: Function:'func'
      loc: file1:5:41
    - from: Alias:'C1'
      to: Class:'Clz'
      loc: file1:5:52
```

### Properties

| Name | Description | Type | Default |
|---|---|:---:|:---:|