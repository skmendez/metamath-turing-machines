#!/usr/bin/env python3
"""Build the experimental 392-state RH Turing machine."""
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

SOURCE = ROOT / "riemann-rh-392.nql"
OUTPUT = ROOT / "riemann-rh-392.tm"

# One-instruction semantic no-ops inserted before raw main-IR positions.
# They alter only program-counter addresses and BDD sharing.  None of these
# indices directly follows a decrement instruction (whose success path skips
# the next PC slot); see the README for the safety argument.
LAYOUT_NOPS = {
    25: 1,
    31: 1,
    63: 1,
    164: 1,
}
REGISTER_ORDER = ("denom", "lcm", "x", "i", "l", "c", "j", "k")
PC_BITS = 9
EXPECTED_STATES = 392


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
