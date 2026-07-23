# Why the cutoff `x > 253` can be removed

Let

- `q(n) = lcm(1, ..., n)`,
- `psi(n) = log q(n)`, Chebyshev's second function,
- `H_m = 1 + 1/2 + ... + 1/m`,
- `R_n = max(H_{q(n)} - n, 0)`.

The optimized program halts exactly when

    R_n^2 > n H_n^4

for some `n >= 1`.

The proof uses two results stated by Yuri Matiyasevich in *The Riemann
Hypothesis in Computer Science* (2018), equations (10) and (11):

1. RH implies, for every integer `n > 1`,

       psi(n) - n < (1/25) sqrt(n) log(n)^2.

2. If there is a constant `C` such that, for every sufficiently large `n`,

       psi(n) - n < C sqrt(n) log(n)^2,

   then RH holds.

The paper derives the first statement from Schoenfeld's conditional estimate
and the second from the standard Omega-plus/minus theorem for `psi(x)-x`.

We also use the elementary harmonic-number bounds

    log m < H_m <= 1 + log m.

## RH implies that the machine never halts

For `n >= 3`,

    H_{q(n)} - n
      <= 1 + log q(n) - n
       = 1 + psi(n) - n
       < 1 + (1/25) sqrt(n) log(n)^2.

The function `sqrt(n) log(n)^2` is increasing for `n > 1`, and at `n = 3`

    (24/25) sqrt(3) log(3)^2 > 1.

Consequently, for every `n >= 3`,

    1 + (1/25) sqrt(n) log(n)^2
      < sqrt(n) log(n)^2
      < sqrt(n) H_n^2.

Taking the positive part and squaring gives

    R_n^2 < n H_n^4.

The two remaining cases are immediate:

- `n = 1`: `q(1)=1`, so `R_1=0`;
- `n = 2`: `q(2)=2` and `H_2=3/2<2`, so `R_2=0`.

Thus RH implies that no tested integer makes the machine halt.

## If the machine never halts, then RH holds

Suppose

    R_n <= sqrt(n) H_n^2

for every `n >= 1`.

Because `psi(n)=log q(n)<H_{q(n)}`:

- when `H_{q(n)} <= n`, we have `psi(n)-n<0`;
- when `H_{q(n)} > n`, we have

      psi(n)-n < H_{q(n)}-n = R_n <= sqrt(n) H_n^2.

Therefore, for all `n`,

    psi(n)-n < sqrt(n) H_n^2
               <= sqrt(n) (1+log n)^2.

For `n >= 3`, `1+log n <= 2 log n`, hence

    psi(n)-n < 4 sqrt(n) log(n)^2.

This is Matiyasevich's sufficient condition with `C=4`, so RH follows.

Therefore

    RH  <=>  for every n >= 1, R_n^2 <= n H_n^4,

and the `x > 253` guard is unnecessary.

## Source-level invariant

At the end of the inner loop, with `D=q(n)!`, the optimized program has

    denom = D,
    l     = D H_{q(n)},
    c     = D H_n.

NQL subtraction is monus, so after `l = l - denom*x`,

    l = D max(H_{q(n)}-n, 0).

The final operations turn the two comparison registers into

    l = D^4 R_n^2,
    c = n D^4 H_n^4.

The common positive factor `D^4` cancels, giving exactly the criterion above.

## References

- Yuri Matiyasevich, *The Riemann Hypothesis in Computer Science*, CDMTCS-527, 2018.
  https://www.cs.auckland.ac.nz/research/groups/CDMTCS/researchreports/download.php?selected-id=692
- Lowell Schoenfeld, *Sharper Bounds for the Chebyshev Functions theta(x) and psi(x). II*, Mathematics of Computation 30 (1976), 337-360.
  https://doi.org/10.2307/2005976
- Original 744-state NQL source:
  https://github.com/sorear/metamath-turing-machines/blob/master/machines/2016-riemann-matiyasevich-aaronson-744/riemann.nql
