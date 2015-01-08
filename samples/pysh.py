"""
pysh.py - Callable Python shell, can be embedded in any Python application.
           
pysh (rhymes with "fish") defines the function 'mk_shell' whose
parameters define a configuration, which returns a function (a
closure) that interprets a single Python expression or statement.
This function is the callable Python shell.  We use a closure so we
can create different shells that use different configurations.

At this time the only configuration parameter is the 'globals'
dictionary used by eval and exec to look up names and bind variables.

The default globals dictionary is from the __main__ module so the
shell returned by mk_shell behaves just like the usual top-level
interpreter.  But we could configure the shell differently.

This example shows how to use pysh:

 import pysh
 python = pysh.mk_shell()
 command = "print 'Now it is', datetime.datetime.now()"
 import datetime
 python(command) # prints Now it is ...

See also the main function defined below.

The handler function returned by mk_shell simply passes the command
line to the Python eval function (for expressions) or the exec
statement (statements).  On eval and exec:

 http://docs.python.org/2/library/functions.html#eval 
 http://docs.python.org/2/reference/simple_stmts.html#exec
 http://stackoverflow.com/questions/2220699/whats-the-difference-between-eval-exec-and-compile-in-python
 http://lucumr.pocoo.org/2011/2/1/exec-in-python/

"""

import sys, traceback

main_globals = sys.modules['__main__'].__dict__

# pysh handles exit() as a special case 
# We do NOT want to exit from the underlying Python session, just from pysh.
pexit = False

def exit():
    'Call this function to exit from pysh shell, NOT underlying Python session'
    global pexit
    pexit = True

def mk_shell(globals=main_globals):
    """
    Returns a handler function with one argument, the command.
    Use mk_shell to make the handler function with globals dict baked in.
    Accept the default globals to use the same dict as the __main__ module.
    """

    def shell(command):
        """
        Pass command to Python eval or exec to execute
        This is a closure that includes the globals dictionary 
        """
        # exit() is a special case - do NOT exit from underlying Python session
        if command == 'exit()':
            exit()
            return
        try: # don't crash out of piety if exception, but print traceback
            try: # try eval, if it fails call exec
                # exec does not automatically print values,
                #  so use eval if we can
                result = eval(command, globals)
                # print out results just as in standard Python REPL
                if result == None:
                    pass
                elif isinstance(result,str):
                    print "'"+result+"'"
                else:
                    print result
                # statements (not exprs) like x = 42 crash eval
                #  with syntax error, so use exec for those
            except SyntaxError:
                exec command in globals
        except BaseException as e:
          traceback.print_exc() # looks just like unhandled exception

    return shell

# Test

def main():
    'Python REPL using home-made pysh shell'
    global pexit
    pexit = False # may have been set by True previous invocation
    pysh = mk_shell()
    print "pysh shell, type any Python statement, exit() to exit"
    while not pexit:
        command = raw_input('>> ')
        pysh(command)

if __name__ == '__main__':
    main()