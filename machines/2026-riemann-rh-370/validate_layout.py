#!/usr/bin/env python3
"""Check that the layout declarations only re-address the machine.

The compiler already refuses layout no-ops that directly follow a decrement
(whose success path skips one program-counter slot).  This script checks the
behavioral half: the built machine must be register-operation
trace-equivalent to a build of the same source with all layout declarations
removed, over a long simulation prefix, and a comparison-flipped variant of
the source must halt with identical traces under both layouts."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / ".." / ".." / "compiler"))

import nqlgrammar
import nqlast
from framework import Machine, State

SOURCE = (ROOT / "riemann.nql").read_text()
MAX_STEPS = 4_000_000


def build(src, keep_layout):
    ast, = nqlgrammar.grammar.parseString(src, parseAll=True)
    if not keep_layout:
        ast.options.layout_nops = {}
    m1 = nqlast.AstMachine(ast)
    m1.pc_bits = 50
    order = m1.main().order
    ast2, = nqlgrammar.grammar.parseString(src, parseAll=True)
    if not keep_layout:
        ast2.options.layout_nops = {}
    m2 = nqlast.AstMachine(ast2)
    m2.pc_bits = order
    machine = Machine(m2)
    machine.compress()
    return machine


def trace(machine, max_steps):
    machine.state = machine.entry
    ops = []
    steps = 0
    prev_regop = False
    while isinstance(machine.state, State) and steps < max_steps:
        st = machine.state
        nm = st.name or ''
        is_start = nm.startswith('reg_incr.') or nm.startswith('reg_decr.')
        if is_start and not prev_regop:
            ops.append(nm)
        prev_regop = is_start
        if machine.current_tape == '0':
            write, move, nxt = st.write0, st.move0, st.next0
        else:
            write, move, nxt = st.write1, st.move1, st.next1
        machine.current_tape = write
        machine.state = nxt
        if move == 1:
            machine.left_tape.append(write)
            machine.current_tape = machine.right_tape.pop() if machine.right_tape else '0'
        else:
            machine.right_tape.append(write)
            machine.current_tape = machine.left_tape.pop() if machine.left_tape else '0'
        steps += 1
    return ops, isinstance(machine.state, State)


ops_a, running_a = trace(build(SOURCE, True), MAX_STEPS)
ops_b, running_b = trace(build(SOURCE, False), MAX_STEPS)
n = min(len(ops_a), len(ops_b))
assert running_a and running_b
assert ops_a[:n] == ops_b[:n], 'register-operation traces diverge'
print('trace-equivalent to the layout-free build over %d register operations' % n)

FLIP = SOURCE.replace('builtin_halt_if_gt_destroy(l, c);',
                      'builtin_halt_if_gt_destroy(c, l);')
assert FLIP != SOURCE
ops_a, running_a = trace(build(FLIP, True), 2_000_000)
ops_b, running_b = trace(build(FLIP, False), 2_000_000)
assert not running_a and not running_b, 'flipped variant should halt'
assert ops_a == ops_b, 'flipped traces differ between layouts'
print('comparison-flipped variant halts with identical %d-operation traces '
      'under both layouts' % len(ops_a))
