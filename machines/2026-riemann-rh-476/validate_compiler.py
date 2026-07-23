import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'compiler'))
import nqlgrammar,nqlast
from framework import Machine,State

def run(src,max_steps=5_000_000):
 ast,=nqlgrammar.grammar.parseString(src,parseAll=True)
 m1=nqlast.AstMachine(ast);m1.pc_bits=50;order=m1.main().order
 m2=nqlast.AstMachine(ast);m2.pc_bits=order
 mach=Machine(m2);mach.compress();mach.state=mach.entry
 steps=0
 while isinstance(mach.state,State) and steps<max_steps:
  st=mach.state
  if mach.current_tape=='0':w,mv,nx=st.write0,st.move0,st.next0
  else:w,mv,nx=st.write1,st.move1,st.next1
  mach.current_tape=w;mach.state=nx
  if mv==1:
   mach.left_tape.append(w);mach.current_tape=mach.right_tape.pop() if mach.right_tape else '0'
  else:
   mach.right_tape.append(w);mach.current_tape=mach.left_tape.pop() if mach.left_tape else '0'
  steps+=1
 return not isinstance(mach.state,State),steps,len(mach.reachable())

arith='''
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
print('arith',run(arith))

for a in range(1,9):
 for b in range(1,6):
  exp=1 if a%b else 2
  src=f'''global a; global b; global flag; proc main() {{
   a={a}; b={b}; flag=0;
   if(a != (a / b) * b) {{ flag=1; }} else {{ flag=2; }}
   if(flag != {exp}) {{ while(true) {{}} }}
   return;
  }}'''
  halted,steps,n=run(src,2_000_000)
  if not halted:
   print('DIV FAIL',a,b,steps,n);sys.exit(1)
print('divisibility 40/40 passed')

false_src='''global l; global c; global m; proc main(){l=3;c=5;m=0;builtin_halt_if_gt_destroy(l,c);m=1;if(m!=1){while(true){}}return;}'''
true_src='''global l; global c; proc main(){l=5;c=3;builtin_halt_if_gt_destroy(l,c);while(true){}}'''
equal_src='''global l; global c; global m; proc main(){l=4;c=4;m=0;builtin_halt_if_gt_destroy(l,c);m=1;if(m!=1){while(true){}}return;}'''
print('destroy false',run(false_src))
print('destroy equal',run(equal_src))
print('destroy true',run(true_src))
