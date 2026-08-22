import argparse
import os.path
import shlex
import struct

import lldb


def getValue(debugger, valstr):
    target = debugger.GetSelectedTarget()
    result = target.EvaluateExpression(f"(unsigned long)({valstr})")
    if result.IsValid() and result.GetError().Success():
        return result.GetValueAsUnsigned()
    return None


def getCstr(debugger, valstr):
    target = debugger.GetSelectedTarget()
    result = target.EvaluateExpression(f"(char *)({valstr})")
    if result.IsValid() and result.GetError().Success():
        return result.GetSummary()
    return None


def nsviewtree(debugger, command, result, internal_dict):
    '''
    Prints a debug view of the hierarchy of an NSView
    '''
    parser = argparse.ArgumentParser(prog=__name__)
    parser.add_argument("object", help="object to dump nsview tree")
    args = parser.parse_args(shlex.split(command))

    ci = debugger.GetCommandInterpreter()
    ci.HandleCommand(f"po [{args.object} _subtreeDescription]", result)
    # import ctypes
    # AppKit = ctypes.CDLL(ctypes.util.find_library("AppKit"))
    # AppKit.
    # NSBeep = AppKit.NSBeep
    # NSBeep.restype = None
    # NSBeep()
    # print(result)


def dumpselectors(debugger, command, result, internal_dict):
    '''
    Prints out all selectors defined in an object (does not include superclass
    methods)
    '''
    parser = argparse.ArgumentParser(prog=__name__)
    parser.add_argument("object", help="object to dump selectors on")
    args = parser.parse_args(shlex.split(command))

    target = debugger.GetSelectedTarget()
    process = target.GetProcess()
    error = lldb.SBError()
    count_addr = process.AllocateMemory(4, lldb.ePermissionsReadable | lldb.ePermissionsWritable, error)

    # Using id* as cannot seem to find type Method
    expr_result = target.EvaluateExpression(
        f"(id*) class_copyMethodList((Class)[(id){args.object} class], (unsigned int*){count_addr})"
    )
    ptr = expr_result.GetValueAsUnsigned()
    n = process.ReadUnsignedFromMemory(count_addr, 4, error)
    process.DeallocateMemory(count_addr, error)

    print(f"{n} selectors", file=result)
    for index in range(n):
        name = getCstr(debugger, f"method_getName(((id*){ptr})[{index}])")
        address = getValue(debugger, f"method_getImplementation(((id*){ptr})[{index}])")
        print(f"{name} (0x{address:016x})", file=result)

    target.EvaluateExpression(f"(void) free((void*){ptr})")


def dumpproperties(debugger, command, result, internal_dict):
    '''
    Prints out all properties for an object (does not include superclass
    properties)
    '''
    parser = argparse.ArgumentParser(prog=__name__)
    parser.add_argument("object", help="object to dump properties on")
    args = parser.parse_args(shlex.split(command))

    target = debugger.GetSelectedTarget()
    process = target.GetProcess()
    error = lldb.SBError()
    count_addr = process.AllocateMemory(4, lldb.ePermissionsReadable | lldb.ePermissionsWritable, error)

    expr_result = target.EvaluateExpression(
        f"(id*) class_copyPropertyList((Class)[{args.object} class], (unsigned int*){count_addr})"
    )
    ptr = expr_result.GetValueAsUnsigned()
    n = process.ReadUnsignedFromMemory(count_addr, 4, error)
    process.DeallocateMemory(count_addr, error)

    print(f"{n} properties", file=result)
    for index in range(n):
        name = getCstr(debugger, f"property_getName(((id*){ptr})[{index}])")
        attr = getCstr(debugger, f"property_getAttributes(((id*){ptr})[{index}])")
        val = target.EvaluateExpression(f"[{args.object} {name}]").GetObjectDescription() or ''
        print(f"{name} ({attr}) = {val}", file=result)

    target.EvaluateExpression(f"(void) free((void*){ptr})")


