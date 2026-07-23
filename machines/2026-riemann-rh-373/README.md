# Experimental 373-state Riemann-hypothesis machine

This directory contains an exact 373-state, two-symbol, one-tape Turing-machine
candidate that starts on a blank tape and halts exactly when it finds an
integer `n >= 1` violating

    max(H_lcm(1..n) - n, 0)^2 <= n H_n^4.

The NQL source is **identical** to the neighbouring 392-state machine's;
every state saved here comes from two new compiler passes plus a much deeper
layout search. `PROOF.md` (unchanged) proves the criterion equivalent to the
Riemann hypothesis; `verify_small_n.py` certifies unconditionally that no
`n <= 400` can fire the halt condition.

## Build

Requires Python 3 and `pyparsing`.

    python3 build.py

The build asserts 373 reachable states and writes `riemann-rh-373.tm`.

Expected SHA-256:

    9955e684334fc4933f58bb28bb17ddadfa861fd2794075f029b863bd0ab52873

## Compiler passes (new relative to the 392 machine's compiler)

1. **Copy-idiom unification.** Reading a register emits
   `transfer(reg -> target, save); transfer(save -> reg)`. Previously `save`
   was whatever scratch register the allocator handed out, so textually
   identical copy sites compiled to *different* transfer subroutines and the
   dispatcher could not share them. A dedicated `_copysave` register (zero
   before and after every copy by construction, also used by the in-place
   squaring path) makes every copy of a given source/target pair emit the
   same two memoized subroutines. Baseline effect on this machine:
   416 -> 410 states before any layout search, and one scratch register
   freed (11 registers total, still 16 after power-of-two rounding).

2. **Layout optimization pass** (`compiler/layoutopt.py`). The dispatcher is
   a binary tree over program-counter bits whose subtrees merge whenever two
   aligned power-of-two blocks of the instruction stream are identical, so
   one-slot no-ops that re-phase repeated fragments can collapse whole
   subtrees. The objective is a global function of all offsets, so the pass
   searches: parse once and pin `pc_bits`, making one exact build+compress
   trial ~6 ms (no need for native code); then exhaustive singles ->
   exhaustive pairs (~11k trials) -> greedy extension -> simulated annealing
   with fixed-seed restarts, proposing only decrement-safe positions. On
   this machine it found 55 no-ops at 41 indices (many absorbed by alignment
   padding that would exist anyway), taking 410 -> 373 states. The old
   hand-greedy approach on the same compiler had stalled at 386.

3. **Canonical jump selection** (`framework.JUMP_CANONICAL`, off by
   default). Chooses one `(order, rel)` encoding per goto by greedy set
   cover to minimize distinct jump gadgets. Implemented and tested honestly:
   on this machine it *loses* ~2 states after layout search (the layout
   search interacts better with the default largest-required-jump
   heuristic), so it ships disabled — kept because it may help other
   programs.

State-count lineage for this construction: 744 (2016 email machine) -> 476
-> 419 -> 392 -> **373**.

## Validation

    python3 validate_source.py
    python3 validate_compiler.py
    python3 verify_small_n.py
    python3 build.py
    python3 validate_layout.py

Checks performed when this machine was added:

1. **Reproducibility.** Deterministic rebuild verified against the SHA-256
   above; 373 reachable states at `pc_bits = 9` (no-op-free build: 410).
2. **Source semantics.** Unchanged source; `validate_source.py` re-runs the
   exact big-integer model (monus semantics, destroy-gadget register
   effects, all zero-invariants) for `n = 1..9`.
3. **Compiler.** `validate_compiler.py` extends the inherited suite with a
   copy-save stress test (interleaved copies in compound expressions); the
   dedicated save register is zero before and after every copy by
   construction (the two transfers fill and then drain it, with no emission
   in between).
4. **Layout.** `validate_layout.py` re-checks that no inserted no-op
   follows a decrement instruction and that the machine is
   register-operation trace-equivalent to the no-op-free build over
   millions of steps (11,651 operations compared). A comparison-flipped
   variant halts with identical 219-operation traces under both layouts.

As with its predecessors, this is careful machine-level validation, not a
formal proof; proof-assistant formalization is still required before
treating `BB(373)` as an established bound.
