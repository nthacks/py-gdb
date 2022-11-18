A collection of python scripts to automate certain GDB actions.

## funclinetrace.py

This script traces the execution of lines in a single function.

### When to use:

This can help in debugging when comparing a bug's execution path to a known one.

### How to use:

1. Start GDB and set a breakpoint on the parent function to start tracing from.
    eg: break foo

2. When you hit the breakpoint, run
    source /path/to/stacklinetrace.py


## gdbdump.py

This script recursively expands an object and dumps it in a JSON file.
If the same address is visited again, it inserts the path of the previous value.
You can configure particular object types for which expansion is ignored,
to speed up the script.

### When to use:

This can help record or compare the current state of data structures

### How to use:
Edit global_ignore_ctypes
When you hit a breakpoint, run
    source /path/to/gdbdump.py


## stacklinetrace.py

This script traces the execution of lines across multiple functions in the same
call flow.

### When to use:

This can help in debugging when comparing a bug's execution path to a known one,
when you are not sure in exactly which function the difference occurs.

### How to use:

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
