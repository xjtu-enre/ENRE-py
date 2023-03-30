## Relation: Set
A Set dependency indicates some object's binding in a namespace was overwritten.
### Supported Patterns
```yaml
name: Set
```

#### Semantic: 

##### Examples
###### Set Module Level Definition
```python
//// module_a.py
x = input()
x = 1
```
```yaml
name: SetModuleLevelDefinition
relation:
    type: Set
    extra: false
    items:
    - from: Module:'module_a'
      to: Variable:'module_a.x'
      type: Set
      loc: '1:0'
    - from: Module:'module_a'
      to: Variable:'module_a.x'
      type: Set
      loc: '2:0'
```
###### Set local Definition
```python
//// test_set_local.py
def foo(y):
    x = input()
    x = 1
    y = 1
```
```yaml
name: SetLocalLevelDefinition
relation:
    items:
    - from: Function:'test_set_local.foo'
      to: Variable:'test_set_local.foo.x'
      type: Set
      loc: '2:4'
    - from: Function:'test_set_local.foo'
      to: Variable:'test_set_local.foo.x'
      type: Set
      loc: '3:4'
    - from: Function:'test_set_local.foo'
      to: Parameter:'test_set_local.foo.y'
      type: Set
      loc: '4:4'
```

###### Set Attribute
```python
//// test_set_attribute.py
class Base:
    static_attr = 1
    def __init__(self):
        self.base_attribute = 1

class Inherit(Base):
    def __init__(self):

        super().__init__()

    def use_attribute(self):
        self.base_attribute = 1

        self.static_attr = 2

Base.static_attr = 2
```

```yaml
name: SetAttribute
relation:
  type: Set
  extra: false
  items:
  - type: Set
    to: Attribute:'test_set_attribute.Base.static_attr'
    from: Class:'test_set_attribute.Base'
    loc: '2:4'
  - type: Set
    to: Attribute:'test_set_attribute.Base.base_attribute'
    from: Function:'test_set_attribute.Base.__init__'
    loc: '4:13'
  - type: Set
    to: Attribute:'test_set_attribute.Base.base_attribute'
    from: Function:'test_set_attribute.Inherit.use_attribute'
    loc: '12:13'
  - type: Set
    to: Attribute:'test_set_attribute.Base.static_attr'
    from: Function:'test_set_attribute.Inherit.use_attribute'
    loc: '14:13'
  - type: Set
    from: Module:'test_set_attribute'
    to: Attribute:'test_set_attribute.Base.static_attr'
    loc: '16:5'
```

### Properties

| Name | Description | Type | Default |
|---|---|:---:|:---:|
