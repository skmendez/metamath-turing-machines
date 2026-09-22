#!/usr/bin/python3
"""Andrew J. Wade's ZF2 machine (codeberg.org/ajwade/turing_machine_explorer)
with its two duplicated axiom clauses removed, and the axiom order re-tuned
with his own block-move hill-climb.  392 states (his: 393).

Usage (WADE = path to a checkout of turing_machine_explorer):
    WADE=/path/to/turing_machine_explorer python3 zf2_dedup.py [--search]

Wade's axioms() lists B6b and B8b twice with identical encodings.  Each clause
is a hash-consed subtree, so the duplicate contributes almost no states, but
it does occupy a position in the main sequence and an axiom code.  Removing it
is semantically inert: proofs are sequences of (axiomcode, p1, p2, p3) steps,
every axiom remains reachable under its other code, and the last clause still
absorbs all codes beyond the table, so the set of enumerated proofs - and thus
halting iff ZF (without regularity) is inconsistent - is unchanged.
"""
import os, sys
sys.path.insert(0, os.environ.get('WADE', '.'))
import zf2 as wade

ORDER = [14, 15, 3, 16, 4, 7, 12, 8, 10, 5, 11, 2, 13, 0, 1, 6, 9, 17]


class ZF2(wade.ZF2):
    def axioms(self):
        ax = super().axioms()
        keys = [self.add_sequence(a) for a in ax]
        seen, keep = {}, []
        for i, k in enumerate(keys):
            if k not in seen:
                seen[k] = i
                keep.append(i)
        return [ax[i] for i in keep]


def cost(order):
    b = ZF2(); b.debug = False; b.AXIOMORDER = list(order); b.build_machine()
    return len(set(s[0] for s in b.tm.states)), b


if __name__ == '__main__':
    order = list(ORDER)
    if '--search' in sys.argv:
        n = len(order); best, _ = cost(order); changed = True
        while changed:
            changed = False
            for mid in range(1, n):
                for left in range(mid):
                    for right in range(mid + 1, n + 1):
                        new = order[:left] + order[mid:right] + order[left:mid] + order[right:]
                        if new[-1] in (0, 1):
                            continue
                        c, _ = cost(new)
                        if c < best:
                            order, best, changed = new, c, True
                            print('improved ->', best, order, flush=True)
        print('optimized axiom order:', order)
    states, b = cost(order)
    print('states:', states)
    b.tm.save('zf2_dedup_%d.tm' % states)
