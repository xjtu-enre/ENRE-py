
class A:
    def __init__(self) -> None:
        self.x = 1

    def foo(self) -> None:
        self.not_exist = 1
        pass

    def method(self):
        pass

class B:
    def __init__(self) -> None:
        self.x = 2
        self.foo()

    def foo(self) -> None:
        pass

    @property
    def rand(self) -> int:
        nested_function.out_fun()
        print_A_x()
        return random.randint(0, 100)


def print_A_x(a):
    a = A()
    print()
    a.method()
    if True:
        a = A()
        a.x = 1
    else:
        a = B()
    a.foo()
    b = a
    b.foo()
    raise MyException()


def loop_fun(l):
    a = B()
    for a in l:
        a = A()
    a.foo()
