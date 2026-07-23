"""Implements an EDSL for constructing Turing machines without subclassing
MachineBuilder."""

from framework import Machine, MachineOptions, MachineBuilder, Goto, Label, memo

class Node:
    """Base class for all Not Quite Laconic syntax nodes."""
    def __init__(self, **kwargs):
        self.lineno = kwargs.pop('lineno', 0)
        self.children = kwargs.pop('children', [])
        assert not kwargs
        self.check_children()

    child_types = ()

    def check_children(self):
        """Verifies that the node has the correct number and types of child
        nodes."""
        if isinstance(self.child_types, tuple):
            assert len(self.children) == len(self.child_types)
            for child, ctype in zip(self.children, self.child_types):
                assert isinstance(child, ctype)
        else:
            for child in self.children:
                assert isinstance(child, self.child_types)

    def error(self, message):
        """Print an error using the line number of this node."""
        raise str(self.lineno) + ": " + message

    repr_suppress = ('lineno','children')

    def __repr__(self):
        result = []
        result.append(self.__class__.__name__ + '(')
        result.append(('\n  ',''))

        has_items = False
        for k, v in vars(self).items():
            if k in self.repr_suppress:
                continue
            result.append(k + '=' + repr(v).replace('\n', '\n  '))
            result.append((',\n  ', ', '))
            has_items = True

        if self.children:
            result.append('children=[')
            result.append(('\n    ', ''))
            for child in self.children:
                result.append(repr(child).replace('\n', '\n    '))
                result.append((',\n    ', ', '))
            result.pop()
            result.append(']')
        elif has_items:
            result.pop()
        result.append(')')

        result = [(tup if isinstance(tup, tuple) else (tup, tup)) for tup in result]
        broken = ''.join(a for a, b in result)
        unbroken = ''.join(b for a, b in result)
        if len(unbroken) < 80 and '\n' not in unbroken:
            return unbroken
        else:
            return broken

class NatExpr(Node):
    """Base class for expressions which result in a natural number.

    Sub classes should define an emit method which generates code to put the
    evaluation result in a caller-allocated temporary register.

    TODO: context-sensitive code generation and peephole optimization will
    reduce the state count here quite a bit."""

    def emit_nat(self, state, target):
        """Calculate the value of this expression into the target register,
        which is guaranteed to be zero by the caller unless is_additive
        returns True."""
        temps = []
        for child in self.children:
            temp = state.get_temp()
            temps.append(temp)
            child.emit_nat(state, temp)
        self.emit_nat_op(state, target, temps)
        for temp in temps:
            state.put_temp(temp)

    def emit_nat_add(self, state, out):
        if self.is_additive():
            self.emit_nat(state, out)
        else:
            temp = state.get_temp()
            self.emit_nat(state, temp)
            state.emit_transfer(temp, out)
            state.put_temp(temp)

    def emit_nat_op(self, state, target, temps):
        """Calculate the value of this expression with the arguments already
        evaluated.

        To customize argument evaluation, override emit_nat instead."""
        raise NotImplementedError()

    def is_additive(self):
        """Returns True if emit_nat actually just adds and is safe for non-zero targets."""
        return False

class Reg(NatExpr):
    def __init__(self, **kwargs):
        self.name = kwargs.pop('name')
        super().__init__(**kwargs)

    def is_additive(self):
        return True

    def emit_nat_op(self, state, target, _args):
        save = state.get_temp()
        reg = state.resolve(self.name)
        state.emit_transfer(reg, target, save)
        state.emit_transfer(save, reg)
        state.put_temp(save)

class Mul(NatExpr):
    child_types = (NatExpr, NatExpr)
    def is_additive(self):
        return True

    def emit_nat(self, state, out):
        lhs_ex, rhs_ex = self.children
        if lhs_ex.is_additive() and not rhs_ex.is_additive():
            lhs_ex, rhs_ex = rhs_ex, lhs_ex
        lhs = state.get_temp()
        lhs_ex.emit_nat(state, lhs)
        again = state.gensym()
        done = state.gensym()
        state.emit_label(again)
        state.emit_dec(lhs)
        state.emit_goto(done)
        rhs_ex.emit_nat_add(state, out)
        state.emit_goto(again)
        state.emit_label(done)
        state.put_temp(lhs)

