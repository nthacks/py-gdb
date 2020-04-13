'''
This script traces the execution of lines across multiple functions in the same
call flow.

HOW TO USE:

1. Create a file named stack.txt in the same folder where you execute gdb.
    This should contain the list of function names (without brackets, one 
    function per line)
    The functions in the list should all be connected in the call stack. 
    e.g. If there are 2 functions which you are interested in : foo() and log()
        But the call flow is like foo() calls bar() which then calls log()
        Then in the file you must have even bar() to connect them:
            foo
            bar
            log

2. Start GDB and set a breakpoint on the parent function to start tracing from.
    NOTE: even "foo" should be present in stack.txt
    eg: break foo

3. When you hit the breakpoint, run
    source /path/to/stacklinetrace.py
'''
from __future__ import print_function
import gdb
from time import time
import re


# DEBUG = False
# if DEBUG:
#     debug_log = open("debug.log", "w")

# log = open("linetrace.log", 'w')


# def dbug_print(*args, **kwargs):
#     if DEBUG:
#         print(*args, **kwargs)
#     else:
#         pass


# def dbug_log(command):
#     if DEBUG:
#         print(command, file=debug_log)
#     else:
#         pass


# Keeps track of the relative depth to indent the traced code.
GLOBAL_INDENT = 0

# Returns absolute depth of frame


def framedepth(frame, depth=0):
    if frame is None:
        return depth
    return framedepth(frame.older(), depth+1)


# Returns relative depth of frame
def cur_depth():
    global GLOBAL_INDENT
    GLOBAL_INDENT = framedepth(gdb.selected_frame()) - break_depth
    return GLOBAL_INDENT


# Returns current function name
def cur_fn():
    return gdb.selected_frame().name()


# Returns current line
def _line():
    cur_line = execute("frame", to_string=True)
    print_line = ''.join(cur_line.splitlines()[1:]).strip()
    return print_line


# Prints current line with indent and function name to outfile
def print_cur_line():
    print("{}{} {}".format(" "*GLOBAL_INDENT, cur_fn(), _line()), file=log)


# Wrappers to execute commands
def execute(*args, **kwargs):
    # dbug_log(args[0])
    return gdb.execute(*args, **kwargs)


def up():
    # dbug_print("# before   up : {} {}".format(cur_fn(), _line()), file=log)
    execute("up")
    # dbug_print("# after    up : {} {}".format(cur_fn(), _line()), file=log)


def next():
    # dbug_print("# before next : {} {}".format(cur_fn(), _line()), file=log)
    execute("next")
    # dbug_print("# after  next : {} {}".format(cur_fn(), _line()), file=log)


def step():
    # dbug_print("# before step : {} {}".format(cur_fn(), _line()), file=log)
    execute("step")
    # dbug_print("# after  step : {} {}".format(cur_fn(), _line()), file=log)
    # print("ENTER : ", end='', file=log)
    # print(cur_fn(), file=log)


execute("set pagination off")
break_fn = gdb.selected_frame().function()


outfile = input("\nEnter desired output file name (leave blank for default): ")
if not outfile:
    outfile = "linetrace_{}_{}.log".format(
        break_fn.name.split('(')[0], int(time()))

log = open(outfile, 'w')
print("\nLogging to {}\n".format(outfile))

# Read list of functions and prepare a regex to match any of them
with open("stack.txt") as f:
    break_fn_list = [line.rstrip() for line in f]

break_fn_regex = "(" + "|".join(break_fn_list) + ")\("
break_fn_pattern = re.compile(break_fn_regex)

break_depth = framedepth(gdb.selected_frame())

print(break_fn, file=log)
while cur_depth() >= 0:
    print_cur_line()
    if re.search(break_fn_pattern, _line()):
        step()
    else:
        next()

log.close()

print("\nSaved to {}\n".format(outfile))

# if DEBUG:
#     debug_log.close()
