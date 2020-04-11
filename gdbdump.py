'''
This script recursively expands an object and dumps it in a JSON file.
If the same address is visited again, it inserts the path of the previous value.
You can configure particular object types for which expansion is ignored,
to speed up the script.

HOW TO USE:
Edit global_ignore_ctypes below
When you hit a breakpoint, run
    source /path/to/gdbdump.py
'''
from __future__ import print_function
import gdb
import re
import json
import traceback
from os import system as shell
from datetime import datetime as time
start_time = time.now()
"""
Configure ignorable ctypes (to not expand) when printing
"""
global_ignore_ctypes = frozenset((
    # 'TABLE *',
    # 'handler *',
    # 'THD *',
    # 'MEM_ROOT',
    # 'mysql_mutex_t',
    # 'const CHARSET_INFO *',
))

type_codes = {0: 'UNKNOWN', 1: 'PTR', 2: 'ARRAY', 3: 'STRUCT', 4: 'UNION', 5: 'ENUM', 6: 'FLAGS', 7: 'FUNC', 8: 'INT', 9: 'FLT', 10: 'VOID', 11: 'SET', 12: 'RANGE', 13: 'STRING', -1: 'BITSTRING',
              14: 'ERROR', 15: 'METHOD', 16: 'METHODPTR', 17: 'MEMBERPTR', 18: 'REF', 19: 'RVALUE_REF', 20: 'CHAR', 21: 'BOOL', 22: 'COMPLEX', 23: 'TYPEDEF', 24: 'NAMESPACE', 25: 'DECFLOAT', 27: 'INTERNAL_FUNCTION'}

printable_types = frozenset((
    gdb.TYPE_CODE_INT,
    gdb.TYPE_CODE_FLT,
    gdb.TYPE_CODE_CHAR,
    gdb.TYPE_CODE_BOOL,
    gdb.TYPE_CODE_ENUM,
    gdb.TYPE_CODE_FLAGS,
    gdb.TYPE_CODE_COMPLEX,
    gdb.TYPE_CODE_DECFLOAT,
    gdb.TYPE_CODE_METHOD,
    gdb.TYPE_CODE_FUNC,
    gdb.TYPE_CODE_STRING,
    gdb.TYPE_CODE_ARRAY
))
expandable_types = frozenset((
    gdb.TYPE_CODE_STRUCT,
    gdb.TYPE_CODE_UNION
))
extract_hex_re = re.compile(r'0x[0-9a-f]+')
replace_hex_re = re.compile(r'\s*0x[0-9a-f]+\s*')
error_log = open("error.log", 'w')
# log = open("dump.log", 'w')


def depth(x):
    if type(x) is dict and x:
        return 1 + max(depth(x[a]) for a in x)
    if type(x) is list and x:
        return 1 + max(depth(a) for a in x)
    return 0


def backtrace(frame, trace=[]):
    function = frame.function()
    if function is None:
        return trace
    trace.append({
        "function": function.print_name,
        "line": function.line
    })
    return backtrace(frame.older(), trace)


class VisitedAddresses:
    def __init__(self):
        self.visited = dict({0: None})

    def __contains__(self, key_addr_and_type):
        key_addr, field_ctype = key_addr_and_type
        result = extract_hex_re.search(str(key_addr))
        if not result:
            return False
        hex_addr_str = result.group(0)
        int_addr = int(hex_addr_str, 16)
        return (int_addr, field_ctype) in self.visited

    def __setitem__(self, key_addr_and_type, value_expr):
        key_addr, field_ctype = key_addr_and_type
        result = extract_hex_re.search(str(key_addr))
        if not result:
            return
        hex_addr_str = result.group(0)
        int_addr = int(hex_addr_str, 16)
        self.visited[(int_addr, field_ctype)] = value_expr

    def __getitem__(self, key_addr_and_type):
        key_addr, field_ctype = key_addr_and_type
        result = extract_hex_re.search(str(key_addr))
        hex_addr_str = result.group(0)
        int_addr = int(hex_addr_str, 16)
        return self.visited[(int_addr, field_ctype)]

    def get_dict(self):
        return self.visited


