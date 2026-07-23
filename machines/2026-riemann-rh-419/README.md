# Experimental 419-state Riemann-hypothesis machine

This directory contains an exact 419-state, two-symbol, one-tape Turing-machine
candidate that starts on a blank tape and halts exactly when it finds an integer
`n >= 1` violating

    max(H_lcm(1..n) - n, 0)^2 <= n H_n^4.

`PROOF.md` proves that this all-`n` condition is equivalent to the Riemann
hypothesis, using the necessary and sufficient one-sided Chebyshev-psi bounds
stated by Matiyasevich in 2018. In particular, the historical `n > 253` guard
is unnecessary.

## Build

Requires Python 3 and `pyparsing`.

    python3 build.py

The build asserts that all 419 emitted states are reachable and writes
`riemann-rh-419.tm`.

Expected SHA-256:

    fae60d8c7a0ea98d850c30b953af97c1bd2c398e5283da9bf193a75d39ce6c60

## Reduction from the 476-state candidate

1. Remove the initialization `i=253` and its countdown branch.
2. Test every `n >= 1`; see `PROOF.md` for equivalence.
3. Reorder independent initializations and arithmetic statements. This changes
   no register values but substantially changes BDD subtree sharing.
4. Insert six one-instruction semantic no-ops at the lowered-IR positions listed
   in `build.py`, again solely to improve BDD sharing.

The no-op-free version of this exact source has 439 states. The six alignment
no-ops reduce it to 419 states.

## Validation

    python3 validate_source.py
    python3 validate_compiler.py
    python3 build.py

These checks are useful but are not a formal verification of the compiler or
the whole transition table. Independent review or proof-assistant
formalization is still required before presenting `BB(419)` as an established
published bound.

## Independent validation (2026-07-23)

Performed when this bundle replaced the earlier 476-state candidate:

1. **Reproducibility.** `python3 build.py` regenerates `riemann-rh-419.tm`
   bit-for-bit (SHA-256 `fae60d8c...`) with exactly 419 reachable states,
   and the no-op-free build of the same source was confirmed to have 439.
2. **Compiler.** The `compiler/` tree is byte-identical to the one validated
   with the 476-state bundle (peephole audit against the decrement branch
   convention, micro tests, and an end-to-end miniature simulated against a
   big-integer model). `validate_compiler.py` passes.
3. **Source equivalence.** The statement reordering relative to the
   476-state source was checked symbolically (all reordered pairs are
   independent), and `validate_source.py` confirms the register invariants
   `denom = D`, `l = D*H_q(n)`, `c = D*H_n` exactly for `n = 1..10`.
4. **Layout no-ops.** All six `LAYOUT_NOPS` indices were verified statically
   to not follow a decrement instruction (the unsafe pattern that corrupts
   the decrement's skip target), and the 419-state machine's
   register-operation trace matches the 439-state no-op-free build over
   8 million simulated steps.
5. **PROOF.md against its sources.** Matiyasevich's CDMTCS-527 report was
   retrieved and inequalities (10) and (11) are quoted accurately,
   including their quantifier ranges: (10) is asserted for all `n > 1`
   (Schoenfeld's `1/(8 pi)` bound for `n >= 74`, direct verification for
   `n = 2..73`), and (11) requires only sufficiently large `n`, so `C = 4`
   qualifies. The elementary steps in between were checked numerically
   (e.g. `(24/25) sqrt(3) ln(3)^2 = 2.0069 > 1`).
6. **Unconditional small-`n` check.** `verify_small_n.py` proves with
   certified one-sided bounds (exact `lcm` and `H_n`, correctly-rounded
   80-digit logs, Euler-Maclaurin enclosure for `H_lcm`) that the halt
   condition fires for no `n <= 400`; the worst certified
   `R_n^2 / (n H_n^4)` is about `6e-3`. Notably `R_n > 0` for 149 of the
   first 400 values (e.g. `psi(283) - 283 = +7.72`), so the monus result is
   genuinely nonzero there — the guard-free machine really evaluates those
   comparisons, they just never fire. This makes the machine equi-halting,
   unconditionally, with the historical `n > 253` formulation used by the
   744-state machine.
