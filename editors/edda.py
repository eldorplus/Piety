"""
edda.py - Defines the ed Console job that wraps the ed.py line editor,
  along with the wyshka enhanced Python shell and samysh script execution.
  Contrast to the ed.py main function and etty.py.
"""

import edo, wyshka, console

ed = console.Console(prompt=(lambda: wyshka.prompt), 
                     do_command=edo.do_command,
                     stopped=(lambda command: edo.ed.quit),
                     keymap=(lambda: (console.command_keymap 
                                      if edo.ed.command_mode 
                                      else console.insert_keymap)),
                     startup=edo.ed.start, cleanup=edo.ed.q)

def main():
    ed.run()

if __name__ == '__main__':
    filename, options = edo.ed.cmd_options()
    edo.ed.startup(*filename, **options)
    main()