def expand_obj_dict(obj_name, obj_dict):
    global visited, error_log
    for idx, field_name in enumerate(obj_dict):
        # print(idx, field_name)
        try:
            field_type_code = 0
            field_expr = "{}->{}".format(obj_name, field_name)
            # print(idx, field_expr)
            field_val = gdb.parse_and_eval(field_expr)
            field_ctype = str(field_val.type)
            field_type_code = field_val.type.strip_typedefs().code

            if field_ctype in global_ignore_ctypes:
                obj_dict[field_name] = {
                    "expr": field_expr,
                    "type": field_ctype,
                    "value": "(GDB-DUMP-IGNORED-VALUE)"
                }
                continue
            if idx != 0 and (field_val.address, field_ctype) in visited:
                # print("Already Visited", file=log)
                obj_dict[field_name] = {
                    "expr": field_expr,
                    "type": field_ctype,
                    "value": "(GDB-DUMP-PREVIOUSLY-VISITED)" + visited[field_val.address]
                }
                continue

            visited[(field_val.address, field_ctype)] = field_expr

            if field_type_code == gdb.TYPE_CODE_PTR \
                    and field_val.referenced_value().type.strip_typedefs().code == gdb.TYPE_CODE_STRUCT:
                # print("Dereferencing structure pointer", file=log)
                field_val = field_val.referenced_value()

                if field_val.address in visited:
                    # print("Already Visited", file=log)
                    obj_dict[field_name] = {
                        "expr": field_expr,
                        "type": field_ctype,
                        "value": "(GDB-DUMP-PREVIOUSLY-VISITED)" + visited[(field_val.address, field_ctype)]
                    }
                    continue
                visited[(field_val.address, field_ctype)] = "*"+field_expr

            field_type_code = field_val.type.strip_typedefs().code

            # print(field_expr, type_codes[field_type_code], file=log)

            if field_type_code in printable_types:
                # print("Printable type", file=log)
                field_val = str(field_val)

                if field_val.find("error:") != -1:
                    field_val = None

            elif field_type_code == gdb.TYPE_CODE_PTR:
                # print("Printable Pointer", file=log)
                field_val = re.sub(replace_hex_re, '', str(
                    field_val)).strip().strip('"')

                if field_val.find("error:") != -1:
                    field_val = None

            elif field_type_code in expandable_types:
                # print("Expanding keys", file=log)
                field_type = field_val.type
                field_keys = field_type.keys()

                if len(field_keys) == 0:
                    field_val = None

                elif field_keys[0].find("std::") != -1:
                    field_val = str(field_val)

                else:
                    field_val = dict.fromkeys(field_keys)
                    # TODO: Check ignorelist
                    field_val = expand_obj_dict(field_expr, field_val)

            # print("Value: ", field_val, file=log)

            obj_dict[field_name] = {
                "expr": field_expr,
                "type": field_ctype,
                "value": field_val
            }

        except gdb.MemoryError:
            obj_dict[field_name] = None
            continue

        except gdb.error as e:
            if str(e).find("xmethod") != -1:
                obj_val = gdb.parse_and_eval(obj_name)
                return str(obj_val)

            obj_dict[field_name] = None
            continue

        except Exception as e:

            print("\n---(STATE)---",
                  "\n\tfield_expr = {}\n\ttype_code = ".format(
                      field_expr,
                      type_codes[field_type_code]
                  ),
                  "\nException: {}".format(e),
                  "\n-------------",
                  file=error_log)
            traceback.print_exc(file=error_log)
            continue

    return obj_dict


visited = VisitedAddresses()
gdb.execute("set pagination off")
gdb.execute("set print pretty off")
# obj_expr = "outparam"
obj_expr = str(input("Enter object expression: "))
print("Parsing expression")
obj_val = gdb.parse_and_eval(obj_expr)
print("Checking address")
obj_ctype = str(obj_val.type)
visited[(obj_val.address, obj_ctype)] = obj_expr

if (obj_val.type.code == gdb.TYPE_CODE_PTR):
    print("Dereferencing")
    obj_val = obj_val.referenced_value()

print("Determining type")
obj_type = obj_val.type

print("Preparing object dictionary")
obj_dict = dict.fromkeys(obj_type.keys())
print("Expanding object dictionary (will take a while)")
print("(TypeErrors can be ignored)")
obj_dict = expand_obj_dict(obj_expr, obj_dict)

print("Dumping JSON")

final_dict = {
    "timestamp": str(start_time),
    "backtrace": backtrace(gdb.selected_frame()),
    "expr": obj_expr,
    "type": obj_ctype,
    "value": obj_dict
}

filename = "{}_{}.json".format(
    obj_expr.replace('->', '.'), start_time.strftime('%Y%m%d%H%M%S'))
print("Saved in {}".format(filename))
json.dump(final_dict, open(filename, 'w'), indent=4)
# print("Dumping visited addresses")
# json.dump(visited.get_dict(), open("visited.json", 'w'), indent=4)

# log.close()
error_log.close()
time_taken = str(time.now() - start_time)
print("Time Taken: ", time_taken)
shell("notify-send 'Finished GDB dump' '{} in {}'".format(obj_expr, time_taken))


# TODO:
# CTYPE specific ignore-list
# Maxdepth
# With -D_GLIBCXX_DEBUG compiler flag, see STL values
# Tracking value changes
