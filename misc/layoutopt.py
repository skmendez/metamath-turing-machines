#!/usr/bin/env python3
"""Search for "layout" no-op declarations that minimize a machine's states.

The main dispatcher is a binary tree over program-counter bits whose subtrees
merge whenever two aligned power-of-two blocks of the instruction stream are
identical.  Whether repeated code fragments align - and whether their jumps
get identical encodings - depends on the absolute offsets of everything
before them, so inserting one-slot no-ops can bring large fragments into
phase and collapse whole dispatch subtrees.  The objective is a global
function of all offsets, so this tool optimizes it by exact search: every
candidate is a real build (parse once, pin pc_bits; a few milliseconds per
trial), staged as exhaustive singles -> exhaustive pairs -> greedy ->
fixed-seed simulated annealing.

Only decrement-safe insertion points are proposed (the compiler additionally
enforces this at build time).  Output is a block of "layout INDEX COUNT;"
declarations to paste into the .nql file.

Usage:
    python3 misc/layoutopt.py MACHINE.nql [ANNEAL_RESTARTS]

The source's existing option declarations are honored; existing layout
declarations are ignored (the search starts from scratch).
"""
import itertools
import os
import random
import sys
import time
from multiprocessing import Pool

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'compiler'))

_ctx = {}


def _init(path):
    import nqlgrammar
    import nqlast
    import framework
    ast, = nqlgrammar.grammar.parseFile(path, parseAll=True)
    ast.options.layout_nops = {}
    builder = nqlast.AstMachine(ast)
    builder.pc_bits = 50
    pcb = builder.main().order
    _ctx.update(ast=ast, nqlast=nqlast, framework=framework, pcb=pcb)


def _trial(nops):
    from framework import Machine
    ast = _ctx['ast']
    ast.options.layout_nops = dict(nops)
    try:
        builder = _ctx['nqlast'].AstMachine(ast)
        builder.pc_bits = _ctx['pcb']
        machine = Machine(builder)
        machine.compress()
        return len(machine.reachable())
    except BaseException:
        return 10 ** 9


def _batch(cands):
    return [(_trial(n), tuple(sorted(n.items()))) for n in cands]


def _safe_indices():
    import framework
    from framework import Label, Machine
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
        _ctx['ast'].options.layout_nops = {}
        builder = _ctx['nqlast'].AstMachine(_ctx['ast'])
        builder.pc_bits = _ctx['pcb']
        Machine(builder)
    finally:
        framework.MachineBuilder.makesub = orig
    parts = box['parts']
    safe = []
    for index in range(len(parts) + 1):
        prev = index - 1
        while prev >= 0 and isinstance(parts[prev], Label):
            prev -= 1
        if prev >= 0 and getattr(parts[prev], 'is_decrement', False):
            continue
        safe.append(index)
    return safe


def find_layout(path, anneal_restarts=6, anneal_iters=90, workers=None,
                log=lambda *a: None):
    _init(path)
    safe = _safe_indices()
    best_states, best = _trial({}), {}
    log('baseline %d states at pc_bits=%d, %d safe positions'
        % (best_states, _ctx['pcb'], len(safe)))
    workers = workers or max(1, (os.cpu_count() or 2) - 1)
    t0 = time.time()
    with Pool(workers, initializer=_init, initargs=(path,)) as pool:

        def run(cands):
            nonlocal best_states, best
            out = []
            for chunk in pool.imap_unordered(
                    _batch, [cands[i:i + 40] for i in range(0, len(cands), 40)]):
                out.extend(chunk)
            for states, items in out:
                if states < best_states or (states == best_states and best and
                                            sum(dict(items).values()) < sum(best.values())):
                    best_states, best = states, dict(items)
            return out

        run([{index: 1} for index in safe])
        log('singles: %d (%.0fs)' % (best_states, time.time() - t0))
        cands = []
        for a, b in itertools.combinations_with_replacement(safe, 2):
            d = {a: 1}
            d[b] = d.get(b, 0) + 1
            cands.append(d)
        run(cands)
        log('pairs: %d (%.0fs)' % (best_states, time.time() - t0))
        improved = True
        while improved:
            prev = best_states
            run([dict(best, **{index: best.get(index, 0) + 1}) for index in safe])
            improved = best_states < prev
        log('greedy: %d (%.0fs)' % (best_states, time.time() - t0))
        for restart in range(anneal_restarts):
            rng = random.Random(1000 + restart)
            temperature = restart % 2
            cur, cur_states = dict(best), best_states
            for _ in range(anneal_iters):
                proposals = []
                for _ in range(160):
                    d = dict(cur)
                    r = rng.random()
                    if r < 0.35:
                        index = rng.choice(safe)
                        d[index] = d.get(index, 0) + 1
                    elif r < 0.45 and d:
                        index = rng.choice(list(d))
                        other = rng.choice(safe)
                        d[index] -= 1
                        if not d[index]:
                            del d[index]
                        d[other] = d.get(other, 0) + 1
                    elif r < 0.6:
                        for index in (rng.choice(safe), rng.choice(safe)):
                            d[index] = d.get(index, 0) + 1
                    elif d:
                        index = rng.choice(list(d))
                        d[index] -= 1
                        if not d[index]:
                            del d[index]
                    proposals.append(d)
                out = sorted(run(proposals))
                if out and out[0][0] <= cur_states + temperature:
                    cur_states, cur = out[0][0], dict(out[0][1])
            log('anneal %d: %d (%.0fs)' % (restart, best_states, time.time() - t0))
    return best_states, best


if __name__ == '__main__':
    path = sys.argv[1]
    restarts = int(sys.argv[2]) if len(sys.argv) > 2 else 6
    states, nops = find_layout(path, anneal_restarts=restarts,
                               log=lambda *a: print(*a))
    print('best: %d states' % states)
    for index in sorted(nops):
        print('layout %d %d;' % (index, nops[index]))
