def f(p):
    pass

bad = 3
result = 0

a = bad     # source
f(a)        # barrier
result = a  # sink

a = bad     # source
result = a  # sink