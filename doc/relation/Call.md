# Relation: Call

## Supported Pattern
```yaml
name: Call
```
### Examples

- Global Function Call
```python
// test_global_function_call.py
def func1():
    func1()
    return 0

func1()

```

```yaml
name: GlobalFunctionCall
relation:
  exact: false
  items:
  - category: Define
    dest: test_global_function_call.func1
    src: test_global_function_call
    r:
        s:o/Concept
  - category: Call
    dest: test_global_function_call.func1
    src: test_global_function_call.func1
    r:
        s:.
  - category: Call
    dest: test_global_function_call.func1
    src: test_global_function_call
    r:
        s:.
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
  - category: Define
    dest: test_method_call.ClassA
    src: test_method_call
    r:
        s:o/Concept
  - category: Define
    dest: test_method_call.ClassA.method
    src: test_method_call.ClassA
    r:
        s:o/Concept
  - category: Define
    dest: test_method_call.ClassB
    src: test_method_call
    r:
        s:o/Concept
  - category: Define
    dest: test_method_call.ClassB.method
    src: test_method_call.ClassB
    r:
        s:o/Concept
  - category: Define
    dest: test_method_call.instance
    src: test_method_call
    r:
        s:.
  - category: Call
    dest: test_method_call.ClassA.method
    src: test_method_call
    r:
        s:.
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
name: LocalFunctionCall
relation:
  exact: false
  items:
  - category: Define
    dest: test_local_call.func
    src: test_local_call
    r:
        s:o/Concept
  - category: Define
    dest: test_local_call.func.inner
    src: test_local_call.func
    r:
        s:o/Concept
  - category: Define
    dest: test_local_call.func.inner.inner_inner
    src: test_local_call.func
    r:
        s:o/Concept
  - category: Call
    dest: test_local_call.func
    src: test_local_call.func.inner.inner_inner
    r:
        s:.
  - category: Call
    dest: test_local_call.func
    src: test_local_call.func.inner
    r:
        s:.
  - category: Call
    dest: test_local_call.func.inner.inner_inner
    src: test_local_call.func.inner
    r:
        s:x
  - category: Call
    dest: test_local_call.func.inner
    src: test_local_call.func
    r:
        s:.
```

- First Order Function Call
``` python
// test_first_order_func_call.py
def acceptor(f):
    f()
```

```yaml
name: FirstOrderFunctionCall
relation:
    exact: False
    filter: Call
    items:
    - dest: test_first_order_func_call.f
      src: test_first_order_func_call.acceptor
      r:
        s:x

```
