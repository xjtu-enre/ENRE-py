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
//// module_a.py
import module_b

def func():
    ...
x = 1

class ClassA:
    ...
```
```python
//// module_b.py
from module_a import func as f, x as x_b, ClassA as c
import module_a as a

```

```yaml
name: GlobalImport
relation:
  items:
  - type: Import
    from: Module:'module_a'
    to: Module:'module_b'
    loc: 'file0:1:7'
  - type: Import
    from: Module:'module_b'
    to: Function:'module_a.func'
    loc: 'file1:1:21'
  - type: Import
    from: Module:'module_b'
    to: Variable:'module_a.x'
    loc: 'file1:2:32'
  - type: Import
    from: Module:'module_b'
    to: Module:'module_a'
    loc: 'file1:2:7'
  - type: Alias
    from: Alias:'module_b.f'
    to: Function:'module_a.func'
    loc: 'file1:1:29'
  - type: Alias
    from: Alias:'module_b.c'
    to: Class:'module_a.ClassA'
    loc: 'file1:1:52'
  - type: Alias
    from: Alias:'module_b.x_b'
    to: Variable:'module_a.x'
    loc: 'file1:1:37'
  - type: Alias
    from: Alias:'module_b.a'
    to: Module:'module_a'
    loc: 'file1:2:19'
  - type: Define
    from: Module:'module_b'
    to: Alias:'module_b.x_b'
    loc: 'file1:1:37'
  - type: Define
    from: Module:'module_b'
    to: Alias:'module_b.f'
    loc: 'file1:1:29'
  - type: Define
    from: Module:'module_b'
    to: Alias:'module_b.a'
    loc: 'file1:2:19'
```
###### Local Import
```python
//// module_c.py
def func():
    ...
```

```python
//// module_d.py
def foo():
    import module_c as c
    from module_c import func
```

```yaml
name: LocalImport
relation:
  items:
  - type: Import
    from: Function:'module_d.foo'
    to: Module:'module_c'
    loc: 'file1:2:11'
  - type: Import
    from: Function:'module_d.foo'
    to: Function:'module_c.func'
    loc: 'file1:3:25'
  - type: Alias
    from: Alias:'module_d.foo.c'
    to: Module:'module_c'
    loc: 'file1:2:23'
  - type: Alias
    from: Alias:'module_d.foo.func'
    to: Function:'module_c.func'
    loc: 'file1:3:25'
  - type: Define
    from: Function:'module_d.foo'
    to: Alias:'module_d.foo.c'
    loc: 'file1:2:23'
```
