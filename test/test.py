def func3(x, *y, **z):
    ...


def bar():
    ...


def foo():
    ...


def identity(x):
    return x


if ...:
    f1 = identity(identity(identity(foo)))
else:
    def f1():
        ...

f1()


def create_class():
    class Difficult:
        def test(self):
            ...

    return Difficult


cls = create_class()

difficult_obj = cls()

difficult_obj.test()


class A():
    def test(self):
        ...


a = A()

a.test()
