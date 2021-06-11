from itertools import islice


def next_n(it, n):
    return next(islice(it, n, None))
