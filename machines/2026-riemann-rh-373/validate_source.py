#!/usr/bin/env python3
"""Exact small-n checks of the optimized source, including the register
invariants that the in-place additions rely on.

The source reloads `j` and `k` with `j = j + lcm` / `k = k + x` (no clearing
transfer) and never re-initializes `l`; this is only correct because

  - `j` and `k` are exactly exhausted by the countdown loop (`lcm >= x`),
  - `builtin_halt_if_gt_destroy(l, c)` leaves its left argument zero on
    every non-halting exit, and `l` starts at zero,

so all three registers are provably zero at their reload points.  This model
executes the program exactly (big integers, monus semantics, and the destroy
gadget's register effects) and asserts those invariants each iteration.
"""
from fractions import Fraction
from math import factorial, gcd

x = lcm = l = denom = i = c = j = k = 0
lcm = 1
q_ref = 1
H = Fraction(0)
for n in range(1, 10):
    x += 1
    c = lcm
    while lcm % x:
        lcm += c
    q_ref = q_ref * n // gcd(q_ref, n)
    assert lcm == q_ref

    assert l == 0, 'l invariant broken'
    assert j == 0, 'j invariant broken'
    assert k == 0, 'k invariant broken'
    i = 1
    denom = 1
    j = j + lcm
    k = k + x
    while j > 0:
        j -= 1
        c = c * i
        l = l * i + denom
        if k > 0:
            k -= 1
            c = l
        denom = denom * i
        i += 1

    D = factorial(lcm)
    Hq = sum(Fraction(1, t) for t in range(1, lcm + 1))
    H += Fraction(1, n)
    assert denom == D
    assert Fraction(l, D) == Hq
    assert Fraction(c, D) == H

    l = max(l - denom * x, 0)
    c = c * c
    l = l * denom
    c = c * c
    c = c * x
    l = l * l
    assert Fraction(l, D ** 4) == max(Hq - n, 0) ** 2
    assert Fraction(c, D ** 4) == n * H ** 4
    assert not l > c, f'machine would halt at n={n}'

    # builtin_halt_if_gt_destroy(l, c): non-halting register effects
    if c > l:
        l, c = 0, c - l - 1
    else:
        l, c = 0, 0

print('optimized recurrence, invariants, and comparison: exact checks passed for n=1..9')
