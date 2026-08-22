import gdb


class PrintFlags(gdb.Command):
    '''Print x86-64 EFLAGS/RFLAGS or AArch64 CPSR/PSTATE flags in a readable format'''

    DIM = '\x1b[90m'
    RESET = '\x1b[39m'
    X86_FLAGBITS = (
        ('CF', 0), ('PF', 2), ('AF', 4), ('ZF', 6), ('SF', 7),
        ('TF', 8), ('IF', 9), ('DF', 10), ('OF', 11), ('NT', 14),
        ('RF', 16), ('VM', 17), ('AC', 18), ('VIF', 19), ('VIP', 20),
        ('ID', 21),
    )
    AARCH64_FLAGBITS = (
        ('F', 6), ('I', 7), ('A', 8), ('D', 9), ('IL', 20), ('SS', 21),
        ('V', 28), ('C', 29), ('Z', 30), ('N', 31),
    )

    def __init__(self):
        super().__init__('flags', gdb.COMMAND_STATUS)

    def _read_register(self, name):
        frame = gdb.selected_frame()
        try:
            value = frame.read_register(name)
        except (ValueError, gdb.error):
            return None
        return int(value) & 0xffffffff

    def invoke(self, argument, from_tty):
        # gdb exposes the full flags register as either $eflags or $rflags
        # depending on the arch/build; try both before falling back to cpsr.
        flags = self._read_register('eflags')
        if flags is None:
            flags = self._read_register('rflags')

        if flags is not None:
            flagbits = self.X86_FLAGBITS
            extra_fields = [(7, f"IOPL={(flags >> 12) & 0x3}")]
        else:
            flags = self._read_register('cpsr')
            if flags is None:
                print('flags: no eflags/rflags or cpsr register in the selected frame')
                return
            flagbits = self.AARCH64_FLAGBITS
            extra_fields = []

        rendered_flags = [
            name if flags & (1 << bit) else f"{self.DIM}{name}{self.RESET}"
            for name, bit in reversed(flagbits)
        ]
        for index, field in extra_fields:
            rendered_flags.insert(index, field)
        print(' '.join(rendered_flags))


class PrintStdString(gdb.Command):
    '''Prints out a string from a std::string object

    Usage: printstdstring OBJECT [--impl libc++|libstdc++]
    OBJECT is the address of (or a pointer to) the std::string.'''

    def __init__(self):
        super().__init__('printstdstring', gdb.COMMAND_DATA)

    def invoke(self, argument, from_tty):
        args = gdb.string_to_argv(argument)
        impl = None
        obj = None
        i = 0
        while i < len(args):
            if args[i] == '--impl':
                i += 1
                impl = args[i] if i < len(args) else None
            else:
                obj = args[i]
            i += 1
        if obj is None:
            print('printstdstring: expected a std::string object/address')
            return

        impl = impl or self._detect_impl(obj)
        if impl == 'libstdc++':
            # first word points directly at the character data (SSO or heap)
            outstring = _cstr(f'*(char **)({obj})')
        else:
            # libc++: low bit of the first byte flags a long (heap) string
            pseudo_length = _uval(f'*(unsigned char*)({obj})')
            if pseudo_length is not None and pseudo_length & 1:
                outstring = _cstr(f'*(char **)(({obj})+16)')
            else:
                outstring = _cstr(f'(char *)(({obj})+1)')
        print(outstring)

    def _detect_impl(self, obj):
        '''Guess the std::string layout by checking whether the first word is a
        plausible data pointer (libstdc++) or an inline SSO byte (libc++).'''
        first_word = _uval(f'*(unsigned long *)({obj})')
        if first_word is None:
            return 'libc++'
        obj_addr = _uval(f'(unsigned long)({obj})')
        # libstdc++'s _M_p either points into the object's own SSO buffer
        # (obj+16) or to a separate heap allocation; either way it's a real,
        # non-trivial pointer. libc++'s first word is a length/flags byte.
        if obj_addr is not None and (first_word == (obj_addr + 16) or first_word > 0x1000):
            return 'libstdc++'
        return 'libc++'


def _uval(expr):
    try:
        return int(gdb.parse_and_eval(f'(unsigned long)({expr})')) & 0xffffffffffffffff
    except gdb.error:
        return None


def _cstr(expr):
    try:
        value = gdb.parse_and_eval(f'(char *)({expr})')
    except gdb.error:
        return None
    if int(value) == 0:
        return None
    return value.string()


class _StepUntil(gdb.Command):
    '''Base for commands that single-step until a predicate matches the
    current instruction. GDB has no thread-plan API, so this loops stepi.'''

    MAX_STEPS = 100000

    def _current_instruction(self):
        frame = gdb.selected_frame()
        pc = int(frame.pc())
        arch = frame.architecture()
        insn = arch.disassemble(pc)[0]
        return pc, insn['asm'], arch.name()

    def _is_aarch64(self, arch_name):
        return 'aarch64' in arch_name or 'arm' in arch_name

    def _matches(self, pc, asm, arch_name):
        raise NotImplementedError

    def invoke(self, argument, from_tty):
        for _ in range(self.MAX_STEPS):
            try:
                pc, asm, arch_name = self._current_instruction()
            except gdb.error:
                print(f'{self.name}: no running program')
                return
            if self._matches(pc, asm, arch_name):
                gdb.execute('x/i $pc')
                return
            gdb.execute('stepi', to_string=True)
        print(f'{self.name}: gave up after {self.MAX_STEPS} instructions')


