"""
window.py - Window class for line-oriented display editors.

Each window displays a range of lines - a segment - from a text buffer.
"""

import display

diagnostics = None # assign to update record to show diagnostics on status line

def clip(iline, first, last):
    'return iline limited to range first .. last inclusive'
    return min(max(first, iline), last)

class Window(object):
    """
    Window class for line-oriented display editors.
    Displays a range of lines (the segment) from a text buffer.
    May display a marker to indicate text insertion point (called dot).
    May be followed by a status line with information about the buffer.
    """

    nupdates = 0 # diagnostic, used by update_diagnostics

    def __init__(self, buf, top, nlines, ncols):
        """
        Initialize window, given its text buffer, location,and dimensions
         buf - text buffer displayed in this window
         top - line number on display of first buffer line in window
         nlines - number of lines in this window, excluding status line
         ncols - maximum number of characters in a line
        """
        self.focus = False # True when this window has the input focus
        self.buf = buf
        self.saved_dot = self.buf.dot 
        self.btop = 1 # index in buffer of first line displayed in window
        self.resize(top, nlines, ncols) # assigns self.top .nlines .ncols
        self.blast = self.blastline() # buffer can get out of synch

        # Diagnostics
        self.first = 0    # first line printed on window in this update
        self.nprinted = 0 # n of lines printed on window in this update

    def resize(self, top, nlines, ncols):
        """
        Assign, recalculate window dimensions
         top - line number on display of first line of window
         nlines - n of lines in window, excludling status line
         ncols - maximum number of characters in a line
        """
        self.top = top
        self.nlines = nlines 
        self.ncols = ncols
        self.buf.npage = self.nlines #initial page size for ed z page cmd

    def wline(self, iline):
        'Line number on display of iline in buffer.'
        return self.top + (iline - self.btop)

    def bottom(self):
        'Line num. on display of bottom line in window (not status line)'
        return self.top + self.nlines - 1

    def bbottom(self):
        'Index in buffer of bottom line in window. May exceed buffer size'
        return self.btop + self.nlines - 1

    def blastline(self):
        """
        Index in buffer of last line in window, maybe not bottom of window.
        Assumes that last line in window is up-to-date with buffer size.
        """
        return min(self.bbottom(), self.buf.S())
 
    def statusline(self):
         "Line number on display of window's status line"
         return self.bottom() + 1

    def near_top(self, iline):
        """
        Line number in buffer iline is in
        top half of segment at beginning of buffer that fits in window.
        """
        return (iline <= self.nlines//2 or self.buf.S() <= self.nlines)

    def near_bottom(self, iline):
        """
        Line number in buffer iline is in
        bottom half of segment at end of buffer that fits in window.
        """
        return (self.buf.S() - iline < self.nlines//2 and
                self.buf.S() >= self.nlines)
 
    def empty_line(self, iline):
        'Line number iline in buffer is empty, or is just \n'
        return self.buf.lines[iline] in ('','\n')

    def contains(self, iline):
        'Line number iline in buffer is one of the lines present in the window'
        return (self.btop <= iline <= self.blast)

    def covers(self, iline):
        'Line number iline in buffer is in range of lines covered by window.'
        return (self.btop <= iline <= self.bbottom())

    def intersects(self, start, end):
        'Window intersects range defined by start..end'
        return (self.contains(start) or self.contains(end)
                or (start < self.btop and end > self.bbottom()))

    def ch0(self, iline):
        'First character in line iline in buffer, or space if line empty'
        return ' ' if self.empty_line(iline) else self.buf.lines[iline][0]

    def put_marker(self, iline, clear=False):
        'Set or clear marker on buffer line iline, or top line if buffer empty'
        display.put_render(self.top if self.buf.empty() else self.wline(iline),
                           1, self.ch0(iline), 
                           display.clear if clear else display.white_bg)
        
    def set_marker(self, iline):
        'Set marker on buffer line iline, or top line if buffer empty'
        self.put_marker(iline)

    def clear_marker(self, iline):
        'Clear marker from buffer line iline, or top line if buffer empty'
        self.put_marker(iline, clear=True)

    def scroll(self, nlines):
        """
        Move segment of buffer displayed in window by nlines (pos or neg)
        but leave dot unchanged so window contents appear to scroll.
        """
        self.btop = clip(self.btop + nlines, 1, self.buf.S())
        self.blast = self.blastline()

    def shift(self, nlines):
        """
        Move segment of buffer displayed in window by nlines (pos or neg)
        and shift saved_dot also so window contents appear the same.
        This is only meaningful for the windows without input focus.
        """
        self.scroll(nlines)
        self.saved_dot = clip(self.saved_dot + nlines, 1, self.buf.S())

    def locate_segment(self, iline):
        """
        Given line number in buffer iline, prepare to position window by
        assigning self.btop, index in buffer of top line in window.
        """
        if self.near_top(iline):
            self.btop = 1  
        elif self.near_bottom(iline):
            self.btop = self.buf.S() - (self.nlines - 1) # last page
        else: 
            self.btop = iline - self.nlines//2 # center iline in window
        self.blast = self.blastline()

    def open_line(self, wiline):
        'Make line empty at line number wiline on display'
        #if self.top <= wiline <= self.top + self.nlines-1: # omit,let it crash
        display.put_cursor(wiline, 1)
        display.kill_whole_line()

    def clear_lines(self, first, last):
        """
        Clear consecutive lines from first through last in window.
        Cursor must be positioned at first line already.
        """
        for i in range(first,last+1): # unempty if reached end of buffer
            display.kill_whole_line()
            print()

    def render_lines(self, first, last):
        """
        Print lines in buffer numbered first through last.
        Assumes cursor already positioned at first line.
        """
        i = -1
        for i, line in enumerate(self.buf.lines[first:last+1]):
            print(line.rstrip()[:self.ncols-1], end=' ') # remove \n, truncate
            display.kill_line()
            print()
        return i+1 # fewer than first:last+1 when at end of buffer

    def update_lines(self, first, iline, last=0):
        """
        Write lines in window starting at line numbere first on display,
        to bottom of the window, or to line numbered last if arg present.
        Lines come from self.buf starting at its line iline.
        """
        self.first = first if self.first == 0 else self.first
        last = last if last else self.bottom()
        blastlinenum = iline + (last - first) # might exceed $ near eob
        display.put_cursor(first, 1)
        nprinted = self.render_lines(iline, blastlinenum)
        icursor = first + nprinted
        self.nprinted += nprinted
        self.clear_lines(icursor, last)
        
    def update_from(self, iline):
        'Write lines in window starting at line number iline in buffer'
        self.update_lines(self.wline(iline), iline)
        self.update_status()

    def update(self):
        'Write all lines in window'
        self.update_from(self.btop)

    def move_update(self, iline):
        'Move window to show buffer line iline then update window'
        self.locate_segment(iline)
        self.update()
        if self.focus:
            self.set_marker(iline)

    def reupdate(self):
        'Move window to show its buf.dot then update window'
        self.move_update(self.buf.dot)

    def locate(self, origin, destination):
        'Update window after cursor moves from origin to destination'
        if self.contains(destination):
            self.clear_marker(origin)
            self.set_marker(destination)
            self.update_status()
        else:
            self.reupdate()

    def insert(self, origin, start, end):
        'Update window after insert lines from origin to start..end'
        if self.contains(end):
            if origin != 0:
                self.clear_marker(origin)
            self.update_from(start)
        else:
            self.reupdate()

    def delete(self, destination):
        'Update window after delete lines above destination'
        if self.contains(destination): # window already contains new dot
            self.update_from(destination)
            self.set_marker(destination)
        else:
            self.reupdate() 

    def mutate_lines(self, start, destination):
        'Update window after some lines in range start..destination changed'
        top = max(start, self.btop)
        self.update_lines(self.wline(top), top, 
                       last=self.wline(destination))
        self.update_status()

    def mutate(self, origin, start, destination):
        'Update window and move marker after some lines in range changed'
        if self.contains(destination):
            self.clear_marker(origin)
            self.mutate_lines(start, destination)
            self.set_marker(destination)
        else:
            self.reupdate()

# The following methods are only used with the status line

    def update_status_prefix(self):
        "Print information about window's buffer in its status line."
        unsaved = '-----**-     ' if self.buf.unsaved else '--------     ' # 13
        bufname = '%-13s' % self.buf.name
        dot = self.buf.dot if self.focus else self.saved_dot
        position = (' All ' if self.buf.S() <= self.nlines else # S() last line
                    ' Top ' if self.btop == 1 else
                    ' Bot ' if self.blast == self.buf.S() else
                    ' %2.0f%% ' % (100*dot/(len(self.buf.lines)-1)))
        linenums = '%-14s' % ('L%d/%d ' % (dot, self.buf.S()))
        s1 = self.statusline()
        display.put_render(s1, 0, unsaved, display.white_bg)
        display.put_render(s1, 13, bufname, display.bold, display.white_bg)
        display.put_render(s1, 22, position, display.white_bg) # was 26
        display.put_render(s1, 27, linenums, display.white_bg) # was 31

    def update_status(self):
        "Print information about window's buffer in its status line."
        self.update_status_prefix()
        if diagnostics:
            self.update_diagnostics()
            return
        s1 = self.statusline()
        display.put_render(s1, 45, '-'*(self.ncols-45), display.white_bg)

    def update_diagnostics(self):
        "Print diagnostic and debug information in the status line."
        Window.nupdates += 1 # ensure at least this changes in status line
        update_info = '%3d %3s o:%3d d:%3d s:%3d e:%3d, f:%3d n:%3d' % \
            (Window.nupdates, str(diagnostics.op)[3:6], diagnostics.origin, 
             diagnostics.destination, diagnostics.start, diagnostics.end, 
             self.first, self.nprinted)
        s1 = self.statusline()
        display.put_render(s1, 36, update_info, display.white_bg) # was 40
        display.kill_line()
        self.first = 0    # reset after each update
        self.nprinted = 0

# The following methods are only used with input mode

    def update_for_input(self):
        """
        Open next line and overwrite lines below.
        If at bottom of window, scroll insertion point up to the middle.
        """
        wdot = self.wline(self.buf.dot) # line on display where dot appears
        if wdot > 0:
            self.clear_marker(self.buf.dot)
        if wdot >= self.top + self.nlines - 1: # at bottom of window
            self.scroll(self.nlines//2)
            wdot = self.top + (self.buf.dot - self.btop)
            self.update_lines(self.top, self.buf.dot-self.nlines//2+1, 
                              last=wdot)
        self.open_line(wdot+1)
        self.update_lines(wdot+2, self.buf.dot+1)
        self.update_status()

    def put_cursor_for_input(self):
        'Place input cursor for insert after update_for_input, above'
        wdot = self.wline(self.buf.dot)
        display.put_cursor(wdot+1,1)

# The following methods are only used with multiple windows

    def samebuf(self, win):
        'True when this window differs from win but uses the same buffer'
        return (self != win and self.buf == win.buf)

    def set_focus(self):
        'Set input focus to this window'
        self.focus = True
        self.buf.dot = self.saved_dot
        self.set_marker(self.buf.dot)

    def release_focus(self):
        'Release input focus from this window'
        self.focus = False
        self.saved_dot = self.buf.dot
        self.clear_marker(self.saved_dot)

    def adjust_insert(self, start, end, destination):
        'After insert, adjust segment visible in a window without input focus'
        # start, end are line numbers *after* insert is executed in buffer.
        # ed i() inserts text *before* dot, so start == buf.dot before execute.
        # destination == end, last inserted line *after* insert executed in buf
        nlines = end - start + 1
        if self.saved_dot == 0:  # buffer was empty
            self.saved_dot = self.buf.dot
            self.move_update(self.saved_dot)
            self.update_status()
        elif self.covers(start):
            if self.saved_dot >= start:
                self.saved_dot = self.saved_dot + nlines
            self.move_update(self.saved_dot)
            self.update_status()
        elif self.btop >= start:
            self.shift(nlines)
            self.update_status()
        elif self.blast < start:
            self.update_status() # xx% nn/mm in status line changes
        else:
            pass # should be unreachable! status line doesn't update

    def adjust_delete(self, start, end, destination):
        'After delete, adjust segment visible in a window without input focus'
        # start, end are line numbers *before* delete is executed in buffer.
        # destination is first unchanged line *after* delete executed in buf.
        nlines = -(end - start + 1)
        if self.intersects(start, end):
            if self.saved_dot < start:
                pass
            elif self.saved_dot > end:
                self.saved_dot = self.saved_dot + nlines
            else:
                self.saved_dot = destination 
            self.move_update(self.saved_dot)
            self.update_status()
        elif self.btop > end:
            self.shift(nlines)
            self.update_status()
        elif self.blast < start:
            self.update_status() # xx% nn/mm in status line changes
        else:
            pass # should be unreachable! status line doesn't update
