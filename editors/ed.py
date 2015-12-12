"""
ed.py - line-oriented text editor in pure Python based on classic Unix ed.

This module provides both the classic command interface and the public
Python API.  It imports buffer.py which defines the Buffer class that
provides the core data structure and the internal API.

For more explanation see ed.md, ed.txt, the docstrings here, and the tests
in test/ed/
"""

import re, os, sys
import pysh  # provides embedded Python shell for ! command
import buffer

# edsel display editor suppresses output from ed l z commands to scrolling cmd region
# because edsel shows the lines in the display window.

destination = sys.stdout # send output from l z commands to scrolling command region
null = open(os.devnull, 'w')

def discard_printing():
    'suppress output from ed l z commands to scrolling command region'
    global destination
    destination = null

def show_printing():
    'Restore output from ed l z commands to scrolling command region'
    global destination
    destination = sys.stdout 

# arg lists, defaults, range checking

def parse_args(args):
    """
    Parse variable-length argument list where all arguments optional.
o    Return fixed length tuple: start, end, text, params 
    start, end are line numbers, for example the first and last line of a region.
    When present, start and end are int, both might be absent, indicated by None.
    text is the first token in the parameter list, str or None if absent
    params is the parameter list, [] if absent.
    """
    # get 2, 1, or 0 optional line numbers from head of args list
    if len(args) > 1 and isinstance(args[0],int) and isinstance(args[1],int):
        start, end, params = int(args[0]), int(args[1]), args[2:]
    elif len(args) > 0 and isinstance(args[0],int):
        start, end, params = int(args[0]), None, args[1:]
    else:
        start, end, params = None, None, args
    # get 1 or 0 optional strings and the rest of args list
    if params and isinstance(params[0], str):
        text, params = params[0], params[1:]
    else:
        text = None 
    return start, end, text, params # params might still be non-empty

# The commands and API for ed.py use the classic Unix ed conventions for
# indexing and range (which are unlike Python): The index of the first
# line is 1, the index of the last line is the same as the number of
# lines (the length of the buffer in lines), and range i,j includes the
# last line with index j (so the range i,i is just the line i, but it is
# not empty).

# Defaults and range checking, use the indexing and range conventions above.
# mk_ functions replace None missing arguments with default line numbers

def mk_iline(iline):
    'Return iline if given, else default dot, 0 if buffer is empty'
    return iline if iline != None else buf.dot

def mk_range(start, end):
    """Return start, end if given, 
    else return defaults, calc default end from start"""
    start = mk_iline(start)
    return start, end if end != None else start

def iline_ok(iline):
    """Return True if iline address is in buffer, always False for empty buffer
    Used by most commands, which don't make sense for an empty buffer"""
    return (0 < iline <= buf.S()) 

def iline_ok0(iline):
    """Return True if iline address is in buffer, or iline is 0 for start 
    Used by commands which make sense for an empty buffer: insert, append, read
    """
    return (0 <= iline <= buf.S())

def range_ok(start, end):
    'Return True if start and end are in buffer, and start does not follow end'
    return iline_ok(start) and iline_ok(end) and start <= end

# parse_check_ functions used by many commands to parse line address args,
# replace missing args by defaults, check args, and print error messages.

def parse_check_line(ok0, args):
    'Building block for parse_check_... functions'
    iline, x, param, xx = parse_args(args)
    iline = mk_iline(iline)
    valid = iline_ok0(iline) if ok0 else iline_ok(iline)
    if not valid:
        print('? invalid address')
    return valid, iline, param

def parse_check_iline(args):
    'for commands that use one line address where 0 is not valid: k z'
    return parse_check_line(False, args)

def parse_check_iline0(args):
    'for commands that use one line address where 0 is valid: r a i'
    return parse_check_line(True, args)

def parse_check_range(args):
    'for cmds that can affect a range of lines: p d c s'
    start, end, param, param_list = parse_args(args)
    start, end = mk_range(start, end)
    valid = range_ok(start, end)
    if not valid:
        print('? invalid address')
    return valid, start, end, param, param_list

def parse_check_range_dest(args):
    'for cmds that can affect a range of lines and a destination: m t'
    valid, start, end, dest, x = parse_check_range(args)
    if valid:
        dest, x = match_address(dest)
        # dest can be 0 because lines are moved to *after* dest
        dest_valid = iline_ok0(dest)
        if not dest_valid:
            print('? invalid destination')
    return (valid and dest_valid), start, end, dest

