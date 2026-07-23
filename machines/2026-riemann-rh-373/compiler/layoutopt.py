#!/usr/bin/env python3
"""Layout optimization pass: search no-op insertion points for BDD sharing.

The main dispatcher is a binary tree over program-counter bits whose states
merge whenever two aligned power-of-two blocks of the instruction stream are
identical.  Whether repeated code fragments actually align — and whether
their internal jumps get identical encodings — depends on the absolute
offsets of everything before them, so inserting one-slot no-ops can bring
large fragments into phase and collapse whole dispatch subtrees.  The
objective (reachable states after compression) is a global function of all
offsets, so this pass optimizes it by exact search: every candidate is a
real build of the machine, made cheap by parsing once and pinning pc_bits
(~6 ms per trial).

Safety: a no-op inserted immediately after a decrement instruction would be
skipped into by the decrement's success path (PC+2), corrupting control
flow.  Only indices whose predecessor (ignoring zero-size labels) is not a
decrement are considered.

Stages: exhaustive singles -> exhaustive pairs -> greedy extension ->
simulated annealing with restarts.  All seeds are fixed; given the same
source, register order, and stage parameters the result is deterministic.

Usage:
    python3 layoutopt.py SOURCE.nql reg1,reg2,... PC_BITS [ANNEAL_ROUNDS]
"""
import itertools
import os
import random
import sys
import time
from multiprocessing import Pool

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

_ctx = {}


def _init(source_text, register_order, pc_bits):
    import nqlgrammar
    import nqlast
    import framework
    from framework import Machine, Label
    ast, = nqlgrammar.grammar.parse_string(source_text, parse_all=True)
    _ctx.update(ast=ast, order=tuple(register_order), pcb=pc_bits,
                nqlast=nqlast, framework=framework, Machine=Machine, Label=Label)


def _trial(nops):
    fw = _ctx['framework']
    fw.MAIN_INSERT_NOPS = dict(nops)
    try:
        b = _ctx['nqlast'].AstMachine(_ctx['ast'])
        b.pc_bits = _ctx['pcb']
        for name in _ctx['order']:
            b.register('_G' + name)
        m = _ctx['Machine'](b)
        m.compress()
        return len(m.reachable())
    except BaseException:
        return 10 ** 9


def _batch(cands):
    return [(_trial(n), tuple(sorted(n.items()))) for n in cands]


def _safe_indices():
    import framework
    fw, Label = _ctx['framework'], _ctx['Label']
    fw.MAIN_INSERT_NOPS = {}
    box = {}
    orig = framework.MachineBuilder.makesub

    def patched(self, *parts, name):
        if name == 'main()' and 'parts' not in box:
            p = parts
            if not self.options.no_cfg_optimize:
                p = framework.cfg_optimizer(p)
            regcount = self._nextreg
            while regcount & (regcount - 1):
                regcount += 1
            box['parts'] = regcount * (self.reg_init(),) + tuple(p)
        return orig(self, *parts, name=name)

    framework.MachineBuilder.makesub = patched
    try:
        b = _ctx['nqlast'].AstMachine(_ctx['ast'])
        b.pc_bits = _ctx['pcb']
        for name in _ctx['order']:
            b.register('_G' + name)
        _ctx['Machine'](b)
    finally:
        framework.MachineBuilder.makesub = orig
    parts = box['parts']
    safe = []
    for ix in range(len(parts) + 1):
        j = ix - 1
        while j >= 0 and isinstance(parts[j], Label):
            j -= 1
        if j >= 0 and getattr(parts[j], 'is_decrement', False):
            continue
        safe.append(ix)
    return safe


def find_layout(source_text, register_order, pc_bits, anneal_restarts=6,
                anneal_iters=90, workers=None, log=lambda *a: None):
    """Return (states, nop_dict) minimizing reachable states."""
    _init(source_text, register_order, pc_bits)
    safe = _safe_indices()
    best_s, best = _trial({}), {}
    log('baseline %d states, %d safe positions' % (best_s, len(safe)))
    workers = workers or max(1, (os.cpu_count() or 2) - 1)
    t0 = time.time()
    with Pool(workers, initializer=_init,
              initargs=(source_text, register_order, pc_bits)) as pool:

        def run(cands):
            nonlocal best_s, best
            out = []
            for chunk in pool.imap_unordered(
                    _batch, [cands[i:i + 40] for i in range(0, len(cands), 40)]):
                out.extend(chunk)
            for s, items in out:
                if s < best_s or (s == best_s and best and
                                  sum(dict(items).values()) < sum(best.values())):
                    best_s, best = s, dict(items)
            return out

        run([{ix: 1} for ix in safe])
        log('singles: %d (%.0fs)' % (best_s, time.time() - t0))
        cands = []
        for a, b2 in itertools.combinations_with_replacement(safe, 2):
            d = {a: 1}
            d[b2] = d.get(b2, 0) + 1
            cands.append(d)
        run(cands)
        log('pairs: %d (%.0fs)' % (best_s, time.time() - t0))
        improved = True
        while improved:
            prev = best_s
            run([dict(best, **{ix: best.get(ix, 0) + 1}) for ix in safe])
            improved = best_s < prev
        log('greedy: %d (%.0fs)' % (best_s, time.time() - t0))
        for restart in range(anneal_restarts):
            rng = random.Random(1000 + restart)
            temp = restart % 2
            cur, cur_s = dict(best), best_s
            for _ in range(anneal_iters):
                props = []
                for _ in range(160):
                    d = dict(cur)
                    r = rng.random()
                    if r < 0.35:
                        ix = rng.choice(safe)
                        d[ix] = d.get(ix, 0) + 1
                    elif r < 0.45 and d:
                        ix = rng.choice(list(d))
                        jx = rng.choice(safe)
                        d[ix] -= 1
                        if not d[ix]:
                            del d[ix]
                        d[jx] = d.get(jx, 0) + 1
                    elif r < 0.6:
                        for ix in (rng.choice(safe), rng.choice(safe)):
                            d[ix] = d.get(ix, 0) + 1
                    elif d:
                        ix = rng.choice(list(d))
                        d[ix] -= 1
                        if not d[ix]:
                            del d[ix]
                    props.append(d)
                out = sorted(run(props))
                if out and out[0][0] <= cur_s + temp:
                    cur_s, cur = out[0][0], dict(out[0][1])
            log('anneal %d: %d (%.0fs)' % (restart, best_s, time.time() - t0))
    return best_s, best


if __name__ == '__main__':
    src = open(sys.argv[1]).read()
    order = tuple(sys.argv[2].split(','))
    pcb = int(sys.argv[3])
    restarts = int(sys.argv[4]) if len(sys.argv) > 4 else 6
    states, nops = find_layout(src, order, pcb, anneal_restarts=restarts,
                               log=lambda *a: print(*a))
    print('best: %d states' % states)
    print('LAYOUT_NOPS = {')
    for ix in sorted(nops):
        print('    %d: %d,' % (ix, nops[ix]))
    print('}')
