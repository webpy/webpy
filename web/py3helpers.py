"""Utilities for make the code run both on Python2 and Python3.
"""
import sys

PY2 = sys.version_info[0] == 2

# urljoin
try:
    from urllib.parse import urljoin
except ImportError:
    from urlparse import urljoin  # noqa: F401

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
try:
    text_type = unicode
    string_types = (str, unicode)
    numeric_types = (int, long)
except NameError:
    text_type = str
    string_types = (str,)
    numeric_types = (int,)

if PY2:
    is_iter = lambda x: x and hasattr(x, "next")
else:
    is_iter = lambda x: x and hasattr(x, "__next__")

# imap
if PY2:
    from itertools import imap
else:
    imap = map
