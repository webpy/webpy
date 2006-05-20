#!/usr/bin/env python
"""web.py: makes web apps (http://webpy.org)"""
__version__ = "0.2"
__revision__ = "$Rev: 62 $"
__author__ = "Aaron Swartz <me@aaronsw.com>"
__license__ = "public domain"
__contributors__ = "see http://webpy.org/changes"

from __future__ import generators

# todo:
#   - some sort of accounts system

from utils import *
from db import *
from net import *
from http import *
from wsgi import *
from webapi import *
from httpserver import *
from request import *

try:
    from cheetah import *
except ImportError:
    pass

def main():
    import doctest
    
    import utils, net, db, http, wsgi, webapi, request
    doctest.testmod(utils)
    doctest.testmod(db)
    doctest.testmod(net)
    doctest.testmod(http)
    doctest.testmod(wsgi)
    doctest.testmod(webapi)
    doctest.testmod(request)
    
    try:
        import cheetah
    except ImportError:
        doctest.testmod(cheetah)
    
    import sys
    urls = ('/web.py', 'source')
    class source:
        def GET(self):
            header('Content-Type', 'text/python')
            print open(sys.argv[0]).read()
    
    if listget(sys.argv, 1) != 'test':
        run(urls, locals())

if __name__ == "__main__": main()