class Div(NatExpr):
    child_types = (NatExpr, NatExpr)
    def is_additive(self):
        return True

    def emit_nat(self, state, out):
        dividend_ex, divisor_ex = self.children

        dividend = state.get_temp()
        divisor = state.get_temp()

        loop_quotient = state.gensym()
        loop_divisor = state.gensym()
        exhausted = state.gensym()
        full_divisor = state.gensym()

        dividend_ex.emit_nat(state, dividend)

        state.emit_label(loop_quotient)
        divisor_ex.emit_nat(state, divisor)
        state.emit_label(loop_divisor)
        state.emit_dec(divisor)
        state.emit_goto(full_divisor)
        state.emit_dec(dividend)
        state.emit_goto(exhausted)
        state.emit_goto(loop_divisor)
        state.emit_label(full_divisor)

        state.emit_inc(out)
        state.emit_goto(loop_quotient)
        state.emit_label(exhausted)
        state.emit_transfer(divisor)

        state.put_temp(dividend)
        state.put_temp(divisor)

class Add(NatExpr):
    child_types = NatExpr
    def is_additive(self):
        return True

    def emit_nat(self, state, out):
        for child in self.children:
            child.emit_nat_add(state, out)

class Lit(NatExpr):
    def __init__(self, **kwargs):
        self.value = kwargs.pop('value')
        super().__init__(**kwargs)

    def is_additive(self):
        return True

    def emit_nat_op(self, state, out, _args):
        for _ in range(self.value):
            state.emit_inc(out)

class Monus(NatExpr):
    """Subtracts the right argument from the left argument, clamping to zero
    (also known as the "monus" operator)."""
    child_types = (NatExpr, NatExpr)

    def emit_nat_op(self, state, out, args):
        lhs, rhs = args
        # TODO: forward directly out to lhs
        state.emit_transfer(lhs, out)
        loop = state.gensym()
        done = state.gensym()
        state.emit_label(loop)
        state.emit_dec(rhs)
        state.emit_goto(done)
        state.emit_dec(out)
        state.emit_noop()
        state.emit_goto(loop)
        state.emit_label(done)

class BoolExpr(Node):
    """Base class for expressions which result in a boolean test."""

    def emit_test(self, state, target, invert):
        """Evaluate the test and jump to label if the test is true, subject to
        the inversion flag."""
        temps = []
        for child in self.children:
            temp = state.get_temp()
            temps.append(temp)
            child.emit_nat(state, temp)
        self.emit_test_op(state, target, invert, temps)
        for temp in temps:
            state.put_temp(temp)

    def emit_test_op(self, state, target, invert, temps):
        """Calculate the value of this test with the arguments already
        evaluated.

        To customize argument evaluation, override emit_test instead."""
        raise NotImplementedError()

