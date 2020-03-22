"""Utilities for make the code run both on Python2 and Python3.
"""

# urljoin
try:
    from urllib.parse import urljoin
except ImportError:
    from urlparse import urljoin  # noqa: F401

# Dictionary iteration
iterkeys = lambda d: iter(d.keys())
itervalues = lambda d: iter(d.values())
iteritems = lambda d: iter(d.items())

# string and text types
try:
    text_type = unicode
except NameError:
    text_type = str

is_iter = lambda x: x and hasattr(x, "__next__")

# imap
imap = map
