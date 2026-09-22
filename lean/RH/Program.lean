/-!
# The register-level program of the 370-state machine, and its correctness

A shallow embedding of `machines/2026-riemann-rh-370/riemann.nql` over
natural numbers (subtraction is monus, as in NQL), followed by a proof that
the program's halting check at candidate `n` fires exactly when `n` violates
the integer form of the Matiyasevich criterion.

    riemann.nql                        model below
    ---------------------------------  ---------------------------------
    x = x + 1;                         candidate n (outer recursion)
    c = lcm;                           step := L
    while (lcm != (lcm/x)*x)           scanAux x L L x
      { lcm = lcm + c; }
    i = 1; denom = 1;                  inner q 1 1 0 L n
    j = j + lcm;  k = k + x;             (j = q iterations, k = n)
    while (j > 0) { j = j - 1;
      c = c * i;  l = l * i + denom;
      if (k > 0) { k = k - 1; c = l; }
      denom = denom * i;  i = i + 1; }
    l = l - denom * x; c = c * c;      tail of `iterate`
    l = l * denom; c = c * c;
    c = c * x; l = l * l;
    builtin_halt_if_gt_destroy(l, c);  halt iff l > c; l := 0 otherwise

The registers `l`, `j`, `k` are zero at the top of every outer iteration
(initially, and `l` because the halt builtin zeroes its left argument on the
non-halting path); `c` holds the scan step `L` when the inner loop starts and
is overwritten at `i = 1` because `k = n ≥ 1`.  The model makes these
dependencies explicit rather than assuming them.
-/

namespace RHProg

/-! ## Arithmetic definitions (independent of the program) -/

def fact : Nat → Nat
  | 0 => 1
  | n+1 => (n+1) * fact n

/-- `hn m = Σ_{k=1}^{m} m!/k`, the numerator of the harmonic number `H_m`
over the denominator `m!`, via the recurrence `hn (i+1) = hn i · (i+1) + i!`. -/
def hn : Nat → Nat
  | 0 => 0
  | i+1 => hn i * (i+1) + fact i

/-- `prodFrom a b = ∏_{t=a+1}^{b} t` (equal to `b!/a!` for `a ≤ b`; `1` if `b ≤ a`). -/
def prodFrom (a : Nat) : Nat → Nat
  | 0 => 1
  | b+1 => if b+1 ≤ a then 1 else (b+1) * prodFrom a b

/-- `lcm(1..n)`. -/
def lcmUpTo : Nat → Nat
  | 0 => 1
  | n+1 => Nat.lcm (lcmUpTo n) (n+1)

/-- The criterion in integer form.  With `q = lcm(1..n)` and `D = q!`,
`hn q = D·H_q` and `hn n · prodFrom n q = D·H_n`, so `crit n` is
`(D·max(H_q − n, 0)·D)² > n·(D·H_n)⁴`, i.e. `max(H_q − n, 0)² > n·H_n⁴`
after dividing by `D⁴`. -/
def crit (n : Nat) : Prop :=
  let q := lcmUpTo n
  let D := fact q
  let c := hn n * prodFrom n q
  let r := (hn q - D * n) * D
  r * r > n * (c * c * (c * c))

/-! ## The program -/

/-- `while (cur % x ≠ 0) cur := cur + step`, with fuel. -/
def scanAux : Nat → Nat → Nat → Nat → Nat
  | 0, cur, _, _ => cur
  | f+1, cur, step, x => if cur % x = 0 then cur else scanAux f (cur + step) step x

/-- The inner loop with `j` iterations left; returns `(denom, l, c)`. -/
def inner : Nat → Nat → Nat → Nat → Nat → Nat → Nat × Nat × Nat
  | 0, _, denom, l, c, _ => (denom, l, c)
  | j+1, i, denom, l, c, k =>
    let c1 := c * i
    let l1 := l * i + denom
    let c2 := if k > 0 then l1 else c1
    inner j (i+1) (denom * i) l1 c2 (k - 1)

