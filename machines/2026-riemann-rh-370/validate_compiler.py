#!/usr/bin/env python3
"""Bounded execution tests for the optional compiler features this machine
opts into (opt_destructive, opt_remainder_test, opt_dec_fusion,
opt_copy_save, opt_canonical_temps, and builtin_halt_if_gt_destroy).

Each test program is compiled with the repository compiler and executed as a
raw Turing machine; a program that reaches a wrong value hangs in an
infinite loop instead of halting, so "halted" doubles as the assertion."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / ".." / ".." / "compiler"))

import nqlgrammar
import nqlast
from framework import Machine, State

OPTS = ("option opt_destructive; option opt_remainder_test; "
        "option opt_dec_fusion; option opt_copy_save; "
        "option opt_canonical_temps;\n")


def run(src, max_steps=5_000_000, opts=True):
    src = (OPTS if opts else "") + src
    ast, = nqlgrammar.grammar.parseString(src, parseAll=True)
    m1 = nqlast.AstMachine(ast)
    m1.pc_bits = 50
    order = m1.main().order
    m2 = nqlast.AstMachine(ast)
    m2.pc_bits = order
    machine = Machine(m2)
    machine.compress()
    machine.state = machine.entry
    steps = 0
    while isinstance(machine.state, State) and steps < max_steps:
        state = machine.state
        if machine.current_tape == "0":
            write, move, nxt = state.write0, state.move0, state.next0
        else:
            write, move, nxt = state.write1, state.move1, state.next1
        machine.current_tape = write
        machine.state = nxt
        if move == 1:
            machine.left_tape.append(write)
            machine.current_tape = machine.right_tape.pop() if machine.right_tape else "0"
        else:
            machine.right_tape.append(write)
            machine.current_tape = machine.left_tape.pop() if machine.left_tape else "0"
        steps += 1
    return not isinstance(machine.state, State)


arithmetic = r'''
global x; global y; global z; global flag; global i;
proc main() {
 x=5; y=3; x=x+y; if(x!=8){while(true){}}
 x=5; y=7; x=x-y; if(x!=0){while(true){}}
 x=9; y=4; x=x-y; if(x!=5){while(true){}}
 x=5; y=3; x=x*y; if(x!=15){while(true){}}
 x=5; x=x*x; if(x!=25){while(true){}}
 x=4; y=3; z=2; x=x*y+z; if(x!=14){while(true){}}
 y=11; x=y; if(x!=11){while(true){}} if(y!=11){while(true){}}
 i=3; flag=0;
 if(i>0){i=i-1;}else{flag=flag+1;}
 if(i>0){i=i-1;}else{flag=flag+1;}
 if(i>0){i=i-1;}else{flag=flag+1;}
 if(i>0){i=i-1;}else{flag=flag+1;}
 if(i!=0){while(true){}} if(flag!=1){while(true){}}
 return;
}
'''
assert run(arithmetic)
assert run(arithmetic, opts=False)

for a in range(1, 9):
    for b in range(1, 6):
        expected = 1 if a % b else 2
        src = f'''global a; global b; global flag; proc main() {{
          a={a}; b={b}; flag=0;
          if(a != (a / b) * b) {{ flag=1; }} else {{ flag=2; }}
          if(flag != {expected}) {{ while(true) {{}} }}
          return;
        }}'''
        assert run(src, 2_000_000), (a, b)

false_src = 'global l; global c; global m; proc main(){l=3;c=5;m=0;builtin_halt_if_gt_destroy(l,c);m=1;if(m!=1){while(true){}}return;}'
equal_src = 'global l; global c; global m; proc main(){l=4;c=4;m=0;builtin_halt_if_gt_destroy(l,c);m=1;if(m!=1){while(true){}}return;}'
true_src = 'global l; global c; proc main(){l=5;c=3;builtin_halt_if_gt_destroy(l,c);while(true){}}'
assert run(false_src)
assert run(equal_src)
assert run(true_src)

fused_taken = '''global k; global c; global l; proc main() {
  k=2; l=7; c=0;
  if (k > 0) { k = k - 1; c = l; }
  if (k != 1) { while(true) {} }
  if (c != 7) { while(true) {} }
  if (l != 7) { while(true) {} }
  return;
}'''
fused_not_taken = '''global k; global c; global f; proc main() {
  k=0; c=7; f=0;
  if (k > 0) { k = k - 1; c = 9; } else { f = 5; }
  if (k != 0) { while(true) {} }
  if (c != 7) { while(true) {} }
  if (f != 5) { while(true) {} }
  return;
}'''
copysave = '''global a; global b; global c; global d; proc main() {
  a=6; b=4; c=0; d=0;
  c = a + b * a;
  if (c != 30) { while(true) {} }
  if (a != 6) { while(true) {} }
  if (b != 4) { while(true) {} }
  d = (a - b) * (a + b);
  if (d != 20) { while(true) {} }
  c = c - a * b;
  if (c != 6) { while(true) {} }
  a = a * a;
  if (a != 36) { while(true) {} }
  return;
}'''
assert run(fused_taken)
assert run(fused_not_taken)
assert run(copysave, 4_000_000)

print("compiler feature tests passed (arithmetic with and without options, "
      "40 divisibility cases, destructive comparison, decrement fusion, "
      "copy-save stress)")
