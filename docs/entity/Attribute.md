## Entity: Attribute
A attribute is a field of class object or a field of class instance which can be infered from the class definition.
### Supported Patterns
```yaml
name: ClassAttributeDefinition
```
#### Syntax: ClassAttributeDefinition

```text
```

##### Examples
###### Static Class Attribute Definition
```python
//// test_static_class_attribute.py
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
  type: Attribute
  extra: false
  items:
  - type: Attribute
    qualified: test_static_class_attribute.Base.attribute_a
    name: attribute_a
    loc: '2:4'
  - type: Attribute
    qualified: test_static_class_attribute.Base.attribute_b
    name: attribute_b
    loc: '3:4'
  - type: Attribute
    qualified: test_static_class_attribute.Base.attribute_c
    name: attribute_c
    loc: '4:4'
  - type: Attribute
    qualified: test_static_class_attribute.Base.attribute_d
    name: attribute_d
    loc: '4:17'
  - type: Attribute
    qualified: test_static_class_attribute.Base.attribute_x
    name: attribute_x
    loc: '6:13'
  - type: Attribute
    qualified: test_static_class_attribute.Inherit.attribute_e
    name: attribute_e
    loc: '8:4'
  - type: Attribute
    qualified: test_static_class_attribute.Inherit.attribute_f
    name: attribute_f
    loc: '11:13'
```

### Properties

| Name | Description | Type | Default |
|---|---|:---:|:---:|
