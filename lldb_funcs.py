import argparse
import shlex
import lldb
import re
import struct
import ctypes
import os.path


def getValue(commandInterpreter, valstr):
    ret = lldb.SBCommandReturnObject()
    commandInterpreter.HandleCommand(f"expr (unsigned long) {valstr}", ret)

    match = re.search(r"=\s*(\S*)", ret.GetOutput(), re.I)
    if match:
        return int(match.group(1), 0)
    else:
        return None


def getCstr(commandInterpreter, valstr):
    ret = lldb.SBCommandReturnObject()
    commandInterpreter.HandleCommand(f"expr (char*) {valstr}", ret)

    match = re.search(r'=[^"]*"(.*)"', ret.GetOutput(), re.I)
    if match:
        return match.group(1)
    else:
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

    ci = debugger.GetCommandInterpreter()

    ret = lldb.SBCommandReturnObject()
    ci.HandleCommand("expr --persistent-result false -- $n", ret)
    ci.HandleCommand("expr --persistent-result false -- $methodps", ret)

    # Using id* as cannot seem to find type Method
    debugger.HandleCommand(
        "expr unsigned int $n = 0; "
        f"id* $methodps = (id*) class_copyMethodList((Class)[(id){args.object} class], &$n)"
    )

    nSeletors = getValue(ci, "$n")
    print(f"{nSeletors} selectors", file=result)
    for index in range(nSeletors):
        name = getCstr(ci, f"method_getName(*($methodps+{index}))")
        address = getValue(
            ci, f"method_getImplementation(*($methodps+{index}))")
        print(f"{name} (0x{address:016x})", file=result)

    debugger.HandleCommand(
        "expr (void) free($methodps)"
    )


def dumpproperties(debugger, command, result, internal_dict):
    '''
    Prints out all properties for an object (does not include superclass
    properties)
    '''
    parser = argparse.ArgumentParser(prog=__name__)
    parser.add_argument("object", help="object to dump properties on")
    args = parser.parse_args(shlex.split(command))

    ci = debugger.GetCommandInterpreter()

    ret = lldb.SBCommandReturnObject()
    ci.HandleCommand("expr --persistent-result false -- $n", ret)
    ci.HandleCommand("expr --persistent-result false -- $propps", ret)

    # Using id* as cannot seem to find type Method
    debugger.HandleCommand(
        "expr unsigned int $n = 0; "
        f"id* $propps = (id*) class_copyPropertyList((Class)[{args.object} class], &$n)"
    )

    nProps = getValue(ci, "$n")
    print("{nProps} properties", file=result)
    for index in range(nProps):
        name = getCstr(ci, f"property_getName(*($propps+{index}))")
        attr = getCstr(ci, f"property_getAttributes(*($propps+{index}))")
        ci.HandleCommand(
            f"po [{args.object} {name}]",
            ret
        )
        val = ret.GetOutput().strip()
        print(f"{name} ({attr}) = {val}", file=result)

    debugger.HandleCommand(
        "expr (void) free($propps)"
    )


def dumpivars(debugger, command, result, internal_dict):
    '''
    Prints out all ivars for an object
    '''
    parser = argparse.ArgumentParser(prog=__name__)
    parser.add_argument("object", help="object to dump ivars on")
    args = parser.parse_args(shlex.split(command))

    ci = debugger.GetCommandInterpreter()
    ret = lldb.SBCommandReturnObject()

    cls = getValue(ci, f"[{args.object} class]")
    name = args.object
    while cls:
        clsname = getCstr(ci, f"class_getName({cls})")
        name += "." + clsname
        print(name, file=result)

        ci.HandleCommand("expr --persistent-result false -- $n", ret)
        ci.HandleCommand("expr --persistent-result false -- $ivarps", ret)

        # Using id as cannot seem to find type Ivar
        debugger.HandleCommand(
            "expr unsigned int $n = 0; "
            f"id* $ivarps = (id*) class_copyIvarList((Class){cls}, &$n)"
        )
        nIvars = getValue(ci, "$n")
        print(f"{nIvars} ivar{'s' if nIvars>1 else ''}", file=result)
        for index in range(nIvars):
            ivarname = getCstr(ci, f"ivar_getName(*($ivarps+{index}))")
            ci.HandleCommand(
                f"po object_getIvar({args.object}, *($ivarps+{index}))",
                ret
            )
            val = ret.GetOutput().strip()
            print(f"{ivarname} = {val}", file=result)
        debugger.HandleCommand(
            "expr (void) free($ivarps)"
        )
        print(file=result)
        cls = getValue(ci, f"[{cls} superclass]")


