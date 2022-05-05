# Entity: Class Attribute
A class attribute is a field of class object or a field of class instance which can be infered from the class definition.
## Supported pattern
```yaml
name: ClassAttributeDefinition
```
## Syntax: ClassAttributeDefinition

```
```

### Examples
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
  - category: Class
    longname: test_static_class_attribute.Base
    name: Base
    r:
    	d: 
    	e:
    	s:.
    	u:
  - category: Class Attribute
    longname: test_static_class_attribute.Base.attribute_a
    name: attribute_a
    r:
    	d: 
    	e:
    	s:field
    	u:
  - category: Class Attribute
    longname: test_static_class_attribute.Base.attribute_b
    name: attribute_b
    r:
    	d: 
    	e:
    	s:field
    	u:
  - category: Class Attribute
    longname: test_static_class_attribute.Base.attribute_c
    name: attribute_c
    r:
    	d: 
    	e:
    	s:field
    	u:
  - category: Class Attribute
    longname: test_static_class_attribute.Base.attribute_d
    name: attribute_d
    r:
    	d: 
    	e:
    	s:field
    	u:
  - category: Class Attribute
    longname: test_static_class_attribute.Base.attribute_x
    name: attribute_x
    r:
    	d: 
    	e:
    	s:field
    	u:
  - category: Class
    longname: test_static_class_attribute.Inherit
    name: Inherit
    r:
    	d: 
    	e:
    	s:.
    	u:
  - category: Class Attribute
    longname: test_static_class_attribute.Inherit.attribute_e
    name: attribute_e
    r:
    	d: 
    	e:
    	s:field
    	u:
  - category: Class Attribute
    longname: test_static_class_attribute.Inherit.attribute_f
    name: attribute_f
    r:
    	d: 
    	e:
    	s:field
    	u:
```