# central data structure and variables

# Each ed command is implemented by a function with the same
# one-letter name, whose arguments are the same as the ed command
# args.  The current buffer is used by many of these functions but to
# make the API similar to ed commands, it cannot appear as an arg. 
# So the current buffer, buf, must be global.

buffers = dict() # dict from buffer names (strings) to Buffer instances
deleted = list() # most recently deleted lines from any buffer, for yank command
deleted_mark = list() # markers for deleted lines, for yank command
                 
# There is always a current buffer so we can avoid check for special case
# Start with one empty buffer named 'main', can't ever delete it
current = 'main'
buf = buffer.Buffer(current, caller=sys.modules[__name__]) # caller = this module  
buffers[current] = buf 

# line addresses

def o():
    'Return index of the current line (called dot), 0 if the buffer is empty'
    return buf.dot

def S():
    'Return index of the last line, 0 if the buffer is empty'
    return buf.S()

def k(*args):
    """
    Mark addressed line in this buffer with character c (the command parameter),
    to use with 'c address form.  'c address identifies both buffer and line.
    """
    valid, iline, marker = parse_check_iline(args)
    if valid:
        c = marker[0]
        buf.mark[c] = iline
        print("Mark %s set at line %d in buffer %s" % (c, iline, current))

# search

def F(pattern):
    """Forward Search for pattern, 
    return line number where found, dot if not found"""
    return buf.F(pattern)

def R(pattern):
    """Backward search for pattern, 
    return line number where found, dot if not found"""
    return buf.R(pattern)

def current_filename(filename):
    """
    Return filename arg if present, if not return current filename.
    Do not change current filename, assign only if it was previously absent.
    """
    if filename:
        if not buf.filename:
            buf.filename = filename
        return filename
    if buf.filename:
        return buf.filename 
    print('? no current filename')
    return None

def b_new(name):
    'Create buffer with given name. Replace any existing buffer with same name'
    global current, buf
    buf = buffer.Buffer(name, caller=sys.modules[__name__]) # caller = this module
    buffers[name] = buf # replace buffers[name] if it already exists
    current = name

def b(*args):
    """
    Set current buffer to name.  If no buffer with that name, create one.
    If no name given, print the name of the current buffer.
    """
    global current, buf
    x, xx, bufname, xxx = parse_args(args)
    if not bufname:
        print_status(current, o())
    elif bufname in buffers:
        current = bufname
        buf = buffers[current]
    else:
        b_new(bufname)

def r_new(buffername, filename):
    'Create new buffer, Read in file contents'
    b_new(buffername)
    buf.filename = filename
    r(0, filename)
    buf.unsaved = False # insert in r sets unsaved = True, this is exception

def f(*args):
    'set default filename, if filename not specified print current filename'
    x, xx, filename, xxx = parse_args(args)
    if filename:
        buf.f(filename)
        return
    if buf.filename:
        print(buf.filename)
        return
    print('? no current filename')

def E(*args):
    'read in file, replace buffer contents despite unsaved changes'
    x, xx, filename, xxx = parse_args(args)
    if not filename:
        filename = buf.filename
    if not filename:
        print('? no current filename')
        return
    r_new(current, filename) # replace previous current buffer with new

def e(*args):
    'read in file, replace buffer contents unless unsaved changes'
    if buf.unsaved:
        print('? warning: file modified')
        return
    E(*args)

def r(*args):
    'Read file contents into buffer after iline'
    valid, iline, fname = parse_check_iline0(args)
    if valid:
        filename = current_filename(fname)
        if filename:
            S0 = S()
            buf.r(iline, filename)
            print('%s, %d lines' % (filename, S()-S0))

def B(*args):
    'Create new Buffer and load the named file. Buffer name is file basename'
    x, xx, filename, xxx = parse_args(args)
    if not filename:
        print('? file name')
        return
    buffername = os.path.basename(filename) # may differ from filename
    if buffername in buffers:
        # FIXME? create new buffername a la emacs name<1>, name<2> etc.
        print('? buffer name %s already in use' % buffername)
        return
    r_new(buffername, filename)

def w(*args):
    'write current buffer contents to file name'
    x, xx, fname, xxx = parse_args(args)
    filename = current_filename(fname)
    if filename: # if not, current_filename printed error msg
        buf.w(filename)
        print('%s, %d lines' % (filename, S()))

D_count = 0 # number of consecutive times D command has been invoked