class StepToCall(_StepUntil):
    '''Single-step until reaching a call instruction'''
    name = 'step-to-call'

    def __init__(self):
        super().__init__('step-to-call', gdb.COMMAND_RUNNING)

    def _matches(self, pc, asm, arch_name):
        mnem = asm.split(None, 1)[0].lower() if asm else ''
        if self._is_aarch64(arch_name):
            return mnem in ('bl', 'blr')
        return mnem == 'call'


class StepToBranch(_StepUntil):
    '''Single-step until reaching a branch instruction'''
    name = 'step-to-branch'

    # x86: conditional/unconditional jumps, calls, returns, loops. Matched
    # exactly (not by prefix) so mnemonics like bt/bswap/bsr aren't mistaken
    # for branches.
    X86_JCC = (
        'ja', 'jae', 'jb', 'jbe', 'jc', 'jcxz', 'je', 'jecxz', 'jg', 'jge',
        'jl', 'jle', 'jmp', 'jna', 'jnae', 'jnb', 'jnbe', 'jnc', 'jne', 'jng',
        'jnge', 'jnl', 'jnle', 'jno', 'jnp', 'jns', 'jnz', 'jo', 'jp', 'jpe',
        'jpo', 'jrcxz', 'js', 'jz',
    )
    X86_OTHER = (
        'call', 'ret', 'retf', 'iret', 'iretd', 'iretq',
        'loop', 'loope', 'loopne', 'loopnz', 'loopz',
    )
    # AArch64: B/BL/BR/BLR/RET, conditional B.cond (b.eq, ...), and the
    # compare/test-and-branch forms cbz/cbnz/tbz/tbnz.
    AARCH64_BRANCH = ('b', 'bl', 'br', 'blr', 'ret', 'cbz', 'cbnz', 'tbz', 'tbnz')

    def __init__(self):
        super().__init__('step-to-branch', gdb.COMMAND_RUNNING)

    def _matches(self, pc, asm, arch_name):
        mnem = asm.split(None, 1)[0].lower() if asm else ''
        if self._is_aarch64(arch_name):
            # b.eq, b.ne, ... share the b. prefix
            return mnem in self.AARCH64_BRANCH or mnem.startswith('b.')
        return mnem in self.X86_JCC or mnem in self.X86_OTHER


class StepToSyscall(_StepUntil):
    '''Single-step until reaching a system-call instruction'''
    name = 'step-to-syscall'

    def __init__(self):
        super().__init__('step-to-syscall', gdb.COMMAND_RUNNING)

    def _matches(self, pc, asm, arch_name):
        if not asm:
            return False
        parts = asm.split(None, 1)
        mnem = parts[0].lower()
        operands = parts[1] if len(parts) > 1 else ''
        # x86: syscall/sysenter/int 0x80; AArch64: svc
        return mnem in ('syscall', 'sysenter', 'svc') or \
            (mnem == 'int' and '0x80' in operands)


class StepToAntiDebug(_StepUntil):
    '''Single-step until reaching a potential anti-debug instruction (pushf /
    rdtsc). On pushf, masks the trap flag out of the pushed value.'''
    name = 'step-to-antidebug'

    def __init__(self):
        super().__init__('step-to-antidebug', gdb.COMMAND_RUNNING)
        self._pushf_pending = False

    def _matches(self, pc, asm, arch_name):
        if self._pushf_pending:
            self._pushf_pending = False
            # the just-executed pushf placed flags at the top of the stack;
            # clear the trap flag (bit 8) so debugger detection can't see it.
            sp = int(gdb.selected_frame().read_register('sp'))
            try:
                current = int(gdb.parse_and_eval(f'*(unsigned short *){sp}'))
                gdb.execute(f'set *(unsigned short *){sp} = {current & 0xfeff}',
                            to_string=True)
            except gdb.error:
                pass
            return True
        mnem = asm.split(None, 1)[0].lower() if asm else ''
        if 'pushf' in mnem:
            self._pushf_pending = True
            return False
        return 'rdtsc' in mnem


def _install(cmd_cls, label):
    cmd_cls()
    print(f'The "{label}" python command has been installed and is ready for use.')


_install(PrintFlags, 'flags')
_install(PrintStdString, 'printstdstring')
_install(StepToCall, 'step-to-call')
_install(StepToBranch, 'step-to-branch')
_install(StepToSyscall, 'step-to-syscall')
_install(StepToAntiDebug, 'step-to-antidebug')
