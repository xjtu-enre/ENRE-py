# E: Module-$tf=test_function@


class ClassA:
    # E: Class-$CA=test_function.ClassA@ClassA
    # D: Define-$tf->$CA@ClassA
    x: int
    # E: Class Attribute-$CAx=test_function.ClassA.x@x
    # D: Define-$CA->$CAx@x

    def method(self):
        # E: Function-$CAm=test_function.ClassA.method@def
        # D: Define-$CA->$CAm@def
        ...


class ClassB:
    # E: Class-$CB=test_function.ClassB@Class
    # D: Define-$tf->$CB@ClassB

    def method(self):
        # E: Function-$CBm=test_function.ClassB.method@def
        # D: Define-$CB->$CBm@def
        ...


def func1(x):
    # E: Function-$func1=test_function.func1@func1
    # E: Parameter-$f1_x=test_function.func1.x@x)
    # D: Define-$tf->$func1@func1

    return 0


def func():
    # E: Function-$func=test_function.func@func():
    # D: Define-$tf->$func1@func

    x = 0
    # E: Variable-$f_x=test_function.func.x@x =
    # D: Define-$func->$f_x@x
    func1(x)
    # D: Call-$func->$func1@func1

    instance = ClassA()
    # E: Variable-$CAi=test_function.func.instance@instance
    # D: Define-$func->$CAi@instance
    instance.method()
    # D: Define-$func->$CAm@method
    def inner():
        # E: Function-$inner=test_function.func.inner@inner
        # D: Define-$func->$inner@def
        def inner_inner():
            # E: Function-$inner_inner=test_function.func.inner_inner@inner_inner
            # D: Define-$func->$inner_inner@def
            func1(x)
            # D: Call-$inner_inner->$func1@func1
            # D: Use-$inner->f_x@func1

        func1(x)
        # D: Call-$inner->$func1@func1
        # D: Use-$inner->f_x@func1
        inner_inner()
        # D: Call-$inner->$inner_inner@inner_inner

    inner()
    # D: Call-$func->$inner@inner

