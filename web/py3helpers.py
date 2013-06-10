"""Utilities for make the code run both on Python2 and Python3.
"""
import sys

PY2 = sys.version_info[0] == 2

# urljoin
if PY2:
    from urlparse import urljoin
else:
    from urllib.parse import urljoin

# Dictionary iteration
if PY2:
    iterkeys = lambda d: d.iterkeys()
    itervalues = lambda d: d.itervalues()
    iteritems = lambda d: d.iteritems()
else:
    iterkeys = lambda d: iter(d.keys())
    itervalues = lambda d: iter(d.values())
    iteritems = lambda d: iter(d.items())

# string and text types
if PY2:
    text_type = unicode
    string_types = (str, unicode)
else:
    text_type = str
    string_types = (str,)

# imap
if PY2:
	from itertools import imap
else:
	imap = map
