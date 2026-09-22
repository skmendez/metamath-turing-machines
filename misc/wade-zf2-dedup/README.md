# 392-state ZF machine: Wade's 393 with duplicated axiom clauses removed

Andrew J. Wade's `zf2.py` (<https://codeberg.org/ajwade/turing_machine_explorer>,
commit 9c5c2e8) builds a 393-state machine that halts iff ZF without
regularity is inconsistent - the current record for a ZF-independent machine
(the bbchallenge wiki still lists his earlier 432).

Its axiom list has 20 entries but only 18 distinct axioms: `B6b` and `B8b`
each appear twice with identical encodings. `zf2_dedup.py` subclasses his
builder, drops the duplicates (detected structurally via the hash-consed
sequence ids, not by label), and re-runs his own block-move hill-climb over
the axiom order, giving **392 states** (`zf2_dedup_392.tm`, his `.tm` format).

Why it is semantically inert: a proof is a list of (axiomcode, p1, p2, p3)
steps; the machine tries the clauses in list order, decrementing the code,
so clause k is active for code k and the last clause absorbs every larger
code. Removing a duplicate clause removes one code that selected an axiom
still selectable under its other code, so the set of enumerable proofs is
unchanged, and so is halting.

Reproduce with a checkout of Wade's repository:

    WADE=/path/to/turing_machine_explorer python3 zf2_dedup.py           # build with the tuned order
    WADE=/path/to/turing_machine_explorer python3 zf2_dedup.py --search  # re-run the hill-climb

Caveats. This is a one-state improvement obtained by inspection, not the
"below 387" that would need an actual reduction of the axiom set (each
clause costs on the order of 10-15 decision-DAG states, so eliminating a
derivable axiom is the lever). Wade's `--debug` assertion build trips
`assert_eq(scratch1,0)` at step 86836 on his own unmodified machine as well
as on this one (identical step and state), so his debug asserts are stale
and were not usable as an oracle; the justification above is structural.
Not formally verified.
