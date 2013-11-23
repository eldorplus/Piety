"""
test_ed_urc.py - Test ed.py functions (b)u(ffer), r(ead), c(hange)

Run this script from the directory above Piety, it uses relative paths:

 python -i Piety/samples/test_ur.py

These tests don't write any files, so you needn't delete anything afterward.

"""

from ed import *
from test_cmd import test_cmd

test_cmd(u, 'create buffer', 'new.txt')

print "> n() # print buffers"
n()
print

test_cmd(r, 'read file into empty buffer', 'Piety/samples/test_cmd.py')

print "> l(9) # advance to line 9 and print it"
l(9)
print

test_cmd(r, 'read file into middle of buffer', 'Piety/samples/README.md')

print "> p() # print the current line"
p()
print

test_cmd(c, 'change the current line', '### This is the changed line ###')

test_cmd(c, 'replace all the remaining lines', 
         o(),S(), '### This line replaces all that followed ###')
