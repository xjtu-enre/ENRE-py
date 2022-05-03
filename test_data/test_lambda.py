# E: Module-$tl=test_lambda@

l = []
# E: Variable-$l=test_lambda.l@l
# D: Define-$tl->$l@l

l1 = lambda a: [y + 1 for y in l]
# E: AnonymousFunction-$anonymous1=test_lambda.($line)@lambda
# E: Variable-$l1=test_lambda.l1@l1
# E: Lambda Parameter-$pa=test_lambda.($line).a@a:
# E: Variable-$y=test_lambda.($line).y@y in
# D: Define-$tl->$l1@l1
# D: Define-$anonymous1->$pa@a:
# D: Define-$anonymous1->$y@y in
# D: Use-$anonymous1->$y@y + 1

l2 = lambda a: {y + 1 for y in l}
# E: AnonymousFunction-$anonymous2=test_lambda.($line)@lambda
# E: Variable-$l2=test_lambda.l2@l2
# E: Lambda Parameter-$pa=test_lambda.($line).a@a:
# E: Variable-$y=test_lambda.($line).y@y in
# D: Define-$tl->$l2@l1
# D: Define-$anonymous2->$pa@a:
# D: Define-$anonymous2->$y@y in
# D: Use-$anonymous2->$y@y + 1

l3 = lambda a: (y + 1 for y in l)
# E: AnonymousFunction-$anonymous3=test_lambda.($line)@lambda
# E: Variable-$l3=test_lambda.l3@l3
# E: Lambda Parameter-$pa=test_lambda.($line).a@a:
# E: Variable-$y=test_lambda.($line).y@y in
# D: Define-$tl->$l1@l1
# D: Define-$anonymous3->$pa@a:
# D: Define-$anonymous3->$y@y in
# D: Use-$anonymous3->$y@y + 1

def wrapper():
    # E: Function-$wrapper=test_lambda.wrapper@wrapper
    # D: Define-$tl->$wrapper@wrapper

    and_one = l1(l)
    # E: Variable-$and_one=test_lambda.and_one@and_one
    # D: Define-$wrapper->$and_one@and_one
    # D: Call-$wrapper->$anonymous1@l1
    # D: Use-$wrapper->$l@l