def dumpivars(debugger, command, result, internal_dict):
    '''
    Prints out all ivars for an object
    '''
    parser = argparse.ArgumentParser(prog=__name__)
    parser.add_argument("object", help="object to dump ivars on")
    args = parser.parse_args(shlex.split(command))

    target = debugger.GetSelectedTarget()
    process = target.GetProcess()

    cls = getValue(debugger, f"[{args.object} class]")
    name = args.object
    while cls:
        clsname = getCstr(debugger, f"class_getName({cls})")
        name += "." + clsname
        print(name, file=result)

        error = lldb.SBError()
        count_addr = process.AllocateMemory(4, lldb.ePermissionsReadable | lldb.ePermissionsWritable, error)
        # Using id as cannot seem to find type Ivar
        expr_result = target.EvaluateExpression(
            f"(id*) class_copyIvarList((Class){cls}, (unsigned int*){count_addr})"
        )
        ptr = expr_result.GetValueAsUnsigned()
        n = process.ReadUnsignedFromMemory(count_addr, 4, error)
        process.DeallocateMemory(count_addr, error)

        print(f"{n} ivar{'s' if n>1 else ''}", file=result)
        for index in range(n):
            ivarname = getCstr(debugger, f"ivar_getName(((id*){ptr})[{index}])")
            val = target.EvaluateExpression(
                f"object_getIvar({args.object}, ((id*){ptr})[{index}])"
            ).GetObjectDescription() or ''
            print(f"{ivarname} = {val}", file=result)

        target.EvaluateExpression(f"(void) free((void*){ptr})")
        print(file=result)
        cls = getValue(debugger, f"[{cls} superclass]")


def printflags(debugger, command, result, internal_dict):
    '''
    Print x86-64 RFLAGS or AArch64 CPSR/PSTATE flags in a readable format
    '''
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
    thread = debugger.GetSelectedTarget().GetProcess().GetSelectedThread()
    frame = thread.GetSelectedFrame()
    rflags = frame.FindRegister('rflags')
    cpsr = frame.FindRegister('cpsr')

    if rflags.IsValid():
        flags = rflags.unsigned
        flagbits = X86_FLAGBITS
        extra_fields = [(7, f"IOPL={(flags >> 12) & 0x3}")]
    elif cpsr.IsValid():
        flags = cpsr.unsigned
        flagbits = AARCH64_FLAGBITS
        extra_fields = []
    else:
        result.write('flags: no rflags or cpsr register in the selected frame\n')
        return

    rendered_flags = [
        name if flags & (1 << bit) else f"{DIM}{name}{RESET}"
        for name, bit in reversed(flagbits)
    ]
    for index, field in extra_fields:
        rendered_flags.insert(index, field)
    result.write(' '.join(rendered_flags) + '\n')


def printstdstring(debugger, command, result, internal_dict):
    '''
    Prints out a string from std::string object
    '''
    # todo: add wchar detection
    parser = argparse.ArgumentParser(prog=__name__)
    parser.add_argument("object", help="std::string object")
    parser.add_argument("--impl", choices=("libc++", "libstdc++"),
                        help="force a standard-library layout instead of autodetecting")
    args = parser.parse_args(shlex.split(command))

    impl = args.impl or _detect_stdstring_impl(debugger, args.object)
    if impl == "libstdc++":
        # first word points directly at the character data (SSO or heap)
        outstring = getCstr(debugger, f"*(char **) ({args.object})")
    else:
        # libc++: low bit of the first byte flags a long (heap) string
        pseudo_length = getValue(debugger, f"*(unsigned char*) {args.object}")
        if pseudo_length & 1:
            outstring = getCstr(debugger, f"*(char **) ({args.object}+16)")
        else:
            outstring = getCstr(debugger, f"({args.object}+1)")

    print(outstring, file=result)


def _detect_stdstring_impl(debugger, obj):
    '''
    Guess the std::string layout by checking whether the first word is a
    plausible data pointer (libstdc++) or an inline SSO byte (libc++).
    '''
    first_word = getValue(debugger, f"*(unsigned long *) ({obj})")
    if first_word is None:
        return "libc++"
    # libstdc++'s _M_p either points into the object's own SSO buffer
    # (obj+16) or to a separate heap allocation; either way it's a real,
    # non-trivial pointer. libc++'s first word is a length/flags byte.
    obj_addr = getValue(debugger, f"(unsigned long)({obj})")
    if first_word == (obj_addr + 16) or first_word > 0x1000:
        return "libstdc++"
    return "libc++"


def fsa(debugger, command, result, internal_dict):
    '''
    Installs F-script menu
    '''
    debugger.HandleCommand(f'expr (void) [[NSBundle bundleWithPath:@"{fscript_framework}"]'
                           ' load]')
    debugger.HandleCommand('expr (void) [FScriptMenuItem insertInMainMenu]')
fscript_framework = '/Library/Frameworks/FScript.framework'


class ScriptedStepBase:
    def __init__(self, thread_plan, internal_dict):
        self.thread_plan = thread_plan

    def explains_stop(self, event):
        ''' Returns true if this explains why the execution was halted '''
        # We are stepping, so if we stop for any other reason, it isn't
        # because of us.
        return self.thread_plan.GetThread().GetStopReason() == lldb.eStopReasonTrace

    def should_stop(self, event):
        '''
        Should debugger stop or continue
        Notimplemented in base class
        '''
        return True

    def should_step(self):
        ''' Should be enabled '''
        return True