/-- One outer iteration for candidate `x` with incoming `lcm = L`.
Returns `(halted, new lcm)`. -/
def iterate (x L : Nat) : Bool × Nat :=
  let q := scanAux x L L x
  let p := inner q 1 1 0 L x
  let denom := p.1
  let l := p.2.1
  let c := p.2.2
  let l2 := l - denom * x
  let c2 := c * c
  let l3 := l2 * denom
  let c3 := c2 * c2
  let c4 := c3 * x
  let l4 := l3 * l3
  (decide (l4 > c4), q)

/-- The `lcm` register after the outer iterations for candidates `1..n`. -/
def lcmAfter : Nat → Nat
  | 0 => 1
  | n+1 => (iterate (n+1) (lcmAfter n)).2

/-- The halting check fires at candidate `n`. -/
def haltsAt (n : Nat) : Prop := 1 ≤ n ∧ (iterate n (lcmAfter (n-1))).1 = true

/-- The program halts. -/
def ProgHalts : Prop := ∃ n, haltsAt n

/-! ## The lcm scan computes the lcm -/

theorem scanAux_spec (f cur step x : Nat)
    (ht : ∃ t, t ≤ f ∧ (cur + t * step) % x = 0) :
    (scanAux f cur step x) % x = 0 ∧
    ∃ t, t ≤ f ∧ scanAux f cur step x = cur + t * step := by
  induction f generalizing cur with
  | zero =>
    obtain ⟨t, ht0, hm⟩ := ht
    have : t = 0 := by omega
    subst this
    simp at hm
    exact ⟨by simpa [scanAux] using hm, 0, Nat.le_refl _, by simp [scanAux]⟩
  | succ f ih =>
    by_cases h : cur % x = 0
    · exact ⟨by simp [scanAux, h], 0, Nat.zero_le _, by simp [scanAux, h]⟩
    · obtain ⟨t, htf, hm⟩ := ht
      cases t with
      | zero => simp at hm; exact absurd hm h
      | succ t' =>
        have hm' : (cur + step + t' * step) % x = 0 := by
          rw [Nat.succ_mul] at hm
          have : cur + (t' * step + step) = cur + step + t' * step := by omega
          rw [this] at hm; exact hm
        obtain ⟨h1, t'', ht'', h2⟩ := ih (cur + step) ⟨t', by omega, hm'⟩
        refine ⟨by simpa [scanAux, h] using h1, t'' + 1, by omega, ?_⟩
        simp [scanAux, h, h2, Nat.succ_mul]; omega

theorem scanAux_le (f cur step x t : Nat) (ht : t ≤ f) (h : (cur + t * step) % x = 0) :
    scanAux f cur step x ≤ cur + t * step := by
  induction f generalizing cur t with
  | zero =>
    have : t = 0 := by omega
    subst this; simp [scanAux]
  | succ f ih =>
    by_cases hc : cur % x = 0
    · simp [scanAux, hc]
    · cases t with
      | zero => simp at h; exact absurd h hc
      | succ t' =>
        have h' : (cur + step + t' * step) % x = 0 := by
          rw [Nat.succ_mul] at h
          have : cur + (t' * step + step) = cur + step + t' * step := by omega
          rw [this] at h; exact h
        have := ih (cur + step) t' (by omega) h'
        simp [scanAux, hc]
        rw [Nat.succ_mul]; omega

theorem scan_eq_lcm (L x : Nat) (hL : 0 < L) (hx : 0 < x) :
    scanAux x L L x = Nat.lcm L x := by
  have hq : 0 < Nat.lcm L x := Nat.lcm_pos hL hx
  have hLq : L ∣ Nat.lcm L x := Nat.dvd_lcm_left L x
  have hxq : x ∣ Nat.lcm L x := Nat.dvd_lcm_right L x
  obtain ⟨k, hk⟩ := hLq
  have hk0 : 0 < k := by
    rcases Nat.eq_zero_or_pos k with h | h
    · subst h; simp at hk; omega
    · exact h
  -- lcm ≤ L * x
  have hle : Nat.lcm L x ≤ L * x :=
    Nat.le_of_dvd (Nat.mul_pos hL hx) (Nat.lcm_dvd (Nat.dvd_mul_right L x) (Nat.dvd_mul_left x L))
  have hkx : k ≤ x := by
    rw [hk] at hle
    exact Nat.le_of_mul_le_mul_left hle hL
  -- the scan reaches lcm at t = k - 1
  have hreach : (L + (k - 1) * L) % x = 0 := by
    have : L + (k - 1) * L = L * k := by
      cases k with
      | zero => omega
      | succ k' => rw [Nat.add_sub_cancel, Nat.mul_succ, Nat.mul_comm L k']; omega
    rw [this, ← hk]; exact Nat.mod_eq_zero_of_dvd hxq
  obtain ⟨hmod, t, htx, hres⟩ := scanAux_spec x L L x ⟨k - 1, by omega, hreach⟩
  have hle2 := scanAux_le x L L x (k - 1) (by omega) hreach
  -- the result is a common multiple, hence ≥ lcm
  have hLr : L ∣ scanAux x L L x := by
    rw [hres]; exact ⟨t + 1, by rw [Nat.mul_succ, Nat.mul_comm L t]; omega⟩
  have hxr : x ∣ scanAux x L L x := Nat.dvd_of_mod_eq_zero hmod
  have hrpos : 0 < scanAux x L L x := by rw [hres]; omega
  have hge : Nat.lcm L x ≤ scanAux x L L x := Nat.le_of_dvd hrpos (Nat.lcm_dvd hLr hxr)
  have hkk : L + (k - 1) * L = Nat.lcm L x := by
    have : L + (k - 1) * L = L * k := by
      cases k with
      | zero => omega
      | succ k' => rw [Nat.add_sub_cancel, Nat.mul_succ, Nat.mul_comm L k']; omega
    rw [this, hk]
  omega

