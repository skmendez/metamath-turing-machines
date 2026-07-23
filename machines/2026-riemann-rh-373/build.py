#!/usr/bin/env python3
"""Build the experimental 373-state RH Turing machine."""
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

SOURCE = ROOT / "riemann-rh-373.nql"
OUTPUT = ROOT / "riemann-rh-373.tm"

# One-instruction semantic no-ops inserted before raw main-IR positions,
# found by the compiler's layout optimization pass:
#
#     python3 compiler/layoutopt.py riemann-rh-373.nql \
#         denom,lcm,x,i,l,c,j,k 9
#
# Many of these are absorbed by alignment padding that would exist anyway,
# which is why 55 insertions fit in the 512-slot program counter space.
# None of these indices directly follows a decrement instruction (whose
# success path skips the next PC slot); layoutopt only proposes safe
# positions, and validate_layout.py re-checks this.
LAYOUT_NOPS = {
    16: 1, 20: 1, 22: 1, 25: 1, 26: 4, 30: 1, 31: 1, 33: 2, 41: 1,
    45: 1, 46: 1, 47: 1, 48: 2, 49: 1, 50: 1, 51: 1, 52: 1, 63: 1,
    65: 1, 69: 1, 77: 2, 80: 1, 82: 1, 85: 2, 94: 1, 96: 1, 97: 1,
    103: 1, 107: 3, 108: 1, 112: 1, 114: 1, 122: 1, 130: 2, 131: 1,
    139: 1, 141: 2, 147: 2, 148: 1, 156: 1, 164: 3,
}
REGISTER_ORDER = ("denom", "lcm", "x", "i", "l", "c", "j", "k")
PC_BITS = 9
EXPECTED_STATES = 373


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
