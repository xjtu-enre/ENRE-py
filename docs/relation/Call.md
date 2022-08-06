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
    dest: test_global_function_call.func1
    loc: '2:4'
    src: test_global_function_call
  - type: Call
    dest: test_global_function_call.func1
    loc: '5:4'
    src: test_global_function_call.func1
  - type: Call
    dest: test_global_function_call.func1
    loc: '10:0'
    src: test_global_function_call
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
    dest: test_method_call.ClassA
    loc: '2:6'
    src: test_method_call
  - type: Define
    dest: test_method_call.ClassA.method
    loc: '5:4'
    src: test_method_call.ClassA
  - type: Define
    dest: test_method_call.ClassB
    loc: '9:6'
    src: test_method_call
  - type: Define
    dest: test_method_call.ClassB.method
    loc: '12:4'
    src: test_method_call.ClassB
  - type: Define
    dest: test_method_call.instance
    loc: '16:0'
    src: test_method_call
  - type: Call
    dest: test_method_call.ClassA.method
    loc: '19:9'
    src: test_method_call
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
    dest: test_nested_define.func
    loc: '2:4'
    src: test_nested_define
  - type: Define
    dest: test_nested_define.func.inner
    loc: '5:4'
    src: test_nested_define.func
  - type: Define
    dest: test_nested_define.func.inner_inner
    loc: '8:8'
    src: test_nested_define.func
  - type: Call
    dest: test_nested_define.func
    loc: '11:12'
    src: test_nested_define.func.inner_inner
  - type: Call
    dest: test_nested_define.func
    loc: '13:8'
    src: test_nested_define.func.inner
  - type: Call
    dest: test_nested_define.func.inner_inner
    loc: '16:8'
    src: test_nested_define.func.inner
  - type: Call
    dest: test_nested_define.func.inner
    loc: '18:4'
    src: test_nested_define.func
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
    - dest: test_first_order_func_call.f
      src: test_first_order_func_call.acceptor
      loc: '5:4'
    - dest: test_first_order_func_call.foo
      src: test_first_order_func_call.acceptor
      loc: '5:4'
    - dest: test_first_order_func_call.acceptor
      src: test_first_order_func_call
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
    - dest: test_first_order_class_call.Base
      src: test_first_order_class_call
      loc: '4:7'
    - dest: test_first_order_class_call.create_class
      src: test_first_order_class_call
      loc: '12:6'
    - dest: test_first_order_class_call.cls
      src: test_first_order_class_call
      loc: '14:16'
    - dest: test_first_order_class_call.create_class.Difficult.test
      src: test_first_order_class_call
      loc: '16:14'
    - dest: test_first_order_class_call.create_class.Difficult
      src: test_first_order_class_call.create_class
      type: Define
      loc: '7:4'
```