class CompareBase(BoolExpr):
    child_types = (NatExpr, NatExpr)
    jump_lt = False
    jump_eq = False
    jump_gt = False

    def emit_compare_reg_0(self, state, label, j_eq, j_gt, name):
        # LT is not possible here

        no_jump = state.gensym()
        state.emit_dec(state.resolve(name))
        state.emit_goto(label if j_eq else no_jump)
        state.emit_inc(state.resolve(name))
        state.emit_goto(label if j_gt else no_jump)
        state.emit_label(no_jump)

    def emit_compare_lit(self, state, label, j_lt, j_eq, j_gt, lhs_ex, rhs_val):
        if isinstance(lhs_ex, Reg) and rhs_val == 0:
            return self.emit_compare_reg_0(state, label, j_eq, j_gt, lhs_ex.name)

        lhs = state.get_temp()
        lhs_ex.emit_nat(state, lhs)

        no_jump = state.gensym()
        for _ in range(rhs_val):
            state.emit_dec(lhs)
            state.emit_goto(label if j_lt else no_jump)

        if j_eq != j_gt:
            state.emit_dec(lhs)
            state.emit_goto(label if j_eq else no_jump)

        state.emit_transfer(lhs)
        if j_gt:
            state.emit_goto(label)
        state.emit_label(no_jump)
        state.put_temp(lhs)

    def emit_test(self, state, label, invert):
        lhs_ex, rhs_ex = self.children

        jump_lt, jump_eq, jump_gt = self.jump_lt ^ invert, self.jump_eq ^ invert, \
            self.jump_gt ^ invert

        if isinstance(rhs_ex, Lit):
            return self.emit_compare_lit(state, label, jump_lt, jump_eq, jump_gt, lhs_ex, rhs_ex.value)
        if isinstance(lhs_ex, Lit):
            return self.emit_compare_lit(state, label, jump_gt, jump_eq, jump_lt, rhs_ex, lhs_ex.value)

        lhs = state.get_temp()
        lhs_ex.emit_nat(state, lhs)
        rhs = state.get_temp()
        rhs_ex.emit_nat(state, rhs)

        monus = state.gensym()
        not_less = state.gensym()
        is_less = state.gensym()
        no_jump = state.gensym()

        state.emit_label(monus)
        state.emit_dec(rhs)
        state.emit_goto(not_less)
        state.emit_dec(lhs)
        state.emit_goto(is_less)
        state.emit_goto(monus)

        state.emit_label(not_less)
        if jump_eq != jump_gt:
            state.emit_dec(lhs)
            state.emit_goto(label if jump_eq else no_jump)
        state.emit_transfer(lhs)
        state.emit_goto(label if jump_gt else no_jump)

        state.emit_label(is_less)
        state.emit_transfer(rhs)
        state.emit_goto(label if jump_lt else no_jump)

        state.emit_label(no_jump)

        state.put_temp(lhs)
        state.put_temp(rhs)

class Less(CompareBase):
    jump_lt = True

class LessEqual(CompareBase):
    jump_lt = True
    jump_eq = True

class Greater(CompareBase):
    jump_gt = True

class GreaterEqual(CompareBase):
    jump_eq = True
    jump_gt = True

class Equal(CompareBase):
    jump_eq = True

class NotEqual(CompareBase):
    jump_lt = True
    jump_gt = True

    @staticmethod
    def _same_reg(a, b):
        return isinstance(a, Reg) and isinstance(b, Reg) and a.name == b.name

    def _divisibility_pattern(self):
        # Recognize a != (a / b) * b (allowing the multiplication operands to
        # be swapped).  This is exactly the test "b does not divide a".
        lhs, rhs = self.children
        if not isinstance(lhs, Reg) or not isinstance(rhs, Mul) or len(rhs.children) != 2:
            return None
        for div, factor in (rhs.children, tuple(reversed(rhs.children))):
            if not isinstance(div, Div) or len(div.children) != 2:
                continue
            dividend, divisor = div.children
            if self._same_reg(lhs, dividend) and self._same_reg(divisor, factor):
                return lhs, divisor
        return None

    def emit_test(self, state, label, invert):
        pattern = self._divisibility_pattern()
        if pattern is None:
            return super().emit_test(state, label, invert)

        dividend_ex, divisor_ex = pattern
        dividend = state.get_temp()
        divisor = state.get_temp()
        dividend_ex.emit_nat(state, dividend)

        outer = state.gensym()
        inner = state.gensym()
        divisible = state.gensym()
        nondivisible = state.gensym()
        no_jump = state.gensym()

        # Repeatedly subtract the divisor from a private dividend copy.  Test
        # for zero only between complete subtractions, so exact multiples take
        # the divisible branch while a partial final subtraction does not.
        state.emit_label(outer)
        state.emit_dec(dividend)
        state.emit_goto(divisible)
        state.emit_inc(dividend)
        divisor_ex.emit_nat(state, divisor)

        state.emit_label(inner)
        state.emit_dec(divisor)
        state.emit_goto(outer)
        state.emit_dec(dividend)
        state.emit_goto(nondivisible)
        state.emit_goto(inner)

        state.emit_label(divisible)
        state.emit_goto(label if invert else no_jump)

        state.emit_label(nondivisible)
        state.emit_transfer(divisor)
        state.emit_goto(label if not invert else no_jump)

        state.emit_label(no_jump)
        state.put_temp(divisor)
        state.put_temp(dividend)

class Not(BoolExpr):
    child_types = (BoolExpr,)

    def emit_test(self, state, label, invert):
        self.children[0].emit_test(state, label, not invert)

