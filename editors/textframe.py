"""
textframe.py - wrap functions in ed.py and text.py, methods in buffer.py
                   with calls to frame.py to update display
"""

import frame, ed, buffer, text

# wrap functions in ed.py

# Save a reference to each of these before we reassign them.
# This is necessary to restore unwrapped fcns, also to break infinite recursion.
ed_l = ed.l
ed_p_lines = ed.p_lines
ed_prepare_input_mode = ed.prepare_input_mode
ed_set_command_mode = ed.set_command_mode

# define wrapped functions
    
def prepare_input_mode(cmd_name, start, end):
    ed_prepare_input_mode(cmd_name, start, end) # not ed.prepare_input_mode
    frame.input_mode()

def set_command_mode():
    ed_set_command_mode()
    frame.command_mode()

# wrap functions in text

# Save a reference to each of these before we reassign them.
# This is necessary to restore unwrapped fcns, also to break infinite recursion.
text_create = text.create
text_select = text.select
text_delete = text.delete

# define the wrapped functions

def create(bufname):
    text_create(bufname)  # not text.create - that creates infinite recursion
    frame.create(text.buf)

def select(bufname):
    text_select(bufname)
    frame.select(text.buf)

def delete(bufname):
    text_delete(bufname)
    frame.remove(text.delbuf, text.buf)

# wrap methods in buffer

# Save a reference to the unwrapped base class before we reassign it.
# This is necessary to restore base class, also to break infinite recursion.
buffer_Buffer = buffer.Buffer

# define class with wrapped methods

class BufferFrame(buffer_Buffer):
    """
    BufferFrame class derived from Buffer
    wrap Buffer methods that cause display updates.
    """
      
    def __init__(self, name):
        super().__init__(name)

    def insert(self, iline, lines):
        'Insert lines before iline'
        super().insert(iline, lines)
        frame.insert(iline, self.dot)          

    def insert_other(self, iline, lines, column):
        """
        Insert lines when this buffer is not the current buffer,
        for example when this buffer is updated by a background task.
        """
        super().insert_other(iline, lines, column)
        frame.insert_other(self, iline, self.dot, column)          

    def r(self, iline, filename):
        'Read file contents into buffer after iline.'
        file_found = super().r(iline, filename)
        if not file_found:
            frame.select(self) # if file_found display already updated
        return file_found

    def w(self, name):
        'Write current buffer contents to file name.'
        super().w(name)
        frame.status(self)

    def l(self, iline):
        'Advance dot to iline and return that line (so caller can print it)'
        line, prev_dot = super().l(iline)
        frame.locate(prev_dot, iline)
        return line, prev_dot

    def d(self, start, end, yank=True):              
        'Delete text from start up through end'
        super().d(start, end, yank)
        frame.delete(start, end)

    def I(self, start, end, indent):
        'Indent lines, add indent leading spaces'
        super().I(start, end, indent)
        frame.mutate(start, end)

    def M(self, start, end, outdent):
        'Indent lines, add indent leading spaces'
        super().M(start, end, outdent)
        frame.mutate(start, end)

    def s(self, start, end, old, new, glbl, use_regex):
        'Substitute new for old in lines from start up to end.'
        match = super().s(start, end, old, new, glbl, use_regex)
        frame.mutate(start, self.dot) # self.dot is last line changed
        return match

    def u(self, iline):
        'Undo last substitution: replace line at iline from cut buffer'
        super().u(iline)
        frame.mutate(iline, iline)

# Enable/disable display by assigning/restoring wrapped/uwrapped fcns, methods

def enable():
    'Enable display by assigning wrapped functions and methods'
    ed.l = ed.l_noprint
    ed.p_lines = ed.p_lines_noprint
    ed.prepare_input_mode = prepare_input_mode
    ed.set_command_mode = set_command_mode
    text.create = create
    text.select = select
    text.delete = delete
    buffer.Buffer = BufferFrame

# disable does NOT really work, because Buffer instances that were
# created while the display was enabled continue to update the display
# even after disable is called.  That's how objects work in Python:
# existing objects' methods are not replaced when their code is updated.
# Fixing this would require turning the Buffer methods into ordinary
# functions at top level, like the functions in text and ed.

def disable():
    'Disable display by restoring unwrapped functions and methods'
    ed.l = ed_l
    ed.p_lines = ed_p_lines
    ed.prepare_input_mode = ed_prepare_input_mode
    ed.set_command_mode = ed_set_command_mode
    text.create = text_create
    text.select = text_select
    text.delete = text_delete
    buffer.Buffer = buffer_Buffer

# Called at application startup to ensure the frame is initialized only once.
# The same application may be started, exited, started again several times
# during a single interactive Python session.
# Also solves a chicken-and-egg problem: When display is enabled, 
# frame must be initialized before the first application buffer is created
# BUT frame.init requires a buffer for initial window, so create a placeholder.

def startup(cmd_h):
    'Initialize frame at application startup.'
    enable() # turn on display updates
    if not frame.win: # create initial window only once in session
        if text.buf: # some application has already created a buffer
            frame.init(cmd_h, text.buf)
        else: # create initial window with placeholder buffer
            frame.init(cmd_h, buffer.Buffer('placeholder'))
    frame.rescale(cmd_h) # assign frame.cmd_h then refresh display