def printflags(debugger, command, result, internal_dict):
    '''
    Print flags in a readable format
    '''
    FLAGBITS = (('C', 0x1), ('P', 0x4), ('A', 0x10), ('Z', 0x40), ('S', 0x80),
                ('T', 0x100), ('I', 0x200), ('D', 0x400), ('O', 0x800))
    thread = debugger.GetSelectedTarget().GetProcess().GetSelectedThread()
    sbregisters = thread.GetSelectedFrame().registers
    regs = sbregisters.GetFirstValueByName('General Purpose Registers')
    flags = regs.GetChildMemberWithName('flags').unsigned
    for flagbit in FLAGBITS[::-1]:
        result.write(flagbit[0] if flags & flagbit[1] else '.')
    result.write('\n')


def printstdstring(debugger, command, result, internal_dict):
    '''
    Prints out a string from std::string object
    '''
    # todo: add wchar detection
    parser = argparse.ArgumentParser(prog=__name__)
    parser.add_argument("object", help="std::string object")
    args = parser.parse_args(shlex.split(command))

    ci = debugger.GetCommandInterpreter()

    pseudo_length = getValue(ci, f"*(unsigned char*) {args.object}")
    if pseudo_length & 1:
        outstring = getCstr(ci, f"*(char **) ({args.object}+16)")
    else:
        outstring = getCstr(ci, f"({args.object}+1)")

    print(outstring, file=result)


def fsa(debugger, command, result, internal_dict):
    '''
    Installs F-script menu
    '''
    debugger.HandleCommand('expr (void) [[NSBundle bundleWithPath:@"{}"]'
                           ' load]'.format(fscript_framework))
    debugger.HandleCommand('expr (void) [FScriptMenuItem insertInMainMenu]')
fscript_framework = '/Library/Frameworks/FScript.framework'


class ScriptedStepBase:
    def __init__(self, thread_plan, internal_dict):
        self.thread_plan = thread_plan

    def explains_stop(self, event):
        ''' Returns true if this explains why the execution was halted '''
        # We are stepping, so if we stop for any other reason, it isn't
        # because of us.
        if self.thread_plan.GetThread().GetStopReason() == lldb.eStopReasonTrace:
            return True
        else:
            return False

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
    def __init__(self, thread_plan, internal_dict):
        self.thread_plan = thread_plan

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
    def __init__(self, thread_plan, internal_dict):
        self.thread_plan = thread_plan

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
    def __init__(self, thread_plan, internal_dict):
        self.thread_plan = thread_plan

    def should_stop(self, event):
        ''' Stop only when we have reached a system call instruction '''
        cur_pc = self.thread_plan.GetThread().GetFrameAtIndex(0).GetPCAddress()
        target = self.thread_plan.GetThread().GetProcess().GetTarget()
        instr = target.ReadInstructions(cur_pc, 1)[0]
        if 'sys' in instr.GetMnemonic(target):
            self.thread_plan.SetPlanComplete(True)
            return True
        else:
            return False


class ScriptedStepToAntiDebug(ScriptedStepBase):
    def __init__(self, thread_plan, internal_dict):
        self.thread_plan = thread_plan
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
        text_section = target.GetModuleAtIndex(0).FindSection('__TEXT')
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
        debugger.HandleCommand("command script add -f {0}.{1} "
                               "{2}".format(__name__, func.__name__, name))
        print('The "{}" python command has been installed and is ready '
              'for use.'.format(func.__name__))

    install_function(printflags, 'flags')

    install_function(printstdstring)

    install_function(nsviewtree)

    install_function(dumpselectors)
    install_function(dumpproperties)
    install_function(dumpivars)

    if os.path.exists(fscript_framework):
        install_function(fsa)