class And(BoolExpr):
    child_types = (BoolExpr,BoolExpr)
    is_or = False

    def emit_test(self, state, label, invert):
        left, right = self.children
        if invert ^ self.is_or:
            left.emit_test(state, label, True ^ self.is_or)
            right.emit_test(state, label, True ^ self.is_or)
        else:
            dont_jump = state.gensym()
            left.emit_test(state, dont_jump, True ^ self.is_or)
            right.emit_test(state, label, False ^ self.is_or)
            state.emit_label(dont_jump)

class Or(And):
    is_or = True

class BoolConst(BoolExpr):
    def emit_test(self, state, label, invert):
        if self.value ^ invert:
            state.emit_goto(label)

class TrueConst(BoolConst):
    value = True

class FalseConst(BoolConst):
    value = False

class VoidExpr(Node):
    """Base class for expressions which return no value."""

    def emit_stmt(self, state):
        raise NotImplementedError()

class Assign(VoidExpr):
    child_types = (Reg, NatExpr)

    @staticmethod
    def _uses(node, name):
        if isinstance(node, Reg):
            return node.name == name
        return any(Assign._uses(ch, name) for ch in getattr(node, 'children', ()))

    def emit_aug_op(self, state, lhs, rhs):
        if not (isinstance(rhs, Add) or isinstance(rhs, Monus)):
            return
        if len(rhs.children) != 2:
            return
        rhs_l, rhs_r = rhs.children
        if not (isinstance(rhs_l, Reg) and rhs_l.name == lhs.name):
            return

        out = state.resolve(lhs.name)
        if isinstance(rhs_r, Lit):
            for _ in range(rhs_r.value):
                if isinstance(rhs, Monus):
                    state.emit_dec(out)
                    state.emit_noop()
                else:
                    state.emit_inc(out)
            return True

        if self._uses(rhs_r, lhs.name):
            return

        if isinstance(rhs, Add):
            # x = x + e: add e directly into x, preserving e's inputs.
            rhs_r.emit_nat_add(state, out)
            return True

        # x = x - e (monus): consume x directly instead of copying it to an
        # output temporary and later copying the result back.
        sub = state.get_temp()
        rhs_r.emit_nat(state, sub)
        loop = state.gensym()
        done = state.gensym()
        state.emit_label(loop)
        state.emit_dec(sub)
        state.emit_goto(done)
        state.emit_dec(out)
        state.emit_noop()
        state.emit_goto(loop)
        state.emit_label(done)
        state.put_temp(sub)
        return True

    def emit_horner(self, state, lhs, rhs):
        # x = x*y + z, where y and z do not depend on x.
        if not isinstance(rhs, Add) or len(rhs.children) != 2:
            return
        mul, add = rhs.children
        if not isinstance(mul, Mul) or len(mul.children) != 2:
            return
        a, b = mul.children
        if isinstance(a, Reg) and a.name == lhs.name:
            factor = b
        elif isinstance(b, Reg) and b.name == lhs.name:
            factor = a
        else:
            return
        if self._uses(factor, lhs.name) or self._uses(add, lhs.name):
            return

        outreg = state.resolve(lhs.name)
        result = state.get_temp()
        again = state.gensym()
        done = state.gensym()
        state.emit_label(again)
        state.emit_dec(outreg)
        state.emit_goto(done)
        factor.emit_nat_add(state, result)
        state.emit_goto(again)
        state.emit_label(done)
        add.emit_nat_add(state, result)
        state.emit_transfer(result, outreg)
        state.put_temp(result)
        return True

    def emit_self_mul(self, state, lhs, rhs):
        if not isinstance(rhs, Mul) or len(rhs.children) != 2:
            return
        a, b = rhs.children
        lhs_a = isinstance(a, Reg) and a.name == lhs.name
        lhs_b = isinstance(b, Reg) and b.name == lhs.name
        if not (lhs_a or lhs_b):
            return

        outreg = state.resolve(lhs.name)
        if lhs_a and lhs_b:
            # Square in place.  Split x into a loop counter and a preserved
            # multiplicand, leaving x clear for the result.
            counter = state.get_temp()
            multiplicand = state.get_temp()
            save = state.get_temp()
            state.emit_transfer(outreg, counter, multiplicand)
            again = state.gensym()
            done = state.gensym()
            state.emit_label(again)
            state.emit_dec(counter)
            state.emit_goto(done)
            state.emit_transfer(multiplicand, outreg, save)
            state.emit_transfer(save, multiplicand)
            state.emit_goto(again)
            state.emit_label(done)
            state.emit_transfer(multiplicand)
            state.put_temp(save)
            state.put_temp(multiplicand)
            state.put_temp(counter)
            return True

        other = b if lhs_a else a
        if self._uses(other, lhs.name):
            return
        # x = x*y: consume x as the loop counter, build the result in a temp,
        # and move it back once.
        result = state.get_temp()
        again = state.gensym()
        done = state.gensym()
        state.emit_label(again)
        state.emit_dec(outreg)
        state.emit_goto(done)
        other.emit_nat_add(state, result)
        state.emit_goto(again)
        state.emit_label(done)
        state.emit_transfer(result, outreg)
        state.put_temp(result)
        return True

    def emit_stmt(self, state):
        lhs, rhs = self.children
        if isinstance(rhs, Lit):
            state.emit_transfer(state.resolve(lhs.name))
            rhs.emit_nat(state, state.resolve(lhs.name))
        elif self.emit_aug_op(state, lhs, rhs):
            pass
        elif self.emit_horner(state, lhs, rhs):
            pass
        elif self.emit_self_mul(state, lhs, rhs):
            pass
        elif not self._uses(rhs, lhs.name):
            # The old destination is dead, so clear it first and construct the
            # new value directly in place.
            out = state.resolve(lhs.name)
            state.emit_transfer(out)
            rhs.emit_nat(state, out)
        else:
            temp = state.get_temp()
            rhs.emit_nat(state, temp)
            state.emit_transfer(state.resolve(lhs.name))
            state.emit_transfer(temp, state.resolve(lhs.name))
            state.put_temp(temp)