/-! ## The inner loop -/

/-- The value of `c` after `t` inner iterations, given its initial value `c0`
and the candidate `x`: it tracks `hn t` while `t ≤ x`, then accumulates the
product of the remaining `i`. -/
def cval (x c0 : Nat) : Nat → Nat
  | 0 => c0
  | t+1 => if t < x then hn (t+1) else cval x c0 t * (t+1)

theorem fact_succ (t : Nat) : fact (t+1) = fact t * (t+1) := by
  simp [fact, Nat.mul_comm]

theorem inner_spec (x c0 : Nat) (j t : Nat) :
    inner j (t+1) (fact t) (hn t) (cval x c0 t) (x - t) =
      (fact (t+j), hn (t+j), cval x c0 (t+j)) := by
  induction j generalizing t with
  | zero => simp [inner]
  | succ j ih =>
    have step : inner (j+1) (t+1) (fact t) (hn t) (cval x c0 t) (x - t) =
        inner j (t+2) (fact (t+1)) (hn (t+1)) (cval x c0 (t+1)) (x - (t+1)) := by
      have e1 : fact t * (t+1) = fact (t+1) := (fact_succ t).symm
      have e3 : (if x - t > 0 then hn t * (t+1) + fact t else cval x c0 t * (t+1))
                  = cval x c0 (t+1) := by
        by_cases hlt : t < x
        · simp [cval, hlt, show x - t > 0 by omega, hn]
        · simp [cval, hlt, show ¬ (x - t > 0) by omega]
      have e4 : x - t - 1 = x - (t+1) := by omega
      show inner j (t+1+1) (fact t * (t+1)) (hn t * (t+1) + fact t)
             (if x - t > 0 then hn t * (t+1) + fact t else cval x c0 t * (t+1)) (x - t - 1) = _
      rw [e1, e3, e4]
      rfl
    rw [step, ih (t+1)]
    simp [Nat.add_assoc, Nat.add_comm, Nat.add_left_comm]

theorem prodFrom_self (a : Nat) : prodFrom a a = 1 := by
  cases a with
  | zero => rfl
  | succ a' => simp [prodFrom]

