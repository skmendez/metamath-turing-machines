#!/usr/bin/env python3
"""Bounded execution tests for compiler peepholes used by the RH machine."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "compiler"))

import framework
import nqlgrammar
import nqlast
from framework import Machine, State


def run(src: str, max_steps: int = 5_000_000):
    framework.MAIN_INSERT_NOPS = {}
    ast, = nqlgrammar.grammar.parse_string(src, parse_all=True)
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
    return not isinstance(machine.state, State), steps, len(machine.reachable())


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
assert run(arithmetic)[0]

for a in range(1, 9):
    for b in range(1, 6):
        expected = 1 if a % b else 2
        src = f'''global a; global b; global flag; proc main() {{
          a={a}; b={b}; flag=0;
          if(a != (a / b) * b) {{ flag=1; }} else {{ flag=2; }}
          if(flag != {expected}) {{ while(true) {{}} }}
          return;
        }}'''
        assert run(src, 2_000_000)[0], (a, b)

false_src = 'global l; global c; global m; proc main(){l=3;c=5;m=0;builtin_halt_if_gt_destroy(l,c);m=1;if(m!=1){while(true){}}return;}'
equal_src = 'global l; global c; global m; proc main(){l=4;c=4;m=0;builtin_halt_if_gt_destroy(l,c);m=1;if(m!=1){while(true){}}return;}'
true_src = 'global l; global c; proc main(){l=5;c=3;builtin_halt_if_gt_destroy(l,c);while(true){}}'
assert run(false_src)[0]
assert run(equal_src)[0]
assert run(true_src)[0]

print("compiler arithmetic, 40 divisibility cases, and destructive comparison: passed")

# Generalized decrement fusion: `if (r > 0) { r = r - 1; REST }` lowers to a
# single decrement whose success path runs REST.  Test taken, not-taken, and
# else-branch cases, plus a countdown while-loop.
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
countdown = '''global j; global s; proc main() {
  j=5; s=0;
  while (j > 0) { j = j - 1; s = s + 2; }
  if (s != 10) { while(true) {} }
  if (j != 0) { while(true) {} }
  return;
}'''
assert run(fused_taken)[0]
assert run(fused_not_taken)[0]
assert run(countdown)[0]

print("generalized decrement fusion and countdown loop: passed")