class Block(VoidExpr):
    child_types = VoidExpr
    def emit_stmt(self, state):
        for st in self.children:
            st.emit_stmt(state)

class WhileLoop(VoidExpr):
    child_types = (BoolExpr, VoidExpr)
    def emit_stmt(self, state):
        test, block = self.children
        exit = state.gensym()
        again = state.gensym()
        state.emit_label(again)
        test.emit_test(state, exit, True)
        block.emit_stmt(state)
        state.emit_goto(again)
        state.emit_label(exit)

class IfThen(VoidExpr):
    child_types = (BoolExpr, VoidExpr, VoidExpr)

    @staticmethod
    def _is_dec_one(stmt, name):
        if not isinstance(stmt, Block) or len(stmt.children) < 1:
            return False
        a = stmt.children[0]
        if not isinstance(a, Assign):
            return False
        lhs, rhs = a.children
        return (isinstance(lhs, Reg) and lhs.name == name and
                isinstance(rhs, Monus) and len(rhs.children) == 2 and
                isinstance(rhs.children[0], Reg) and rhs.children[0].name == name and
                isinstance(rhs.children[1], Lit) and rhs.children[1].value == 1)

    def emit_stmt(self, state):
        test, then_, else_ = self.children
        # Fuse `if (r > 0) { r = r - 1; } else { ... }`.  A decrement
        # primitive already branches on zero and performs the decrement when
        # successful, so restoring r for the comparison and decrementing it a
        # second time is pure overhead.
        if (isinstance(test, Greater) and len(test.children) == 2 and
            isinstance(test.children[0], Reg) and
            isinstance(test.children[1], Lit) and test.children[1].value == 0 and
            self._is_dec_one(then_, test.children[0].name)):
            l_else = state.gensym()
            l_end = state.gensym()
            state.emit_dec(state.resolve(test.children[0].name))
            state.emit_goto(l_else)
            for rest in then_.children[1:]:
                rest.emit_stmt(state)
            state.emit_goto(l_end)
            state.emit_label(l_else)
            else_.emit_stmt(state)
            state.emit_label(l_end)
            return

        l_else = state.gensym()
        l_then = state.gensym()
        test.emit_test(state, l_else, True)
        then_.emit_stmt(state)
        state.emit_goto(l_then)
        state.emit_label(l_else)
        else_.emit_stmt(state)
        state.emit_label(l_then)

