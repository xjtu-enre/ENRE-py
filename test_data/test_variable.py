# E: Module-$tv=test_variable@

x = 1
# E: Variable-$x=test_variable.x@x
# D: Define-$tv->$x@x

y: int = 1
# E: Variable-$y=test_variable.y@y
# D: Define-$tv->$y@y


t1, t2 = 1, 2
# E: Variable-$t1=test_variable.t1@t1
# E: Variable-$t2=test_variable.t2@t2
# D: Define-$tv->$t1@t1
# D: Define-$tv->$t2@t2

(t3 := 1)
# E: Variable-$t3=test_variable.t3@t3
# D: Define-$tv->$t3@t3

def func():
    # E: Function-$f=test_variable.func@def func
    # D: Define-$tv->$f@def func
    x = 1
    # E: Variable-$x1=test_variable.func.x@x
    # D: Define-$f->$x1@x

    y: int = 1
    # E: Variable-$y1=test_variable.func.y@y
    # D: Define-$f->$y@y

    t1, t2 = 1, 2
    # E: Variable-$ft1=test_variable.func.t1@t1
    # E: Variable-$ft2=test_variable.func.t2@t2
    # D: Define-$f->$ft1@t1
    # D: Define-$f->$ft2@t2

    (t3 := 1)
    # E: Variable-$ft3=test_variable.func.t3@t3
    # D: Define-$f->$ft3@t3


