## Entity: Class Attribute
A class attribute is a field of class object or a field of class instance which can be infered from the class definition.
### Supported Patterns
```yaml
name: ClassAttributeDefinition
```
#### Syntax: ClassAttributeDefinition

```text
```

##### Examples
- Static Class Attribute Definition
```python
// test_static_class_attribute.py
class Base:
    attribute_a = 1
    attribute_b: int
    attribute_c, attribute_d = 1, 2 
    def __init__(self):
        self.attribute_x = 1
class Inherit(Base):
    attribute_e = 1
    def __init__(self):
        super().__init__()        
        self.attribute_f = 1

```

```yaml
name: StaticClassAttributeDefinition
entity:
  exact: false
  items:
  - type: Class
    longname: test_static_class_attribute.Base
    name: Base
  - type: Class Attribute
    longname: test_static_class_attribute.Base.attribute_a
    name: attribute_a
  - type: Class Attribute
    longname: test_static_class_attribute.Base.attribute_b
    name: attribute_b
  - type: Class Attribute
    longname: test_static_class_attribute.Base.attribute_c
    name: attribute_c
  - type: Class Attribute
    longname: test_static_class_attribute.Base.attribute_d
    name: attribute_d
  - type: Class Attribute
    longname: test_static_class_attribute.Base.attribute_x
    name: attribute_x
  - type: Class
    longname: test_static_class_attribute.Inherit
    name: Inherit
  - type: Class Attribute
    longname: test_static_class_attribute.Inherit.attribute_e
    name: attribute_e
  - type: Class Attribute
    longname: test_static_class_attribute.Inherit.attribute_f
    name: attribute_f
```