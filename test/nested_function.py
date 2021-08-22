out_var = 1
def out_fun():
    def inner_fun():
        print(out_var)
        inner_fun()

    if False:
        out_var = 2
    else:
        out_var = 3

    inner_fun()

out_fun()