theorem cval_closed (x c0 : Nat) (hx : 1 ≤ x) (t : Nat) (hxt : x ≤ t) :
    cval x c0 t = hn x * prodFrom x t := by
  induction t with
  | zero => omega
  | succ t ih =>
    by_cases h : x ≤ t
    · have hlt : ¬ (t < x) := by omega
      simp [cval, hlt, ih h, prodFrom, show ¬ (t + 1 ≤ x) by omega]
      simp [Nat.mul_assoc, Nat.mul_comm, Nat.mul_left_comm]
    · -- t + 1 = x
      have hex : x = t + 1 := by omega
      subst hex
      simp [cval, prodFrom_self]

/-! ## Correctness of one outer iteration -/

theorem lcmUpTo_pos (n : Nat) : 0 < lcmUpTo n := by
  induction n with
  | zero => simp [lcmUpTo]
  | succ n ih => exact Nat.lcm_pos ih (Nat.succ_pos n)

theorem lcmAfter_eq (n : Nat) : lcmAfter n = lcmUpTo n := by
  induction n with
  | zero => rfl
  | succ n ih =>
    simp only [lcmAfter, iterate, ih, lcmUpTo]
    exact scan_eq_lcm _ _ (lcmUpTo_pos n) (Nat.succ_pos n)

theorem dvd_lcmUpTo_self (n : Nat) (hn1 : 1 ≤ n) : n ∣ lcmUpTo n := by
  cases n with
  | zero => omega
  | succ n => simp only [lcmUpTo]; exact Nat.dvd_lcm_right _ _

theorem le_lcmUpTo (n : Nat) (hn1 : 1 ≤ n) : n ≤ lcmUpTo n :=
  Nat.le_of_dvd (lcmUpTo_pos n) (dvd_lcmUpTo_self n hn1)

theorem iterate_halt_iff (n : Nat) (hn1 : 1 ≤ n) :
    (iterate n (lcmUpTo (n-1))).1 = true ↔ crit n := by
  have hL : 0 < lcmUpTo (n-1) := lcmUpTo_pos _
  have hq : scanAux n (lcmUpTo (n-1)) (lcmUpTo (n-1)) n = lcmUpTo n := by
    rw [scan_eq_lcm _ _ hL (by omega)]
    cases n with
    | zero => omega
    | succ n => rfl
  have hin := inner_spec n (lcmUpTo (n-1)) (lcmUpTo n) 0
  simp only [Nat.zero_add, Nat.sub_zero, fact, hn, cval] at hin
  have hc : cval n (lcmUpTo (n-1)) (lcmUpTo n) = hn n * prodFrom n (lcmUpTo n) :=
    cval_closed n _ hn1 _ (le_lcmUpTo n hn1)
  rw [hc] at hin
  simp only [iterate, hq, hin, decide_eq_true_eq, crit]
  generalize hn n * prodFrom n (lcmUpTo n) = c
  generalize (hn (lcmUpTo n) - fact (lcmUpTo n) * n) * fact (lcmUpTo n) = r
  rw [Nat.mul_comm (c * c * (c * c)) n]

/-! ## Main theorem: the program halts iff some `n ≥ 1` violates the criterion -/

theorem haltsAt_iff_crit (n : Nat) (hn1 : 1 ≤ n) : haltsAt n ↔ crit n := by
  unfold haltsAt
  rw [lcmAfter_eq]
  constructor
  · rintro ⟨_, h⟩; exact (iterate_halt_iff n hn1).1 h
  · intro h; exact ⟨hn1, (iterate_halt_iff n hn1).2 h⟩

theorem progHalts_iff : ProgHalts ↔ ∃ n, 1 ≤ n ∧ crit n := by
  constructor
  · rintro ⟨n, hn⟩
    exact ⟨n, hn.1, (haltsAt_iff_crit n hn.1).1 hn⟩
  · rintro ⟨n, hn1, hc⟩
    exact ⟨n, (haltsAt_iff_crit n hn1).2 hc⟩

end RHProg
