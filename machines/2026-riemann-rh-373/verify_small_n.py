#!/usr/bin/env python3
"""Certified check that the halt condition fires for no n <= 400.

The machine halts iff some n satisfies R_n^2 > n * H_n^4 with
R_n = max(H_q(n) - n, 0) and q(n) = lcm(1..n).  PROOF.md handles n >= 3
conditionally on RH; this script proves *unconditionally* that no n <= 400
can fire, which makes the machine equi-halting with the historical
n > 253 formulation (any violation must have n > 400 > 253).

Method: q(n) and H_n are exact; H_q(n) is bounded above by the
Euler-Maclaurin enclosure H_m < ln m + gamma + 1/(2m), with ln computed by
Decimal (correctly rounded at 80 digits) plus 10^-60 one-sided slack, and
gamma replaced by a 50-digit upper bound.  All comparisons against the
exact rational n * H_n^4 are then one-sided and rigorous.
"""
from decimal import Decimal, getcontext
from fractions import Fraction
from math import gcd

LIMIT = 400
getcontext().prec = 80
GAMMA_HI = Decimal('0.57721566490153286060651209008240243104215933593994')
SLACK = Decimal(10) ** -60

q = 1
H = Fraction(0)
worst = None
for n in range(1, LIMIT + 1):
    q = q * n // gcd(q, n)
    H += Fraction(1, n)
    Hq_hi = Decimal(q).ln() + SLACK + GAMMA_HI + Decimal(1) / (2 * q)
    R_hi = Hq_hi - n
    if R_hi <= 0:
        continue
    lhs_hi = Fraction(str(R_hi)) ** 2
    rhs = n * H ** 4
    assert lhs_hi < rhs, f'halt condition may fire at n={n}'
    ratio = lhs_hi / rhs
    if worst is None or ratio > worst[1]:
        worst = (n, ratio)

print(f'certified: halt condition fires for no n <= {LIMIT}')
print('worst certified R^2 / (n*H^4): %.3e at n=%d (fires only if > 1)'
      % (float(worst[1]), worst[0]))
