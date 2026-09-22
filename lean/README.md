# Lean 4 formalization of the 370-state Riemann machine (partial)

A Lean 4 project (core Lean only, no Mathlib; `lean-toolchain` pins v4.33.0)
about `machines/2026-riemann-rh-370`.

    cd lean && lake build        # ~30 s; the bounded certificates use native_decide

## The target

    TM.HaltsFrom RH370.M RH370.start ↔ ∃ n, 1 ≤ n ∧ RHProg.crit n

where `RHProg.crit n` is the integer form of the Matiyasevich criterion
(`(D·max(H_q − n,0)·D)² > n·(D·H_n)⁴` with `q = lcm(1..n)`, `D = q!`,
harmonic numerators written as integers). The proof factors into three
layers; the status of each is stated exactly.

| layer | file | statement | status |
|---|---|---|---|
| (B) model ↔ criterion | `RH/Program.lean` | `RHProg.progHalts_iff : ProgHalts ↔ ∃ n, 1 ≤ n ∧ crit n` | **proved** (axioms: `propext`, `Quot.sound`) |
| (A') IR ↔ model | `RH/IR370.lean` | `Target.IRRefinesModel` | not proved; bounded certificate `IR370.heads_ok` |
| (A) TM ↔ IR | `RH/Bridge.lean` | `Target.RefinesIR` | not proved; bounded certificate `Bridge.lockstep_ok` |
| assembly | `RH/Target.lean` | `target_of_refinements : RefinesIR → IRRefinesModel → target` | proved |

### (B) The model program computes the criterion — proved

`RH/Program.lean` is a shallow embedding of `riemann.nql`, statement for
statement (the lcm scan as a fuel-bounded loop, the fused countdown loop with
the `k`-guarded overwrite of `c`, the monus/squaring tail, the halt builtin's
`l > c` test), over natural numbers with monus. Independently of the program
it defines `fact`, `hn m = Σ m!/k`, `prodFrom`, `lcmUpTo` and `crit`. The
proof establishes: the scan returns `lcm(L, x)` (`scan_eq_lcm`, via the
first multiple of `L` divisible by `x`); the inner loop's invariants
`denom = t!`, `l = hn t`, `c = cval x c0 t` (`inner_spec`) and the closed
form `cval x c0 t = hn x · prodFrom x t` for `t ≥ x` (`cval_closed`); the
`lcm` register equals `lcmUpTo n` after `n` iterations (`lcmAfter_eq`); and
finally `haltsAt_iff_crit`, `progHalts_iff`.

### (A') The compiled program implements the model — bounded evidence only

`RH/IR370.lean` contains the register program the compiler actually emitted
for `riemann.nql` (extracted from the subroutine child maps: one instruction
per PC slot, 512 slots, absolute jump targets, the compiler's
skip-on-nonzero decrement convention) with its semantics. `heads_ok`
(`native_decide`) checks that the program reaches the outer-loop head
three times within 60000 steps, each time with `x = n−1`,
`lcm = lcmUpTo (n−1)` and the zero-invariants the model relies on.

### (A) The transition table implements the compiled program — bounded evidence only

`RH/Bridge.lean` decodes the tape at every entry to the dispatcher root
(`main()[]`, state 251): nine PC bits left of a `00` separator, then the
register file as `value + 1` ones per register. `lockstep_ok`
(`native_decide`) checks that for the first 40000 root entries (about two
million machine steps, covering the outer iterations for n = 1 and n = 2 and
into n = 3) the decoded (pc, registers) equal the IR state, advancing one IR
instruction per root entry. This is a kernel-checked lockstep *certificate
for a prefix*, not a simulation proof.

### Also here

`RH/RH370.lean`: the table imported verbatim, `no_halt_200000`.
`RH/RH370Flip.lean`: the comparison-flipped variant halts (`halts`).

## What a full proof still needs

(A) for all steps: a simulation relation between tape configurations and IR
states, with a lemma per gadget class (the dispatcher BDD, the register
increment/decrement microcode that shifts the tape, the jump gadgets) — the
decoder in `Bridge.lean` is the relation's core. (A') for all steps: a
decompilation argument that the IR's instruction ranges implement each
statement of the model. Both are large but routine; neither is started
beyond the definitions. The bounded certificates cannot be pushed past
n = 2 (the n = 3 iteration takes ~10¹² instructions), so any further
assurance must come from proof, not evaluation.

`native_decide` trusts the Lean compiler; the (B) proof does not use it.
