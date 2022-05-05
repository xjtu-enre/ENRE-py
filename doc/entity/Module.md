# Entity: Module
An object that serves as an organizational unit of Python code. Modules have a namespace containing arbitrary Python objects. Definition within a module can be imported by import statement.

## Syntax: Module
```
```

### Examples

- Module Definition
```python
// test_module_a.py
import test_module_b as b

// test_module_b.py
import test_module_a as a
```

```yaml
name: ModuleDefinition
exact: false
items:
  - category: Module
    longname: test_module_a
    name: test_module_a
    r:
        d: 
        e:
        s:.
        u:
  - category: Module
    longname: test_module_b
    name: test_module_b
    r:
        d: 
        e:
        s:.
        u:
  - category: Module Alias
    longname: test_module_a.b
    name: b
    r:
        d: 
        e:
        s:.
        u:
  - category: Module Alias
    longname: test_module_b.a
    name: a
    r:
        d: 
        e:
        s:.
        u:
```