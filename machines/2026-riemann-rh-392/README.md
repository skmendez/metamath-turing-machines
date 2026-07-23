# Experimental 392-state Riemann-hypothesis machine

This directory contains an exact 392-state, two-symbol, one-tape Turing-machine
candidate that starts on a blank tape and halts exactly when it finds an
integer `n >= 1` violating

    max(H_lcm(1..n) - n, 0)^2 <= n H_n^4.

The criterion is identical to the neighbouring 419-state machine's; `PROOF.md`
(carried over unchanged) proves it equivalent to the Riemann hypothesis, and
`verify_small_n.py` certifies unconditionally that no `n <= 400` can fire the
halt condition.

## Build

Requires Python 3 and `pyparsing`.

    python3 build.py

The build asserts 392 reachable states and writes `riemann-rh-392.tm`.

Expected SHA-256:

    c413cb7e3b430575d3285e4fdb402363e929e096d993bb2f8db620dfa3f6b750

## Reduction from the 419-state machine

The dominant cost in the 419-state machine's program-counter space was its two
register-vs-register comparisons (`i <= lcm` and `i <= x`, roughly 40 PC slots
each), plus one clearing initialization. Three source-level changes remove
them:

1. **Countdown registers.** Two new globals `j` and `k` count `lcm` and `x`
   down, replacing both comparisons with compare-against-zero tests
   (~4 slots each). Both are provably zero at their reload points (they are
   exactly exhausted each outer iteration, using `lcm >= x`), so they reload
   with in-place additions `j = j + lcm` / `k = k + x` needing no clearing
   transfer.
2. **`l = 0` elimination.** The lcm-scan's step value moves from `l` to `c`
   (whose stale value is dead: it is overwritten at the first inner-loop
   iteration). `builtin_halt_if_gt_destroy(l, c)` leaves its left argument
   zero on every non-halting exit and `l` starts zero, so `l` is invariantly
   zero at the loop head and its initialization disappears.
3. **Generalized decrement fusion** (compiler): the peephole for
   `if (r > 0) { r = r - 1; }` is extended to allow trailing statements in
   the fused block, so `if (k > 0) { k = k - 1; c = l; }` lowers to a single
   decrement instead of a compare-restore-decrement triple. This is the only
   compiler change relative to the 419 machine's compiler (two lines in
   `nqlast.py`).

Together these shrink main from 549 to 485 raw PC slots — below 512 — so the
**program counter narrows from 10 bits to 9**, shrinking the dispatch
machinery. Without layout no-ops the machine has 416 states; four
one-instruction no-ops (found by greedy search over all decrement-safe
positions, see `build.py`) bring it to 392. An exhaustive-by-sampling search
over 4001 register allocation orders and 38 semantics-preserving statement
reorderings found no better baseline.

## Validation

    python3 validate_source.py
    python3 validate_compiler.py
    python3 verify_small_n.py
    python3 build.py

Checks performed when this machine was added:

1. **Reproducibility.** `build.py` regenerates `riemann-rh-392.tm`
   deterministically (SHA-256 above) with exactly 392 reachable states at
   `pc_bits = 9`; the no-op-free build has 416 states.
2. **Source semantics.** `validate_source.py` executes the program exactly
   (big integers, monus, and the destroy gadget's register effects) for
   `n = 1..9`, asserting the register invariants `denom = D`,
   `l = D*H_lcm`, `c = D*H_n`, the final comparison values, and the three
   zero-invariants (`l`, `j`, `k`) that the in-place reloads depend on.
3. **Compiler.** The compiler differs from the validated 419 compiler only
   in the generalized decrement fusion; `validate_compiler.py` extends the
   inherited suite (arithmetic, 40 divisibility cases, destructive
   comparison) with fused-if taken/not-taken/else cases and a countdown
   loop.
4. **Layout no-ops.** All four insertion indices were checked against the
   pre-insertion parts list: none follows a decrement instruction (whose
   success path skips one PC slot and would be corrupted). The 392-state
   machine's register-operation trace matches the 416-state no-op-free
   build over 8 million simulated steps, and a comparison-flipped variant
   of the source halts with byte-identical register-operation traces
   (211 operations) under both layouts, at exactly the point a big-integer
   model predicts.

As with the 419-state machine, this is careful machine-level validation, not
a formal proof; proof-assistant formalization is still required before
treating `BB(392)` as an established bound.
