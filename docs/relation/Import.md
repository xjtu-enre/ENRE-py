## Relation: Import
A Import dependency indicates a python module was imported, locally or globally.
### Supported Patterns
```yaml
name: Import
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
from file0 import *
from file0 import var, func, Clz
import file0
```

```yaml
name: GlobalImport
relation:
  type: Import
  extra: false
  items:
    - from: Module:'file1'
      to: Module:'file0'
      loc: file1:1:18
    - from: Module:'file1'
      to: Variable:'var'
      loc: file1:2:18
    - from: Module:'file1'
      to: Function:'func'
      loc: file1:2:23
    - from: Module:'file1'
      to: Class:'Clz'
      loc: file1:2:29
    - from: Module:'file1'
      to: Module:'file0'
      loc: file1:3:8
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
    from file0 import var, func, Clz

class Bar:
    from file0 import var, func, Clz
```

```yaml
name: LocalImport
relation:
  type: Import
  extra: false
  items:
    - from: Function:'foo'
      to: Variable:'var'
      loc: file1:2:22
    - from: Function:'foo'
      to: Function:'func'
      loc: file1:2:27
    - from: Function:'foo'
      to: Class:'Clz'
      loc: file1:2:33
    - from: Class:'Bar'
      to: Variable:'var'
      loc: file1:5:22
    - from: Class:'Bar'
      to: Function:'func'
      loc: file1:5:27
    - from: Class:'Bar'
      to: Class:'Clz'
      loc: file1:5:33
```

### Properties

| Name | Description | Type | Default |
|---|---|:---:|:---:|
