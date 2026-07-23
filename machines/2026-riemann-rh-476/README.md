# 476-state Riemann-hypothesis machine (experimental)

This bundle contains an experimental reduction of the published 744-state NQL
machine. The generated binary, one-tape Turing machine halts exactly when the
optimized NQL program finds an integer `x > 253` violating

    (H_lcm(1..x) - x)^2 <= x H_x^4.

## Build

Requires Python 3 and `pyparsing`.

    python build.py

The builder asserts that the compressed machine has exactly 476 reachable
non-halting states, then writes `riemann-rh-476.tm`.

## What changed

Source-level:

1. Scan LCM candidates in steps of the previous LCM, requiring only one
   divisibility test.
2. Compute `H_x` and `H_L` in one loop with a shared factorial denominator.
3. Compare `(D^2(H_L-x))^2` with `x(D H_x)^4`, removing one multiplication.
4. Reuse six global registers and remove dead initialization.

Compiler-level:

1. Direct in-place lowering for augmented addition and monus subtraction.
2. Destructive lowering for `x=x*y`, `x=x*x`, and `x=x*y+z`.
3. Direct remainder-zero lowering for `a != (a / b) * b`.
4. A destructive terminal `lhs > rhs` comparison exposed as
   `builtin_halt_if_gt_destroy`.
5. Eleven one-instruction alignment no-ops selected to improve BDD sharing.

## Validation status

The transition table is exact and reproducible from the included compiler.
The compiler peepholes were exercised on small arithmetic cases, all 40 pairs
`1 <= a <= 8`, `1 <= b <= 5` for the divisibility primitive, and true/equal/
false cases of the destructive terminal comparison.

This is not a formal proof or an independently reviewed submission. In
particular, the whole-machine equivalence to the published construction should
be reviewed and ideally formalized before treating `BB(476)` as an established
literature bound.

## Independent validation (2026-07-23)

The following checks were performed when this bundle was applied to the
repository:

1. **Reproducibility.** `python3 build.py` regenerates `riemann-rh-476.tm`
   bit-for-bit (SHA-256 `6f922bd2...`) with exactly 476 reachable
   non-halting states.
2. **Source equivalence.** The NQL program was checked symbolically against
   `machines/2016-riemann-matiyasevich-aaronson-744/riemann.nql`. With
   `D = lcm(1..x)!`, the inner loop computes `l = D*H_lcm`, `denom = D`, and
   `c = D*H_x` (for `i <= x` the register tracks the harmonic numerator; the
   remaining iterations multiply it up to the shared denominator). The final
   comparison `(D^2 * (l monus denom*x))^2 > x * (D*H_x)^4` reduces to
   `max(H_lcm - x, 0)^2 > x * H_x^4`, identical to the published machine's
   `a*d > b*c` test, including natural-subtraction (monus) semantics, and the
   check fires exactly for `x > 253` via the countdown register.
3. **Compiler peepholes.** The compiler diff against the repository compiler
   was audited against the `dec`-skip branch convention (PC+2 on successful
   decrement, PC+1 on zero), and `validate_compiler.py` passes: arithmetic
   identities, all 40 divisibility cases, and the true/equal/false cases of
   `builtin_halt_if_gt_destroy`. An end-to-end miniature of this program
   (threshold 1, comparison flipped so it halts) was compiled and simulated
   as a raw Turing machine; it halts at `x = 2` with register contents
   matching a big-integer model.
4. **Layout no-ops.** `MAIN_INSERT_NOPS` is *not* safe at arbitrary indices:
   inserting a no-op immediately after a decrement instruction separates the
   decrement from its skip target and corrupts the control flow (confirmed
   experimentally). All eleven indices used here were verified statically to
   not follow a decrement, and the built machine was compared against a
   no-nops build of the same source: the register-operation traces are
   identical over 8 million simulated steps (the no-nops build has 514
   states, so the no-ops save 38 states of dispatcher sharing).

Caveat: anyone tuning `LAYOUT_NOPS` must re-run the safety check that no
inserted no-op immediately follows a `reg_decr` part.
