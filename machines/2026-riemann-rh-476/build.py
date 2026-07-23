#!/usr/bin/env python3
"""Build the 476-state RH Turing machine from the optimized NQL source."""
from pathlib import Path
import contextlib
import sys

ROOT = Path(__file__).resolve().parent
COMPDIR = ROOT / "compiler"
sys.path.insert(0, str(COMPDIR))

import nqlgrammar
import nqlast
import framework
from framework import Machine

SOURCE = ROOT / "riemann-rh-476.nql"
OUTPUT = ROOT / "riemann-rh-476.tm"

# These no-ops change only instruction addresses.  They were selected by a
# greedy search to maximize sharing in the compiler's BDD dispatcher.
LAYOUT_NOPS = {
    16: 1,
    276: 1,
    280: 1,
    301: 1,
    335: 1,
    358: 1,
    365: 1,
    382: 1,
    402: 1,
    406: 1,
    426: 1,
}
REGISTER_ORDER = ("lcm", "l", "denom", "i", "x", "c")
PC_BITS = 10


def build() -> Machine:
    ast, = nqlgrammar.grammar.parseFile(str(SOURCE), parseAll=True)
    framework.MAIN_INSERT_NOPS = dict(LAYOUT_NOPS)
    builder = nqlast.AstMachine(ast)
    builder.pc_bits = PC_BITS
    for name in REGISTER_ORDER:
        builder.register("_G" + name)
    machine = Machine(builder)
    machine.compress()
    return machine


def main() -> None:
    machine = build()
    states = len(machine.reachable())
    if states != 476:
        raise RuntimeError(f"expected 476 reachable states, got {states}")
    with OUTPUT.open("w", encoding="utf-8") as out, contextlib.redirect_stdout(out):
        machine.print_machine()
    print(f"wrote {OUTPUT} ({states} states)")


if __name__ == "__main__":
    main()
