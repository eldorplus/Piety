"""
console_tasks.py - Create Piety console jobs and session used by piety script
"""
import sys
import piety, session, job, command, keyboard, key
import pysh, ed, edd as _edd # rename edd module so we can use edd as job name

class Namespace(object): pass # another way to avoid name clashes
jobs = Namespace()

# Session, a terminal task
console = session.Session(name='console', event=sys.stdin)

# Python shell

def pysh_startup():
    pysh.pexit = False # enable pysh event loop, compare to Job stopped= below

# Name the command pyshc to avoid name clash with pysh module
# Assign reader=key.Key that handles some multicharacter control sequences
pyshc = command.Command(prompt='>> ', reader=key.Key(),  handler=pysh.mk_shell())

# Put pysh job in the jobs namespace to avoid name clash with pysh module
# stopped=... enables exit on exit() command or ^D
jobs.pysh = job.Job(session=console, application=pyshc, startup=pysh_startup, 
                    stopped=(lambda: pysh.pexit or pyshc.command == keyboard.C_d), 
                    cleanup=piety.quit)

# line editor

# startup function handles optional filename argument and optional keyword arg.
def ed_startup(*filename, **options):
    if filename:
        ed.e(filename[0])
    if 'p' in options:
        edc.application.prompt = options['p'] 
    ed.quit = False # enable event loop, compare to Job( stopped=...) arg below

# Name the job edc to avoid name clash with ed module.
# Use default reader, not key.Key, so multicharacter control sequences
#  (such as keyboard arrow keys) will not work.
# Exit with q only, ^D exit is not enabled
edc = job.Job(session=console,
              application=command.Command(prompt='', handler=ed.cmd),
              startup=ed_startup, stopped=(lambda: ed.quit))
              
# display editor

# startup function handles optional filename argument and optional keyword arg.
def edd_startup(*filename, **options):
    _edd.ed.quit = False # enable event loop, compare to Job( stopped=..) arg below
    if 'p' in options:
        edd.application.prompt = options['p'] #edd *not* _edd, Piety command object
    _edd.init_display(*filename, **options) # _ed.prompt is not used by Piety

# edd module was imported as _edd so we can call the job edd without name clash
edd = job.Job(session=console, 
              application=
              command.Command(prompt='', reader=key.Key(), handler=_edd.cmd),
              startup=edd_startup, 
              cleanup=_edd.restore_display)

# Enable exit with q or ^D, must use separate statement so application has a name
edd.stopped=(lambda: _edd.ed.quit or edd.application.command == keyboard.C_d)

# Make edd.main an alias for edd.__call__ so we can call edd.main(...) using
#  exactly the same syntax as when we import edd.py into Python without Piety
edd.main = edd.__call__