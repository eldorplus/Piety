"""
parse.py - command line parsing for ed.py
"""

import re

complete_cmds = 'AbBdDeEfkKlmnpqrstwyz' # commands that do not use input mode
input_cmds = 'aci' # commands that use input mode to collect text
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

def line_address(buf, cmd_string):
    """
    Return line number for address at start of cmd_string (None of not found), 
     also return rest of cmd_string.
    This is where we convert the various line address forms to line numbers.
    All other code in ed.py and related modules uses line numbers only.
    """
    if cmd_string == '':
        return None, '' 
    if cmd_string[0] == '.': # current line
        return buf.dot, cmd_string[1:]
    if cmd_string[0] == '$': # last line
        return buf.nlines(), cmd_string[1:]
    if cmd_string[0] == ';': # equivalent to .,$  - current line to end
        return buf.dot, ',$'+ cmd_string[1:]
    if cmd_string[0] in ',%': # equivalent to 1,$ - whole buffer
        return 1, ',$'+ cmd_string[1:]
    m = number.match(cmd_string) # digits, the line number
    if m:
        return int(m.group(1)), cmd_string[m.end():]
    m = fwdnumber.match(cmd_string) # +digits, relative line number forward
    if m:
        return buf.dot + int(m.group(1)), cmd_string[m.end():]
    m = bkdnumber.match(cmd_string) # -digits, relative line number backward
    if m:
        return buf.dot - int(m.group(1)), cmd_string[m.end():]
    m = bkdcnumber.match(cmd_string) # ^digits, relative line number backward
    if m:
        return buf.dot - int(m.group(1)), cmd_string[m.end():]
    m = plusnumber.match(cmd_string) # + or ++ or +++ ...
    if m:
        return buf.dot + len(m.group(0)), cmd_string[m.end():]
    m = minusnumber.match(cmd_string) # digits, the line number
    if m:
        return buf.dot - len(m.group(0)), cmd_string[m.end():]
    m = caratnumber.match(cmd_string) # digits, the line number
    if m:
        return buf.dot - len(m.group(0)), cmd_string[m.end():]
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

def command(buf, cmd_string):
    """
    Parse ed.py command string, return multiple values in this order:
     cmd_name - single-character command name
     start, end - integer line numbers 
     params - string containing other command parameters
    All are optional except cmd_name, assign None if an item is not present
    """
    global D_count
    cmd_name, start, end, params = None, None, None, None
    # look for start addr, optional. if no match start,tail == None,cmd_string
    start, tail = line_address(buf, cmd_string)
    # look for end address, optional
    if start != None:
        if tail and tail[0] == ',': # ',' means next addr is NOT optional
            end, tail = line_address(buf, tail[1:]) # reassign tail
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
    if cmd_name == 's' and len(params.split('/')) == 4: #s/old/new/g,g optional
        empty, old, new, glbl = params.split('/') # glbl == '' when g absent
        return cmd_name, start, end, old, new, glbl
    # all other commands, no special parameter parsing
    else:
        # return each space-separated parameter as separate arg in sequence
        return (cmd_name,start,end) + (tuple(params.split() if params else ()))

def arguments(args):
    """ 
    Parse variable-length argument list for ed.py Python API, all args optional
    Return fixed length tuple: start, end, text, params 
    start, end are line numbers, for example the first and last line of region.
    When present, start and end are int, both might be absent, indicated None.
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