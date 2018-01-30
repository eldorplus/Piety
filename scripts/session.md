
session.py
==========

**session.py**: Creates a *Session* instance with three *Console*
jobs: the *pysh* shell, the *ed* line editor, and the *edsel*
display editor.

Here is a typical session, that shows how to invoke each job.  The
*pysh* job (a Python interpreter) runs at startup.  Invoke the other
jobs from the Python prompt by name using function call syntax (which invokes
each job's *__call__* method).  Exit from each job to return to the
Python interpreter.  Each job (including the Python interpreter)
preserves its state between invocations, so work in progress can be
resumed.  Moreover the line editor *ed* and the display editor *edsel*
share the same state including editor buffers and insertion points.

    ...$ python3 session.py
    >> dir()
    ...
    >> ed()
    : e README.md
    ... edit in README.md
    :q
    >> import datetime
    ...
    >> edsel()
    ... display editor appears, shows README.md
    ... continue editing README.md
    :q
    >> datetime.datetime.now()
    ... datetime module is still imported
    >> ed()
    ... continue editing README.md
    :q
    >> exit()
    ...$

The *session* module also demonstrates job control, including the
*job* function that lists the jobs, the *^Z* command for suspending a job
and the *fg* (foreground) function that resumes the most recently
suspended job:

    $ python3 session.py
    >> jobs()
    <console.Console object at 0x10301af60>   pysh     State.foreground
    <console.Console object at 0x1030274a8>   ed       State.loaded
    <console.Console object at 0x1030462e8>   edsel    State.loaded
    >> ed()
    :!jobs()
    <console.Console object at 0x1030274a8>   ed       State.foreground
    <console.Console object at 0x10301af60>   pysh     State.background
    <console.Console object at 0x1030462e8>   edsel    State.loaded
    :q

    >> jobs()
    <console.Console object at 0x10301af60>   pysh     State.foreground
    <console.Console object at 0x1030274a8>   ed       State.suspended
    <console.Console object at 0x1030462e8>   edsel    State.loaded
    >> edsel()
    ... 

    :!jobs()
    <console.Console object at 0x1030462e8>   edsel    State.foreground
    <console.Console object at 0x10301af60>   pysh     State.background
    <console.Console object at 0x1030274a8>   ed       State.suspended
    :^Z
    Stopped
    >> jobs()
    <console.Console object at 0x10301af60>   pysh     State.foreground
    <console.Console object at 0x1030462e8>   edsel    State.suspended
    <console.Console object at 0x1030274a8>   ed       State.suspended
    >> fg()
    ... edsel runs again ...

    :!jobs()
    <console.Console object at 0x1030462e8>   edsel    State.foreground
    <console.Console object at 0x10301af60>   pysh     State.background
    <console.Console object at 0x1030274a8>   ed       State.suspended
    :q

    >> jobs()
    <console.Console object at 0x10301af60>   pysh     State.foreground
    <console.Console object at 0x1030462e8>   edsel    State.suspended
    <console.Console object at 0x1030274a8>   ed       State.suspended
    
Revised Jan 2018