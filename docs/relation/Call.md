## Relation: Call
Calling a callable object indicates a call dependency.

### Supported Patterns
```yaml
name: Call
```

#### Semantic: 

##### Examples

###### Global Function Call
```python
//// test_global_function_call.py

def func1():


    func1()


    return 0

func1()


```

```yaml
name: GlobalFunctionCall
relation:
  items:
  - type: Call
    to: Function:'test_global_function_call.func1'
    loc: '5:4'
    from: Function:'test_global_function_call.func1'
  - type: Call
    to: Function:'test_global_function_call.func1'
    loc: '10:0'
    from: Module:'test_global_function_call'
```
###### Class Method Call
```python
//// test_method_call.py

class ClassA:


    def method(self):


        ...
class ClassB:


    def method(self):


        ...
instance = ClassA()


instance.method()

```


```yaml
name: ClassMethodCall
relation:
  items:
  - type: Call
    to: Function:'test_method_call.ClassA.method'
    loc: '19:9'
    from: Module:'test_method_call'
```

###### Local Function Call
```python
//// test_local_call.py

def func():


    def inner():


        def inner_inner():


            func()

        func()


        inner_inner()

    inner()

```

```yaml
name: LocalFunctionCall
relation:
  items:
  - type: Call
    to: Function:'test_local_call.func'
    loc: '11:12'
    from: Function:'test_local_call.func.inner.inner_inner'
  - type: Call
    to: Function:'test_local_call.func'
    loc: '13:8'
    from: Function:'test_local_call.func.inner'
  - type: Call
    to: Function:'test_local_call.func.inner.inner_inner'
    loc: '16:8'
    from: Function:'test_local_call.func.inner'
  - type: Call
    to: Function:'test_local_call.func.inner'
    loc: '18:4'
    from: Function:'test_local_call.func'
```

###### First Order Function Call
``` python
//// test_first_order_func_call.py
def foo():
    ...

def acceptor(f):
    f()

acceptor(foo)
```

```yaml
name: FirstOrderFunctionCall
relation:
    type: Call
    items:
    - to: Variable:'test_first_order_func_call.acceptor.f'
      from: Function:'test_first_order_func_call.acceptor'
      loc: '5:4'
    - to: Function:'test_first_order_func_call.foo'
      from: Function:'test_first_order_func_call.acceptor'
      loc: '5:4'
    - to: Function:'test_first_order_func_call.acceptor'
      from: Module:'test_first_order_func_call'
      loc: '7:0'
```

###### First Order Function Call
``` python
//// test_first_order_class_call.py
class Base:
    ...

base = Base()

def create_class():
    class Difficult:
        def test(self):
            ...
    return Difficult

cls = create_class()

difficult_obj = cls()

difficult_obj.test()
```

```yaml
name: FirstOrderClassCall
relation:
    type: Call
    items:
    - to: Class:'test_first_order_class_call.Base'
      from: Module:'test_first_order_class_call'
      loc: '4:7'
    - to: Function:'test_first_order_class_call.create_class'
      from: Module:'test_first_order_class_call'
      loc: '12:6'
    - to: Variable:'test_first_order_class_call.cls'
      from: Module:'test_first_order_class_call'
      loc: '14:16'
    - to: Function:'test_first_order_class_call.create_class.Difficult.test'
      from: Module:'test_first_order_class_call'
      loc: '16:14'
    - to: Class:'test_first_order_class_call.create_class.Difficult'
      from: Function:'test_first_order_class_call.create_class'
      type: Define
      loc: '7:4'
```

###### Decorator Call
```python
////test_decorator_call.py
def f1(a):
    def wrap(f):
        return f
    return wrap

def f2(f):
    return f

@f1(arg)
@f2
def func(): pass
```

```yaml
name: TestDecoratorCall
relation:
    type: Call
    items:
    - from: Module:'test_decorator_call'
      to: Function:'test_decorator_call.f2'
      loc: '10:1'
    - from: Module:'test_decorator_call'
      to: Function:'test_decorator_call.f1'
      loc: '9:1'
```

### Properties

| Name | Description | Type | Default |
|---|---|:---:|:---:|