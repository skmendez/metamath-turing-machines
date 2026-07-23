#!/usr/bin/env python3
"""Exact small-n checks of the optimized source invariants."""
from fractions import Fraction
from math import factorial, gcd

q = 1
for n in range(1, 11):
    q = q * n // gcd(q, n)

    # Execute the optimized integer recurrence.
    i = 1
    denom = 1
    l = 0
    c = 0
    while i <= q:
        c *= i
        l = l * i + denom
        if i <= n:
            c = l
        denom *= i
        i += 1

    D = factorial(q)
    Hq = sum((Fraction(1, k) for k in range(1, q + 1)), Fraction())
    Hn = sum((Fraction(1, k) for k in range(1, n + 1)), Fraction())
    assert denom == D
    assert Fraction(l, D) == Hq
    assert Fraction(c, D) == Hn

    lhs = max(l - D * n, 0)
    lhs = (lhs * D) ** 2
    rhs = n * (c ** 4)
    assert (lhs > rhs) == ((max(Hq - n, 0) ** 2) > n * Hn**4)

print("optimized recurrence and comparison: exact checks passed for n=1..10")
