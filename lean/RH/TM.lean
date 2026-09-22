/-!
# Binary one-tape Turing machines

States are natural numbers; a transition gives the symbol to write, the
direction to move, and the next state, or `none` to halt.  The tape is a
zipper of `Bool`s with an implicit infinite `false` fill on both sides.
-/

inductive Dir where
  | L | R
  deriving DecidableEq, Repr, Inhabited

structure Step where
  write : Bool
  dir   : Dir
  next  : Option Nat
  deriving Repr, Inhabited

/-- A machine: its transition function, both symbols per state. -/
structure TM where
  δ : Nat → Bool → Step

structure Cfg where
  left  : List Bool   -- cells to the left, nearest first
  cur   : Bool
  right : List Bool   -- cells to the right, nearest first
  state : Option Nat
  deriving Repr

namespace TM

def init (s : Nat) : Cfg := ⟨[], false, [], some s⟩

def step (M : TM) (c : Cfg) : Cfg :=
  match c.state with
  | none => c
  | some s =>
    let t := M.δ s c.cur
    match t.dir with
    | Dir.R =>
      match c.right with
      | []      => ⟨t.write :: c.left, false, [], t.next⟩
      | x :: xs => ⟨t.write :: c.left, x, xs, t.next⟩
    | Dir.L =>
      match c.left with
      | []      => ⟨[], false, t.write :: c.right, t.next⟩
      | x :: xs => ⟨xs, x, t.write :: c.right, t.next⟩

def run (M : TM) (k : Nat) (c : Cfg) : Cfg :=
  match k with
  | 0     => c
  | k + 1 => run M k (M.step c)

def Halted (c : Cfg) : Prop := c.state = none

instance : DecidablePred Halted := fun c => by
  unfold Halted; exact inferInstance

/-- The machine halts from `c` iff some finite run reaches a halted configuration. -/
def HaltsFrom (M : TM) (c : Cfg) : Prop := ∃ k, Halted (M.run k c)

theorem run_add (M : TM) (a b : Nat) (c : Cfg) :
    M.run (a + b) c = M.run b (M.run a c) := by
  induction a generalizing c with
  | zero => simp [run]
  | succ a ih => simp [Nat.succ_add, run, ih]

theorem step_halted (M : TM) (c : Cfg) (h : Halted c) : M.step c = c := by
  unfold Halted at h; unfold step; rw [h]

theorem run_halted (M : TM) (k : Nat) (c : Cfg) (h : Halted c) : M.run k c = c := by
  induction k with
  | zero => rfl
  | succ k ih => rw [run, step_halted M c h, ih]

end TM