class SwitchArm(Block):
    def __init__(self, **kwargs):
        self.case = kwargs.pop('case')
        assert self.case is None or isinstance(self.case, int) and self.case >= 0
        super().__init__(**kwargs)

class Break(VoidExpr):
    def emit_stmt(self, state):
        assert state.break_label
        state.emit_goto(state.break_label)

class Switch(VoidExpr):
    def check_children(self):
        head, *arms = self.children
        assert isinstance(head, NatExpr)
        for arm in arms:
            assert isinstance(arm, SwitchArm)

    def emit_stmt(self, state):
        head_ex, *arms_ex = self.children

        head = state.get_temp()
        head_ex.emit_nat(state, head)

        arm_labels = {}
        for arm in arms_ex:
            if arm.case is None or arm.case in arm_labels:
                continue
            arm_labels[arm.case] = state.gensym()

        default_label = state.gensym()

        for count in range(max(arm_labels)):
            state.emit_dec(head)
            state.emit_goto(arm_labels.get(count, default_label))

        state.emit_transfer(head)
        state.emit_goto(default_label)
        state.put_temp(head)

        save_break_label, state.break_label = state.break_label, state.gensym()

        for arm in arms_ex:
            if arm.case is None:
                assert default_label
                state.emit_label(default_label)
                arm.emit_stmt(state)
                default_label = None
            else:
                assert arm.case in arm_labels
                state.emit_label(arm_labels.pop(arm.case))
                arm.emit_stmt(state)

        if default_label:
            state.emit_label(default_label)
        state.emit_label(state.break_label)
        state.break_label = save_break_label

class Call(VoidExpr):
    child_types = Reg
    def __init__(self, **kwargs):
        self.func = kwargs.pop('func')
        super().__init__(**kwargs)

    def emit_stmt(self, state):
        state.emit_call(self.func, [state.resolve(arg.name) for arg in self.children])

class Return(VoidExpr):
    def emit_stmt(self, state):
        state.emit_return()

class GlobalNode(Node):
    pass

class ProcDef(GlobalNode):
    def __init__(self, **kwargs):
        self.name = kwargs.pop('name')
        self.parameters = kwargs.pop('parameters')
        super().__init__(**kwargs)

    child_types = (VoidExpr,)

class Option(GlobalNode):
    def __init__(self, **kwargs):
        self.name = kwargs.pop('name')
        super().__init__(**kwargs)

class GlobalReg(GlobalNode):
    def __init__(self, **kwargs):
        self.name = kwargs.pop('name')
        super().__init__(**kwargs)

class Program(Node):
    child_types = GlobalNode
    repr_suppress = Node.repr_suppress + ('by_name', 'options',)
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.by_name = {node.name: node for node in self.children if isinstance(node,ProcDef)}
        self.options = MachineOptions()
        for node in self.children:
            if isinstance(node,Option):
                if node.name in MachineOptions.boolean:
                    setattr(self.options, node.name, True)
                else:
                    raise Exception("unknown option", node.name, self.lineno)

