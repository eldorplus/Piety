# test_ed_pattern.sh - Same fcns as test_ed_pattern.py but commands not API
#
python -c "from ed import *; ed()" <<'END'
B ed.py.txt
1l
/text/
e
/text/
e
/text/
e
/text/
e
?text?
e
?text?
e
?text?
e
?text?
e
//
e
//
e
//
e
//
e
??
e
??
e
??
e
??
e
q
END