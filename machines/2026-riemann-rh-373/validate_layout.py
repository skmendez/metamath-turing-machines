#!/usr/bin/env python3
"""Check the safety and behavior of the pinned LAYOUT_NOPS.

1. No insertion index may directly follow a decrement instruction in the
   pre-insertion parts list (a decrement's success path skips one PC slot,
   so a no-op there would corrupt control flow).
2. The built machine must be register-operation trace-equivalent to the
   no-op-free build of the same source over a long simulation prefix.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "compiler"))

import framework
import nqlast
import nqlgrammar
from framework import Machine, State, Label

from build import LAYOUT_NOPS, REGISTER_ORDER, PC_BITS, SOURCE

MAX_STEPS = 4_000_000


def make(nops):
    framework.MAIN_INSERT_NOPS = dict(nops)
    ast, = nqlgrammar.grammar.parse_file(str(SOURCE), parse_all=True)
    builder = nqlast.AstMachine(ast)
    builder.pc_bits = PC_BITS
    for name in REGISTER_ORDER:
        builder.register("_G" + name)
    machine = Machine(builder)
    machine.compress()
    return machine


def capture_parts():
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
        make({})
    finally:
        framework.MachineBuilder.makesub = orig
    return box['parts']


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
            w, mv, nx = st.write0, st.move0, st.next0
        else:
            w, mv, nx = st.write1, st.move1, st.next1
        machine.current_tape = w
        machine.state = nx
        if mv == 1:
            machine.left_tape.append(w)
            machine.current_tape = machine.right_tape.pop() if machine.right_tape else '0'
        else:
            machine.right_tape.append(w)
            machine.current_tape = machine.left_tape.pop() if machine.left_tape else '0'
        steps += 1
    return ops, isinstance(machine.state, State)


parts = capture_parts()
for ix in sorted(LAYOUT_NOPS):
    j = ix - 1
    while j >= 0 and isinstance(parts[j], Label):
        j -= 1
    assert not (j >= 0 and getattr(parts[j], 'is_decrement', False)), \
        f'no-op at index {ix} follows a decrement'
print(f'{sum(LAYOUT_NOPS.values())} no-ops at {len(LAYOUT_NOPS)} indices: all decrement-safe')

m_with = make(LAYOUT_NOPS)
m_without = make({})
ops_a, running_a = trace(m_with, MAX_STEPS)
ops_b, running_b = trace(m_without, MAX_STEPS)
n = min(len(ops_a), len(ops_b))
assert running_a and running_b
assert ops_a[:n] == ops_b[:n], 'register-operation traces diverge'
print(f'trace-equivalent to the no-op-free build over {n} register operations')
