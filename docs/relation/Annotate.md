## Relation: Annotate
An entity `x` annotate with entity `y`, when `y`  used for type annotating entity `x`.

### Supported Patterns
```yaml
name: Annotate
```

#### Semantic:

##### Examples

###### Annotation
```python
//// test_annotation.py
class ClassA:
    ...

def int_identity(x: ClassA):
    ...

x: ClassA

class ClassB:
    field: ClassA
```

```yaml
name: Annotation
relation:
  items:
  - type: Annotate
    from: Parameter:'test_annotation.int_identity.x'
    to: Class:'test_annotation.ClassA'
    loc: '4:20'
  - type: Annotate
    from: Variable:'test_annotation.x'
    to: Class:'test_annotation.ClassA'
    loc: '7:3'
  - type: Annotate
    from: Attribute:'test_annotation.ClassB.field'
    to: Class:'test_annotation.ClassA'
    loc: '10:11'
```
