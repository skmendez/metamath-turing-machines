# Lean 4 formalization (partial) of the 370-state Riemann machine

A Lean 4 project (core Lean only, no Mathlib; `lean-toolchain` pins v4.33.0)
giving machine-checked statements about `machines/2026-riemann-rh-370`.

    cd lean && lake build

## What is proved

* `RH/TM.lean` - semantics of binary one-tape Turing machines (`TM`, `Cfg`,
  `step`, `run`, `Halted`, `HaltsFrom`) with basic lemmas (`run_add`,
  `run_halted`).
* `RH/RH370.lean` - the 370-state transition table imported verbatim from
  `riemann.tm` (state `i` is line `i`), and
  `theorem no_halt_200000 : ¬ TM.Halted (M.run 200000 start)`: the machine has
  not halted after 200000 steps (`native_decide`).
* `RH/RH370Flip.lean` - the comparison-flipped variant of the same source
  (`riemann_flip.nql`, the halt builtin's arguments swapped, which must halt
  at the first check), imported the same way, with
  `theorem halts : TM.HaltsFrom M start` (it halts within 30000 steps).  This
  is an end-to-end, kernel-checked confirmation that the compiled artifact
  behaves as the big-integer model predicts at the one point where behaviour
  is observable in bounded time.

## What is NOT proved

The theorem one actually wants -

    HaltsFrom M start  <->  exists n >= 1, max(H_lcm(1..n) - n, 0)^2 > n * H_n^4

- is not formalized here. It needs (A) a refinement proof that the transition
table implements the register program (a simulation relation between tape
configurations and register states, per-gadget lemmas for the dispatcher,
register increment/decrement microcode and jumps), and (B) the loop-invariant
proof that the register program computes the criterion. Both are ordinary
but large formalization tasks; nothing in this directory should be cited as
a verification of the machine's correctness. The bounded theorems above are
exactly what they say and no more.

`native_decide` trusts the Lean compiler; replacing it with `decide` for the
bounded runs would remove that trust assumption at the cost of much longer
checking times.
