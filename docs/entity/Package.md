## Entity: Package
A package is a collection of modules or sub-packages. There are two types of packages in Python: regular package and namespace package.  A regular package requires an `__init__.py` file, while a namespace package doesn't.

### Supported Patterns
```yaml
name: PackageDefinition
```

#### Syntax: Alias Definition
```text
```
##### Examples
###### Regular Package
```python
//// package_a/
```

```python
//// package_a/__init__.py
```

```python
//// package_a/module_a.py
```

```yaml
name: RegularPackage
entity: 
  extra: false
  items:
  - longname: package_a
    name: package_a
    loc: 'file0'
    type: Package
```


###### Namespace Package
```python
//// package_a/
```

```python
//// package_a/module_a.py
```
```yaml
name: NamespacePackage
entity: 
  extra: false
  items:
  - longname: package_a
    name: package_a
    loc: 'file0'
    type: Package
```

### Properties

| Name | Description | Type | Default |
|---|---|:---:|:---:|