def D(*args):
    'Delete the named buffer, if unsaved changes print message and exit'
    global D_count
    x, xx, bufname, xxx = parse_args(args)
    name = bufname if bufname else current
    if name in buffers and buffers[name].unsaved and not D_count:
        print('? unsaved changes, repeat D to delete')
        D_count += 1 # must invoke D twice to confirm, see message below
        return
    DD(*args)

def DD(*args):
    'Delete the named buffer, even if it has unsaved changes'
    global current, buf
    x, xx, bufname, xxx = parse_args(args)
    name = bufname if bufname else current
    if not name in buffers:
        print('? buffer name')
    elif name == 'main':
        print("? Can't delete main buffer")
    else:
        del buffers[name]
        if name == current: # pick a new current buffer
            keys = list(buffers.keys())
            current = keys[0] if keys else None
            buf = buffers[current]
        print('%s, buffer deleted' % name)

# Displaying information

def print_status(bufname, iline):
    'used by e and n, given bufname and iline prints dot, $, filename, unsaved'
    ibuf = buffers[bufname] # avoid name confusion with global buf
    loc = '%s/%d' % (iline, len(ibuf.lines)-1) # don't count empty first line
    print('%7s  %s%s%-12s  %s' % (loc, 
                               '.' if bufname == current else ' ',
                               '*' if ibuf.unsaved else ' ', 
                               bufname, (ibuf.filename if ibuf.filename else 
                                         'no current filename')))

def A(*args):
    ' = in command mode, print the line number of the addressed line'
    iline, x, xx, xxx = parse_args(args)
    iline = iline if iline != None else S() # default $ not .
    if iline_ok0(iline): # don't print error message when file is empty
        print(iline)
    else:
        print('? invalid address')

def n(*args):
    'Print status of all buffers'
    print("""    ./$    Buffer        File
    ---    ------        ----""")
    for name in buffers:
        print_status(name, buffers[name].dot)
    
# Displaying and navigating text
    
def l(*args):
    'Advance dot to iline and print it'
    iline, x, xx, xxx = parse_args(args)
    if not buf.lines:
        print('? empty buffer')
        return
    # don't use usual default dot here, instead advance dot
    if iline == None:
        iline = o() + 1
    if not iline_ok(iline):
        print('? invalid address')
        return
    print(buf.l(iline), file=destination) # can redirect to os.devnull etc.

def p_lines(start, end, destination): # arg here shadows global destination
    'Print lines start through end, inclusive, at destination'
    for iline in range(start, end+1): # +1 because start,end is inclusive
        print(buf.l(iline), file=destination) # file can be null or stdout or ...

def p(*args):
    'Print lines from start up to end, leave dot at last line printed'
    valid, start, end, x, xx = parse_check_range(args)
    if valid:
        p_lines(start, end, sys.stdout) # print unconditionally
    
def z(*args):
    """
    Scroll: print buf.npage lines starting at iline.
    Leave dot at last line printed. If parameter is present, update buf.npage
    """
    valid, iline, npage_string = parse_check_iline(args)
    if valid: 
        if npage_string:
            try:
                npage = int(npage_string)
            except:
                print('? integer expected: %s' % npage_string)
                return 
            if npage < 1:
                print('? integer > 1 expected %d' % npage)
                return
            buf.npage = npage
        end = iline + buf.npage 
        end = end if end <= S() else S()
        p_lines(iline, end, destination) # global destination might be null

# Adding, changing, and deleting text

def a(*args):
    'Append lines from string after  iline, update dot to last appended line'
    valid, iline, lines = parse_check_iline0(args)
    if valid and lines:
        buf.a(iline, lines)

def i(*args):
    'Insert lines from string before iline, update dot to last inserted line'
    valid, iline, lines = parse_check_iline0(args)
    if valid and lines:
        buf.i(iline, lines)

def d(*args):
    'Delete text from start up to end, set dot to first line after deletes or...'
    valid, start, end, x, xx = parse_check_range(args)
    if valid:
        buf.d(start, end)

def c(*args):
    'Change (replace) lines from start up to end with lines from string'
    valid, start, end, lines, xx = parse_check_range(args)
    if valid:
        buf.c(start,end,lines)
        
