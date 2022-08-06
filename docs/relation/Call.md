## Relation: Call
Calling a callable object indicates a call dependency.

### Supported Patterns
```yaml
name: Call
```

#### Semantic: 

##### Examples

- Global Function Call
```python
// test_global_function_call.py

def func1():


    func1()


    return 0

func1()


```

```yaml
relation:
  items:
  - type: Define
    to: test_global_function_call.func1
    loc: '2:4'
    from: test_global_function_call
  - type: Call
    to: test_global_function_call.func1
    loc: '5:4'
    from: test_global_function_call.func1
  - type: Call
    to: test_global_function_call.func1
    loc: '10:0'
    from: test_global_function_call
```
- Class Method Call
```python
// test_method_call.py

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
relation:
  exact: false
  items:
  - type: Define
    to: test_method_call.ClassA
    loc: '2:6'
    from: test_method_call
  - type: Define
    to: test_method_call.ClassA.method
    loc: '5:4'
    from: test_method_call.ClassA
  - type: Define
    to: test_method_call.ClassB
    loc: '9:6'
    from: test_method_call
  - type: Define
    to: test_method_call.ClassB.method
    loc: '12:4'
    from: test_method_call.ClassB
  - type: Define
    to: test_method_call.instance
    loc: '16:0'
    from: test_method_call
  - type: Call
    to: test_method_call.ClassA.method
    loc: '19:9'
    from: test_method_call
```

- Local Function Call
```python
// test_local_call.py

def func():


    def inner():


        def inner_inner():


            func()

        func()


        inner_inner()

    inner()

```

```yaml
relation:
  exact: false
  items:
  - type: Define
    to: test_nested_define.func
    loc: '2:4'
    from: test_nested_define
  - type: Define
    to: test_nested_define.func.inner
    loc: '5:4'
    from: test_nested_define.func
  - type: Define
    to: test_nested_define.func.inner_inner
    loc: '8:8'
    from: test_nested_define.func
  - type: Call
    to: test_nested_define.func
    loc: '11:12'
    from: test_nested_define.func.inner_inner
  - type: Call
    to: test_nested_define.func
    loc: '13:8'
    from: test_nested_define.func.inner
  - type: Call
    to: test_nested_define.func.inner_inner
    loc: '16:8'
    from: test_nested_define.func.inner
  - type: Call
    to: test_nested_define.func.inner
    loc: '18:4'
    from: test_nested_define.func
```

- First Order Function Call
``` python
// test_first_order_func_call.py
def foo():
    ...

def acceptor(f):
    f()

acceptor(foo)
```

```yaml
name: FirstOrderFunctionCall
relation:
    exact: False
    filter: Call
    items:
    - to: test_first_order_func_call.f
      from: test_first_order_func_call.acceptor
      loc: '5:4'
    - to: test_first_order_func_call.foo
      from: test_first_order_func_call.acceptor
      loc: '5:4'
    - to: test_first_order_func_call.acceptor
      from: test_first_order_func_call
      loc: '7:0'
```

- First Order Function Call
``` python
// test_first_order_class_call.py
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
    filter: Call
    items:
    - to: test_first_order_class_call.Base
      from: test_first_order_class_call
      loc: '4:7'
    - to: test_first_order_class_call.create_class
      from: test_first_order_class_call
      loc: '12:6'
    - to: test_first_order_class_call.cls
      from: test_first_order_class_call
      loc: '14:16'
    - to: test_first_order_class_call.create_class.Difficult.test
      from: test_first_order_class_call
      loc: '16:14'
    - to: test_first_order_class_call.create_class.Difficult
      from: test_first_order_class_call.create_class
      type: Define
      loc: '7:4'
```

