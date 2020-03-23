"""Utilities for make the code run both on Python2 and Python3.
"""

# Dictionary iteration
iterkeys = lambda d: iter(d.keys())
itervalues = lambda d: iter(d.values())
iteritems = lambda d: iter(d.items())

is_iter = lambda x: x and hasattr(x, "__next__")
