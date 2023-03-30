## Relation: Contain
A package contains modules and sub-packages.

### Supported Patterns
```yaml
name: Contain
```

#### Semantic:

##### Examples
###### PackageContain
```python
//// package_a/
```

```python
//// package_a/__init__.py
```

```python
//// package_a/module_a.py
```

```python
//// package_a/package_b/
```

```python
//// package_a/package_b/__init__.py
```

```yaml
name: RegularPackage
relation: 
  items:
  - from: Package:'package_a'
    to: Module:'package_a.__init__' 
    loc: 'file1'
    type: Contain
  - from: Package:'package_a'
    to: Module:'package_a.module_a' 
    loc: 'file2'
    type: Contain
  - from: Package:'package_a'
    to: Package:'package_b'
    loc: 'file3'
    type: Contain
  - from: Package:'package_b'
    to: Module:'package_a.package_b.__init__' 
    loc: 'file1'
    type: Contain
```

### Properties

| Name | Description | Type | Default |
|---|---|:---:|:---:|