class SubEmitter:
    """Tracks state while lowering a _SubDef to a call sequence."""

    def __init__(self, register_map, machine_builder, name):
        self._register_map = register_map
        self._machine_builder = machine_builder
        self._scratch_next = 0
        self._scratch_used = []
        self._scratch_free = []
        self._output = []
        self._return_label = None
        self.break_label = None
        self.name = name

    def emit_transfer(self, *regs):
        self._output.append(self._machine_builder.transfer(*regs))

    def emit_halt(self):
        self._output.append(self._machine_builder.halt())

    def emit_noop(self):
        self._output.append(self._machine_builder.noop(0))

    def emit_label(self, label):
        self._output.append(Label(label))

    def emit_goto(self, label):
        self._output.append(Goto(label))

    def emit_return(self):
        if self.name == 'main' and not self._machine_builder.options.implicit_halt:
            self.emit_halt()
            return
        if not self._return_label:
            self._return_label = self.gensym()
        self.emit_goto(self._return_label)

    def close_return(self):
        if self._return_label:
            self.emit_label(self._return_label)

    def emit_inc(self, reg):
        self._output.append(reg.inc)

    def emit_dec(self, reg):
        self._output.append(reg.dec)

    def emit_call(self, func_name, args):
        assert len(self._scratch_used) == 0
        if func_name.startswith('noop_'):
            self._output.append(self._machine_builder.noop(int(func_name[5:])))
        elif func_name.startswith('builtin_'):
            getattr(self, 'emit_' + func_name)(*args)
        else:
            func = self._machine_builder.instantiate(func_name, tuple(arg.name for arg in args))
            self._output.append(func)

    def emit_builtin_halt_if_gt_destroy(self, lhs, rhs):
        """Halt iff lhs > rhs, consuming both registers on the nonhalting path."""
        loop = self.gensym()
        rhs_empty = self.gensym()
        done = self.gensym()
        self.emit_label(loop)
        self.emit_dec(rhs)
        self.emit_goto(rhs_empty)
        self.emit_dec(lhs)
        self.emit_goto(done)
        self.emit_goto(loop)
        self.emit_label(rhs_empty)
        self.emit_dec(lhs)
        self.emit_goto(done)
        self.emit_halt()
        self.emit_label(done)

    def emit_builtin_pair(self, out, in1, in2):
        t0 = self.get_temp()
        extract = self.gensym()
        nextdiag = self.gensym()
        done = self.gensym()
        self.emit_label(extract)
        self.emit_dec(in1)
        self.emit_goto(nextdiag)
        self.emit_inc(t0)
        self.emit_inc(in2)
        self.emit_goto(extract)
        self.emit_label(nextdiag)
        self.emit_dec(in2)
        self.emit_goto(done)
        self.emit_inc(t0)
        self.emit_transfer(in2, in1)
        self.emit_goto(extract)
        self.emit_label(done)
        self.emit_transfer(out)
        self.emit_transfer(t0, out)
        self.put_temp(t0)

    def emit_builtin_unpair(self, out1, out2, in1):
        t0 = self.get_temp()
        self.emit_transfer(in1, t0)
        self.emit_transfer(out1)
        self.emit_transfer(out2)

        nextdiag = self.gensym()
        nextstep = self.gensym()
        done = self.gensym()

        self.emit_label(nextstep)
        self.emit_dec(t0)
        self.emit_goto(done)
        self.emit_inc(out1)
        self.emit_dec(out2)
        self.emit_goto(nextdiag)
        self.emit_goto(nextstep)
        self.emit_label(nextdiag)
        self.emit_transfer(out1, out2)
        self.emit_goto(nextstep)
        self.emit_label(done)

        self.put_temp(t0)

    def emit_builtin_move(self, to_, from_):
        t0 = self.get_temp()
        self.emit_transfer(from_, t0)
        self.emit_transfer(to_)
        self.emit_transfer(t0, to_)
        self.put_temp(t0)

    def resolve(self, regname):
        reg = self._register_map.get(regname) or '_G' + regname
        return self._machine_builder.register(reg) if isinstance(reg,str) else reg

    def put_temp(self, reg):
        self._scratch_used.remove(reg)
        self._scratch_free.append(reg)

    def get_temp(self):
        if self._scratch_free:
            var = self._scratch_free.pop()
        else:
            self._scratch_next += 1
            var = self._machine_builder.register('_scratch_' + str(self._scratch_next))
        self._scratch_used.append(var)
        return var

    def gensym(self):
        self._machine_builder._gensym += 1
        return 'gen' + str(self._machine_builder._gensym)

class AstMachine(MachineBuilder):
    def __init__(self, ast):
        super().__init__(ast.options)
        self._ast = ast
        self._fun_instances = {}
        self._gensym = 0

    @memo
    def instantiate(self, name, args):
        defn = self._ast.by_name[name]
        assert isinstance(defn, ProcDef)
        emit = SubEmitter(dict(zip(defn.parameters, args)), self, name)
        defn.children[0].emit_stmt(emit)
        emit.close_return()
        if name == 'main' and self.options.implicit_halt:
            emit.emit_halt()
        return self.makesub(name=name + '(' + ','.join(args) + ')', *emit._output)

    def main(self):
        return self.instantiate('main', ())

def harness(ast, args):
    mach1 = AstMachine(ast)
    mach1.pc_bits = 50
    order = mach1.main().order
    mach2 = AstMachine(ast)
    mach2.pc_bits = order
    Machine(mach2).harness(args)
