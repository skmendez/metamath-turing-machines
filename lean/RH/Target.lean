import RH.TM
import RH.RH370
import RH.IR370
import RH.Program
import RH.Bridge

/-!
# The target theorem and what remains

The statement one wants about `machines/2026-riemann-rh-370` is

    TM.HaltsFrom RH370.M RH370.start ↔ ∃ n, 1 ≤ n ∧ RHProg.crit n

It factors through two refinement layers:

* (A) the transition table implements the compiled register program
  `IR370.prog` (halting of the one is halting of the other);
* (A') the register program implements the shallow model `RHProg`;
* (B) the shallow model halts iff some `n ≥ 1` violates the criterion.

(B) is proved (`RHProg.progHalts_iff`).  (A) and (A') are stated below as
hypotheses of `target_of_refinements`; they are supported by the bounded,
kernel-checked certificates `Bridge.lockstep_ok` (40000 instructions of
exact TM/IR lockstep) and `IR370.heads_ok` (the IR reaches the outer loop
head three times with the model's register values), but they are NOT proved
for all steps.  Anyone citing this development should cite exactly that.
-/

namespace Target

/-- The compiled register program halts. -/
def IRHalts : Prop := ∃ k, (IR370.run k IR370.start).halted = true

/-- Refinement (A): the Turing machine halts iff the register program halts. -/
def RefinesIR : Prop := TM.HaltsFrom RH370.M RH370.start ↔ IRHalts

/-- Refinement (A'): the register program halts iff the model program halts. -/
def IRRefinesModel : Prop := IRHalts ↔ RHProg.ProgHalts

/-- The theorem, conditional on the two refinements. -/
theorem target_of_refinements (hA : RefinesIR) (hA' : IRRefinesModel) :
    TM.HaltsFrom RH370.M RH370.start ↔ ∃ n, 1 ≤ n ∧ RHProg.crit n := by
  unfold RefinesIR at hA; unfold IRRefinesModel at hA'
  rw [hA, hA', RHProg.progHalts_iff]

end Target
