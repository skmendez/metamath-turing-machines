# 370-state Riemann-hypothesis machine

A 370-state, two-symbol, one-tape Turing machine that, started on a blank
tape, halts if and only if the Riemann hypothesis is false. It tests, for
every integer `n >= 1`, the Matiyasevich criterion

    max(H_lcm(1..n) - n, 0)^2 <= n H_n^4

where `H_m` is the m-th harmonic number, and halts on a violation.

Relative to `2016-riemann-matiyasevich-aaronson-744` this machine

1. removes the `n > 253` guard - `PROOF.md` derives the equivalence of the
   guard-free criterion with RH from conditions (10) and (11) of
   Matiyasevich, *The Riemann Hypothesis in Computer Science* (CDMTCS-527,
   2018), and `verify_small_n.py` independently certifies with rigorous
   one-sided bounds that no `n <= 400` can fire the halt condition (so the
   guard-free machine is unconditionally equi-halting with the guarded
   formulation);
2. restructures the program (shared-denominator harmonic recurrence,
   countdown registers replacing register-register comparisons, in-place
   reloads justified by zero-invariants) so that main fits in 512
   program-counter slots, narrowing the PC to 9 bits;
3. opts into the compiler features `opt_destructive`, `opt_remainder_test`,
   `opt_dec_fusion`, `opt_copy_save`, `opt_canonical_temps`, the
   `builtin_halt_if_gt_destroy` terminal comparison, and 56 `layout`
   padding no-ops found by search (`misc/layoutopt.py`).

## Reproducing

    python3 compiler/nqlaconic.py --print-tm machines/2026-riemann-rh-370/riemann.nql

reproduces `riemann.tm` exactly (370 states); `--print-subs` reproduces
`riemann.subs`.

## Validation

    python3 machines/2026-riemann-rh-370/validate_source.py
    python3 machines/2026-riemann-rh-370/validate_compiler.py
    python3 machines/2026-riemann-rh-370/validate_layout.py
    python3 machines/2026-riemann-rh-370/verify_small_n.py

- `validate_source.py` executes the NQL program exactly on big integers for
  `n = 1..9` (monus semantics and the halt builtin's register effects
  included), asserting the harmonic invariants, the final comparison
  values, and the zero-invariants that the in-place reloads depend on.
- `validate_compiler.py` compiles and runs bounded test machines for every
  opted-into compiler feature.
- `validate_layout.py` checks the layout no-ops are behaviorally inert:
  the machine is register-operation trace-equivalent to a layout-free
  build, and a comparison-flipped (halting) variant halts with identical
  traces under both layouts. The compiler additionally rejects at build
  time any layout no-op placed directly after a decrement, whose
  skip-one-slot success path padding would corrupt.
- `verify_small_n.py` is the certified small-`n` computation described
  above.

This is machine-level validation, not formal verification: the equivalence
of the criterion with RH rests on the cited literature, and the compiler
and framework are tested rather than proven. Formalization (e.g. proving
"halts iff some n violates the criterion" in a proof assistant, in the
style of the bbchallenge Goldbach machine) is the natural next step before
treating `BB(370)` as an established bound.

Development history, including the intermediate 476/419/392/373-state
machines and the search tooling used to find the layout, is preserved in
this repository's git history.
