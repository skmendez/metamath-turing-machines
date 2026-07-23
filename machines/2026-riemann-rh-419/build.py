#!/usr/bin/env python3
"""Build the experimental 419-state RH Turing machine."""
from pathlib import Path
import contextlib
import hashlib
import sys

ROOT = Path(__file__).resolve().parent
COMPDIR = ROOT / "compiler"
sys.path.insert(0, str(COMPDIR))

import framework
import nqlast
import nqlgrammar
from framework import Machine

SOURCE = ROOT / "riemann-rh-419.nql"
OUTPUT = ROOT / "riemann-rh-419.tm"

# One-instruction semantic no-ops inserted before raw main-IR positions.
# They alter only program-counter addresses and BDD sharing.
LAYOUT_NOPS = {
    22: 1,
    23: 1,
    56: 1,
    99: 1,
    102: 1,
    189: 1,
}
REGISTER_ORDER = ("denom", "lcm", "x", "i", "l", "c")
PC_BITS = 10
EXPECTED_STATES = 419


def build() -> Machine:
    ast, = nqlgrammar.grammar.parse_file(str(SOURCE), parse_all=True)
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
    if states != EXPECTED_STATES:
        raise RuntimeError(f"expected {EXPECTED_STATES} reachable states, got {states}")
    with OUTPUT.open("w", encoding="utf-8") as out, contextlib.redirect_stdout(out):
        machine.print_machine()
    digest = hashlib.sha256(OUTPUT.read_bytes()).hexdigest()
    print(f"wrote {OUTPUT} ({states} states)")
    print(f"sha256 {digest}")


if __name__ == "__main__":
    main()
