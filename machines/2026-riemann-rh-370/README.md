# Experimental 370-state Riemann-hypothesis machine

This directory contains an exact 370-state, two-symbol, one-tape Turing-machine
candidate that starts on a blank tape and halts exactly when it finds an
integer `n >= 1` violating

    max(H_lcm(1..n) - n, 0)^2 <= n H_n^4.

The NQL source is identical to the 392- and 373-state machines'; `PROOF.md`
(unchanged) proves the criterion equivalent to the Riemann hypothesis, and
`verify_small_n.py` certifies unconditionally that no `n <= 400` fires.

## Build

Requires Python 3 and `pyparsing`.

    python3 build.py

The build asserts 370 reachable states and writes `riemann-rh-370.tm`.

Expected SHA-256:

    feb11876cb0e75c3e246f4e54efd0bfc44246a2bdc8d38477e58c62adce88594

## Compiler changes relative to the 373 machine

Both changes came out of hand-inspecting the machine's largest state
consumers (main dispatch tree 223 states, transfer-subroutine internals 88)
and were then folded into the compiler:

1. **Canonical temp allocation.** The scratch allocator handed out free
   temps LIFO, so identical operations at different sites could grab
   different scratch registers and emit differently-named transfer
   subroutines (e.g. `transfer(_Gdenom,_copysave,_scratch_1)` at one site
   and `..._scratch_2` at another). `get_temp` now always returns the
   lowest-numbered free scratch.
2. **Divisor-first temp acquisition** in the divisibility peephole, so the
   divisor reload uses the same scratch register as multiply-addend sites.

Neither change moves the no-layout baseline (compress() was already merging
the duplicated *states*), but both make the emitted part stream more
uniform, which makes it more *searchable*: the layout pass's greedy stage
lands at 385 instead of 392, and annealing reaches 370 instead of 373.

Negative results, measured and documented for posterity:

- **pc_bits = 8 is a net loss.** One PC bit costs only ~23-29 states
  (measured by padding the same machine across a power-of-two boundary),
  but reaching 256 slots requires inlining transfers, which loses ~100
  states of subroutine-internal sharing (416 -> 482 at equal pc_bits).
  The slot floor for this algorithm with fully inlined emission is ~296.
- **Hoisting repeated statements into procedure subroutines** (e.g. a
  shared `sq(r)` for the squarings) does produce real dispatch-tree sharing
  (~25 states' worth), but nested subroutines pay their own internal
  power-of-two alignment padding, inflating main past 512 slots and costing
  the pc_bits=10 penalty; net +34.

## Validation

    python3 validate_source.py
    python3 validate_compiler.py
    python3 verify_small_n.py
    python3 build.py
    python3 validate_layout.py

Checks performed when this machine was added: deterministic rebuild against
the SHA-256 above (370 states at `pc_bits = 9`; no-op-free build: 409);
exact big-integer model of the unchanged source for `n = 1..9` with all
zero-invariants asserted; the inherited compiler test suite (arithmetic,
40 divisibility cases, destructive comparison, decrement fusion, countdown
loops, copy-save stress); all 56 layout no-ops verified decrement-safe and
the machine register-operation trace-equivalent to the no-op-free build
(11,507 operations); a comparison-flipped variant halts with identical
211-operation traces under both layouts.

State-count lineage: 744 -> 476 -> 419 -> 392 -> 373 -> **370**.

As with its predecessors, this is careful machine-level validation, not a
formal proof; proof-assistant formalization is still required before
treating `BB(370)` as an established bound.
