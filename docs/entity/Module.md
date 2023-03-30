## Entity: Module
An object that serves as an organizational unit of Python code. Modules have a namespace containing arbitrary Python objects. Definition within a module can be imported by import statement.

### Supported Patterns

```yaml
name: ModuleDefinition
```

#### Syntax: ModuleDefinition
```text
```

##### Examples

###### Module Definition
```python
//// test_module_a.py
import test_module_b as b
```

```python
//// test_module_b.py
import test_module_a as a
```

```yaml
name: ModuleDefinition
entity:
  type: Module
  extra: false
  items:
    - type: Module
      qualified: test_module_a
      name: test_module_a
      loc: 'file0'
    - type: Module
      qualified: test_module_b
      name: test_module_b
      loc: 'file1'
```