class ScriptedStepToCall(ScriptedStepBase):
    def should_stop(self, event):
        ''' Stop only when we have reached a call instruction '''
        cur_pc = self.thread_plan.GetThread().GetFrameAtIndex(0).GetPCAddress()
        target = self.thread_plan.GetThread().GetProcess().GetTarget()
        instr = target.ReadInstructions(cur_pc, 1)[0]
        if 'call' in instr.GetMnemonic(target):
            self.thread_plan.SetPlanComplete(True)
            return True
        else:
            return False


class ScriptedStepToBranch(ScriptedStepBase):
    def should_stop(self, event):
        ''' Stop only when we have reached a branch instruction '''
        cur_pc = self.thread_plan.GetThread().GetFrameAtIndex(0).GetPCAddress()
        target = self.thread_plan.GetThread().GetProcess().GetTarget()
        instr = target.ReadInstructions(cur_pc, 1)[0]
        if instr.DoesBranch():
            self.thread_plan.SetPlanComplete(True)
            return True
        else:
            return False


class ScriptedStepToSyscall(ScriptedStepBase):
    def should_stop(self, event):
        ''' Stop only when we have reached a system call instruction '''
        cur_pc = self.thread_plan.GetThread().GetFrameAtIndex(0).GetPCAddress()
        target = self.thread_plan.GetThread().GetProcess().GetTarget()
        instr = target.ReadInstructions(cur_pc, 1)[0]
        mnemonic = instr.GetMnemonic(target)
        # x86: syscall/sysenter/int 0x80; AArch64: svc
        if mnemonic in ('syscall', 'sysenter', 'svc') or \
                (mnemonic == 'int' and '0x80' in instr.GetOperands(target)):
            self.thread_plan.SetPlanComplete(True)
            return True
        else:
            return False


class ScriptedStepToAntiDebug(ScriptedStepBase):
    def __init__(self, thread_plan, internal_dict):
        super().__init__(thread_plan, internal_dict)
        self.pushfSet = False

    def should_stop(self, event):
        ''' Stop only when we have reached a potential anti-debug instruction '''
        cur_pc = self.thread_plan.GetThread().GetFrameAtIndex(0).GetPCAddress()
        process = self.thread_plan.GetThread().GetProcess()
        target = process.GetTarget()
        instr = target.ReadInstructions(cur_pc, 1)[0]
        if self.pushfSet:
            error = lldb.SBError()
            sp = self.thread_plan.GetThread().GetFrameAtIndex(0).GetSP()
            flags = process.ReadUnsignedFromMemory(sp, 2, error)
            flags &= 0xfeff  # mask off the trap flag
            flagbytes = struct.pack('H', flags)
            process.WriteMemory(sp, flagbytes, error)

            # mask off the trap flag
#            target.EvaluateExpression('*(unsigned short *)$rsp &= 0xfeff')
            self.pushfSet = False
            self.thread_plan.SetPlanComplete(True)
            return True
        if 'pushf' in instr.GetMnemonic(target):
            self.pushfSet = True
            self.thread_plan.SetPlanComplete(True)
            return True
        if 'rdtsc' in instr.GetMnemonic(target):
            self.thread_plan.SetPlanComplete(True)
            return True
        return False


class ScriptedStepToTarget(ScriptedStepBase):
    def __init__(self, thread_plan, internal_dict):
        self.thread_plan = thread_plan
        target = self.thread_plan.GetThread().GetProcess().GetTarget()
        module = target.GetModuleAtIndex(0)
        # __TEXT is the Mach-O code segment; .text the ELF code section
        text_section = module.FindSection('__TEXT') or module.FindSection('.text')
        self.start_addr = text_section.GetLoadAddress(target)
        self.end_addr = self.start_addr + text_section.GetByteSize()

    def should_stop(self, event):
        ''' Stop only when we have reached a certain PC range '''
        cur_pc = self.thread_plan.GetThread().GetFrameAtIndex(0).GetPC()
        if self.start_addr <= cur_pc < self.end_addr:
            self.thread_plan.SetPlanComplete(True)
            return True
        return False


def __lldb_init_module(debugger, internal_dict):
    '''
    Installs python-based commands in lldb
    '''
    def install_function(func, name=None):
        '''
        Installs lldb function
        '''
        if not name:
            name = func.__name__
        debugger.HandleCommand(f"command script add -f {__name__}.{func.__name__} "
                               f"{name}")
        print(f'The "{func.__name__}" python command has been installed and is ready '
              'for use.')

    install_function(printflags, 'flags')

    install_function(printstdstring)

    install_function(nsviewtree)

    install_function(dumpselectors)
    install_function(dumpproperties)
    install_function(dumpivars)

    if os.path.exists(fscript_framework):
        install_function(fsa)
