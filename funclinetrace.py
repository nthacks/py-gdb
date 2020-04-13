'''
This script traces the execution of lines in a single function.

HOW TO USE:

1. Start GDB and set a breakpoint on the parent function to start tracing from.
    eg: break foo

2. When you hit the breakpoint, run
    source /path/to/stacklinetrace.py
'''

from __future__ import print_function
from time import time
import gdb

# Returns current line
def _line():
    cur_line = gdb.execute("frame", to_string=True)
    print_line = ''.join(cur_line.splitlines()[1:]).strip()
    return print_line

gdb.execute("set pagination off")

break_fn = gdb.selected_frame().function()
outfile = input("\nEnter desired output file name (leave blank for default): ")
if not outfile:
    outfile = "linetrace_{}_{}.log".format(
        break_fn.name.split('(')[0], int(time()))

with open(outfile, 'w') as log:
    print(break_fn, file=log)
    while True:
        cur_fn = gdb.selected_frame().function()
        if cur_fn.name != break_fn.name:
            break
        print(_line(), file=log)
        gdb.execute("next")
