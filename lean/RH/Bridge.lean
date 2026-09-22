import RH.TM
import RH.RH370
import RH.IR370

/-!
# Lockstep certificate: the Turing machine vs. the compiled register program

At every entry to the main dispatcher's root state, the tape holds the
program counter (9 bits, immediately left of a `00` separator) followed by
the register file (each register as `value + 1` ones, separated by single
zeros; 16 fields, of which the program uses the first 11).  Between two root
entries the machine executes exactly one register-program instruction, so
decoding the tape at the k-th root entry must give the k-th state of the
IR program.  `lockstep` checks this for a bounded number of entries and
`lockstep_ok` establishes it by evaluation.
-/

namespace Bridge

/-- Index of the state `main()[]` (the dispatcher root) in the imported table. -/
def rootState : Nat := 251

def tapeList (c : Cfg) : List Bool := c.left.reverse ++ (c.cur :: c.right)

/-- Scan the reversed tape for the last `00`; returns (register region in
tape order, the cells left of the separator in reversed order). -/
def findRegs : List Bool → List Bool → List Bool × List Bool
  | false :: false :: rest, acc => (acc, rest)
  | b :: rest, acc => findRegs rest (b :: acc)
  | [], acc => (acc, [])

/-- Lengths of the maximal runs of `true` separated by single `false`s. -/
def runs : Nat → List Bool → List Nat
  | 0, _ => []
  | _, [] => []
  | fuel+1, l =>
    let r := l.takeWhile (· == true)
    let rest := l.dropWhile (· == true)
    r.length :: (match rest with
      | [] => []
      | _ :: t => runs fuel t)

/-- Reversed tape with trailing blank cells removed. -/
def revTrim (c : Cfg) : List Bool := (tapeList c).reverse.dropWhile (· == false)

/-- Registers not yet created by the initializers decode as zero. -/
def decodeRegs (c : Cfg) : Array Nat :=
  let (region, _) := findRegs (revTrim c) []
  let vals := ((runs (region.length + 1) region).take IR370.nregs).map (· - 1)
  (vals ++ List.replicate (IR370.nregs - vals.length) 0).toArray

def decodePc (c : Cfg) : Nat :=
  let (_, restRev) := findRegs (revTrim c) []
  (restRev.take 9).foldr (fun b acc => 2 * acc + (if b then 1 else 0)) 0

/-- Run the TM; at each root entry compare with the IR state, then advance both. -/
def lockstep : Nat → Cfg → IR370.St → Nat → Bool
  | 0, _, _, _ => true
  | b+1, c, s, m =>
    if m = 0 then true
    else if c.state = some rootState then
      (decodeRegs c == s.regs && decodePc c == s.pc) &&
        lockstep b (RH370.M.step c) (IR370.step s) (m - 1)
    else lockstep b (RH370.M.step c) s m

/-- Sanity: the first root entry decodes to pc 0 and all-zero registers. -/
theorem first_entry :
    (RH370.M.run 1 RH370.start).state = some rootState ∧
    decodePc (RH370.M.run 1 RH370.start) = 0 ∧
    decodeRegs (RH370.M.run 1 RH370.start) = IR370.start.regs := by native_decide

/-- Machine-checked: for the first 40000 root entries (about 2 million machine
steps, covering the outer iterations for n = 1 and n = 2 and into n = 3), the
tape decodes exactly to the IR program's state. -/
theorem lockstep_ok : lockstep 2000000 RH370.start IR370.start 40000 = true := by
  native_decide

end Bridge
