import argparse
import shlex
import lldb
import re
import ctypes


def getValue(commandInterpreter, valstr):
    ret = lldb.SBCommandReturnObject()
    commandInterpreter.HandleCommand("p (unsigned long) {}".format(valstr),
                                     ret)
    match = re.search(r"=\s*(\S*)", ret.GetOutput(), re.I)
    if match:
        return int(match.group(1), 0)
    else:
        return None


def getCstr(commandInterpreter, valstr):
    ret = lldb.SBCommandReturnObject()
    commandInterpreter.HandleCommand("p (char*) {}".format(valstr),
                                     ret)
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
    ci.HandleCommand(
        "po [{} _subtreeDescription]".format(args.object),
        result
    )
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

    # Using id* as cannot seem to find type Method
    debugger.HandleCommand(
        "p unsigned int $n = 0; "
        "id* $methodps = (id*) class_copyMethodList((Class)[{} class], &$n)"
        "".format(args.object)
    )

    nSeletors = getValue(ci, "$n")
    print >>result, "{} selectors".format(nSeletors)
    for index in range(nSeletors):
        name = getCstr(ci, "method_getName(*($methodps+{}))".format(index))
        address = getValue(
            ci, "method_getImplementation(*($methodps+{}))".format(index))
        print >>result, "{} (0x{:016x})".format(name, address)

    debugger.HandleCommand(
        "p (void) free($methodps)"
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

    # Using id* as cannot seem to find type Method
    debugger.HandleCommand(
        "p unsigned int $n = 0; "
        "id* $propps = (id*) class_copyPropertyList((Class)[{} class], &$n)"
        "".format(args.object)
    )

    ret = lldb.SBCommandReturnObject()

    nProps = getValue(ci, "$n")
    print >>result, "{} properties".format(nProps)
    for index in range(nProps):
        name = getCstr(ci, "property_getName(*($propps+{}))".format(index))
        attr = getCstr(
            ci, "property_getAttributes(*($propps+{}))".format(index))
        ci.HandleCommand(
            "po [{} {}]".format(args.object, name),
            ret
        )
        val = ret.GetOutput().strip()
        print >>result, "{} ({}) = {}".format(name, attr, val)

    debugger.HandleCommand(
        "p (void) free($propps)"
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

    cls = getValue(ci, "[{} class]".format(args.object))
    name = args.object
    while cls:
        clsname = getCstr(ci, "class_getName({})".format(cls))
        name += "." + clsname
        print >>result, name

        # Using id as cannot seem to find type Ivar
        debugger.HandleCommand(
            "p unsigned int $n = 0; "
            "id* $ivarps = (id*) class_copyIvarList((Class){}, &$n)"
            "".format(cls)
        )
        nIvars = getValue(ci, "$n")
        print >>result, "{} ivar{}".format(nIvars, 's' if nIvars > 1 else '')
        for index in range(nIvars):
            ivarname = getCstr(ci, "ivar_getName(*($ivarps+{}))".format(index))
            ci.HandleCommand(
                "po object_getIvar({}, *($ivarps+{}))".format(args.object,
                                                              index),
                ret
            )
            val = ret.GetOutput().strip()
            print >>result, "{} = {}".format(ivarname, val)
        debugger.HandleCommand(
            "p (void) free($ivarps)"
        )
        print >>result
        cls = getValue(ci, "[{} superclass]".format(cls))


def printstdstring(debugger, command, result, internal_dict):
    '''
    Prints out a string from std::string object
    '''
    # todo: add wchar detection
    parser = argparse.ArgumentParser(prog=__name__)
    parser.add_argument("object", help="std::string object")
    args = parser.parse_args(shlex.split(command))

    ci = debugger.GetCommandInterpreter()

    pseudo_length = getValue(ci, "*(unsigned char*) {}".format(args.object))
    if pseudo_length & 1:
        outstring = getCstr(ci, "*(char **) ({}+16)".format(args.object))
    else:
        outstring = getCstr(ci, "({}+1)".format(args.object))

    print >>result, outstring


def __lldb_init_module(debugger, internal_dict):
    '''
    Installs python-based commands in lldb
    '''
    def install_function(func):
        '''
        Installs lldb function
        '''
        debugger.HandleCommand("command script add -f {0}.{1} "
                               "{1}".format(__name__, func.__name__))
        print('The "{}" python command has been installed and is ready '
              'for use.'.format(func.__name__))

    install_function(printstdstring)

    install_function(nsviewtree)

    install_function(dumpselectors)
    install_function(dumpproperties)
    install_function(dumpivars)
