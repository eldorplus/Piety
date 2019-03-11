"""
edda.py - Defines the ed Console job that wraps the ed.py line editor,
  along with the wyshka enhanced Python shell and samysh script execution.
  Contrast to the ed.py main function and etty.py.

To run from the Python prompt, type from edda import * then edda() or ed.run().
To use the ed API from the Python prompt, use prefix as in edo.ed.p() 
"""

import edo, wyshka, console

ed = console.Console(prompt=(lambda: wyshka.prompt), 
                     process_line=edo.process_line,
                     stopped=(lambda command: edo.ed.quit),
                     startup=edo.startup)

ed.keymap = (lambda: (ed.command_keymap 
                      if edo.ed.command_mode
                      else ed.input_keymap))

def edda(*filename, **options):
    ed.run(*filename, **options)

if __name__ == '__main__':
    filename, options = edo.ed.cmd_options()
    edda(*filename, **options)