def s(*args):
    """
    Substitute new for old in lines from start up to end.
    When glbl is False (the default), substitute only the first occurrence 
    in each line.  Otherwise substitute all occurrences in each line
    """
    valid, start, end, old, params = parse_check_range(args)
    if valid:
        # params might be [ new, glbl ]
        if old and len(params) > 0 and isinstance(params[0],str):
            new = params[0]
        else:
            print('? /old/new/')
            return
        if len(params) > 1:
            glbl = bool(params[1])
        else:
            glbl = False # default
        buf.s(start, end, old, new, glbl)

def m(*args):
    'move lines to after destination line'
    valid, start, end, dest = parse_check_range_dest(args)
    if valid:
        if (start <= dest <= end):
            print('? invalid destination')
            return
        buf.m(start, end, dest)

def t(*args):
    'transfer (copy) lines to after destination line'
    valid, start, end, dest = parse_check_range_dest(args)
    if valid:
        buf.t(start, end, dest)

def y(*args):
    'Insert most recently deleted lines *before* destination line address'
    iline, x, xx, xxx = parse_args(args)
    iline = mk_iline(iline)
    if not (0 <= iline <= buf.S()+1): # allow +y at $ to append to buffer
        print('? invalid address')
        return
    buf.y(iline)

# command mode

quit = False

def q(*args):
    'quit command mode, ignore args, caller quits'
    global quit
    quit = True

complete_cmds = 'deEflpqrswzbBDnAykmt' # commands that do not require further input
input_cmds = 'aic' # commands that use input mode to collect text
ed_cmds = complete_cmds + input_cmds

# regular expressions for line address forms and other command parts
number = re.compile(r'(\d+)')
fwdnumber = re.compile(r'\+(\d+)')
bkdnumber = re.compile(r'\-(\d+)')
bkdcnumber = re.compile(r'\^(\d+)')
plusnumber = re.compile(r'(\++)')
minusnumber = re.compile(r'(\-+)')
caratnumber = re.compile(r'(\^+)')
fwdsearch = re.compile(r'/(.*?)/') # non-greedy *? for /text1/,/text2/
bkdsearch = re.compile(r'\?(.*?)\?')
text = re.compile(r'(.*)') # nonblank
mark = re.compile(r"'([a-z])")  # 'c, ed mark with single lc char label

def match_address(cmd_string):
    """
    Return line number for address at start of cmd_string (None of not found), 
     and rest of cmd_string.
    This is where we convert the various line address forms to line numbers.
    All other code in this module and the buffer module uses line numbers only.
    """
    if cmd_string == '':
        return None, '' 
    if cmd_string[0] == '.': # current line
        return o(), cmd_string[1:]
    if cmd_string[0] == '$': # last line
        return S(), cmd_string[1:]
    if cmd_string[0] == ';': # equivalent to .,$  - current line to end
        return o(), ',$'+ cmd_string[1:]
    if cmd_string[0] in ',%': # equivalent to 1,$ - whole buffer
        return 1, ',$'+ cmd_string[1:]
    m = number.match(cmd_string) # digits, the line number
    if m:
        return int(m.group(1)), cmd_string[m.end():]
    m = fwdnumber.match(cmd_string) # +digits, relative line number forward
    if m:
        return o() + int(m.group(1)), cmd_string[m.end():]
    m = bkdnumber.match(cmd_string) # -digits, relative line number backward
    if m:
        return o() - int(m.group(1)), cmd_string[m.end():]
    m = bkdcnumber.match(cmd_string) # ^digits, relative line number backward
    if m:
        return o() - int(m.group(1)), cmd_string[m.end():]
    m = plusnumber.match(cmd_string) # + or ++ or +++ ...
    if m:
        return o() + len(m.group(0)), cmd_string[m.end():]
    m = minusnumber.match(cmd_string) # digits, the line number
    if m:
        return o() - len(m.group(0)), cmd_string[m.end():]
    m = caratnumber.match(cmd_string) # digits, the line number
    if m:
        return o() - len(m.group(0)), cmd_string[m.end():]
    m = fwdsearch.match(cmd_string)  # /text/ or // - forward search
    if m: 
        return buf.F(m.group(1)), cmd_string[m.end():]
    m = bkdsearch.match(cmd_string)  # ?text? or ?? - backward search
    if m: 
        return buf.R(m.group(1)), cmd_string[m.end():]
    m = mark.match(cmd_string) # 'c mark with single lc char label
    if m: 
        c = m.group(1)
        i = buf.mark[c] if c in buf.mark else -9999 # invalid address
        return i, cmd_string[m.end():] 
    return None, cmd_string

