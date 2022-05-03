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

global_var = 1
# E: Variable-$global_var=test_variable.global_var@global_var
# D: Define-$tv->$global_var@global_var


def func(p1, p2):
    # E: Function-$f=test_variable.func@def func
    # E: Parameter-$p1=test_variable.func.p1@p1
    # E: Parameter-$p2=test_variable.func.p2@p2
    # D: Define-$tv->$f@def func
    # D: Define-$f->$p1@p1
    # D: Define-$f->$p2@p2
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

    if p1 > p2:
        x = x - 1
        # D: Use-$f->$x1@x - 1
        # D: Set-$f->$x1@x =

    for a, b in p1:
        # E: Variable-$a=test_variable.func.a@a, b
        # E: Variable-$b=test_variable.func.b@b in
        # E: Use-$f->$p1@p1
        func(a, b)
        # D: Call-$f->$f@func
        # D: Use-$f->$a@a
        # D: Use-$f->$b@b

        func(t1, global_var)
        # D: Call-$f->$f@func
        # D: Use-$f->$ft1@t1
        # D: Use-$f->$global_var@global_var