def parse_cmd(cmd_string):
    """
    Parses cmd_string, returns multiple values in this order:
     cmd_name - single-character command name
     start, end - integer line numbers 
     params - string containing other command parameters
    All are optional except cmd_name, assigns None if item is not present
    """
    global D_count
    cmd_name, start, end, params = None, None, None, None
    # look for start addr, optional. if no match start,tail == None,cmd_string
    start, tail = match_address(cmd_string)
    # look for end address, optional
    if start != None:
        if tail and tail[0] == ',': # addr separator, next addr NOT optional
            end, tail = match_address(tail[1:])
            if end == None:
                print('? end address expected at %s' % tail)
                return 'ERROR', start, end, params
    # look for cmd_string, NOT optional
    if tail and tail[0] in ed_cmds:
        cmd_name, params = tail[0], tail[1:].strip()
    # special case command names
    elif tail == '':
        cmd_name = 'l' # default for empty cmd_string
    elif tail[0] == '=':
        cmd_name = 'A'
    else:
        print('? command expected at %s' % tail)
        return 'ERROR', start, end, params
    # special handling for commands that must be repeated to confirm
    D_count = 0 if cmd_name != 'D' else D_count
    # command-specific parameter parsing
    if cmd_name == 's' and len(params.split('/')) == 4: # s/old/new/g, g optional
        empty, old, new, glbl = params.split('/') # glbl == '' when g absent
        return cmd_name, start, end, old, new, glbl
    # all other commands, no special parameter parsing
    else:
        return cmd_name, start, end, params if params else None 

# state variables that must persist between ed_cmd invocations during input mode
command_mode = True # alternates with input mode used by a,i,c commands
cmd_name = '' # command name, must persist through input mode
args = []  # command arguments, must persist through input mode

pysh = pysh.mk_shell() # embedded Python shell for ! command

def cmd(line):
    """
    Process one input line without blocking in ed command or input mode
    Update buffers and control state variables: command_mode, cmd_name, args
    """
    # state variables that must persist between cmd invocations during input mode
    global command_mode, cmd_name, args
    if command_mode:
        if line and line[0] == '!': # special case - not a 1-char cmd_name
            pysh(line[1:]) # execute Python expression or statement
            return
        items = parse_cmd(line)
        if items[0] == 'ERROR':
            return None # parse_cmd already printed message
        else:
            tokens = tuple([ t for t in items if t != None ])
        cmd_name, args = tokens[0], tokens[1:]
        if cmd_name in complete_cmds:
            globals()[cmd_name](*args) # dict from name (string) to object (fcn)
        elif cmd_name in input_cmds:
            command_mode = False # enter input mode
            # Instead of using buf.a, i, c, we handle input mode cmds inline here
            # We will add each line to buffer when user types RET at end-of-line,
            # *unlike* in Python API where we pass multiple input lines at once.
            start, end, x, xxx = parse_args(args) # might be int or None
            start, end = mk_range(start, end) # int only
            if not (iline_ok0(start) if cmd_name in 'ai'
                    else range_ok(start, end)):
                print('? invalid address')
                command_mode = True
            # assign dot to prepare for input mode, where we a(ppend) each line
            elif cmd_name == 'a':
                buf.dot = start
            elif cmd_name == 'i': #and start >0: NOT! can insert in empty file
                buf.dot = start - 1 if start > 0 else 0 
                # so we can a(ppend) instead of i(nsert)
            elif cmd_name == 'c': # c(hange) command deletes changed lines first
                buf.d(start, end) # updates buf.dot
                buf.dot = start - 1
            else:
                print('? command not supported in input mode: %s' % cmd_name)
        else:
            print('? command not implemented: %s' % cmd_name)
        return
    else: # input mode for a,i,c commands that collect text
        if line == '.':
            command_mode = True # exit input mode
        else:
            # Recall raw_input returns each line with final \n stripped off,
            # BUT buf.a requires \n at end of each line
            buf.a(o(), line + '\n') # append new line after dot, advance dot
        return

prompt = '' # default no prompt

def main(*filename, **options):
    """
    Top level ed command to use at Python prompt.
    This version won't work in Piety, it calls blocking command raw_input
    """
    global cmd_name, quit, prompt
    quit = False # allow restart
    if filename:
        e(filename[0])
    if 'p' in options:
        prompt = options['p'] 
    while not quit:
        line = input(prompt) # blocking
        cmd(line) # non-blocking

# Run the editor from the system command line:  python ed.py

if __name__ == '__main__':
    main()
