import unittest
import time
import threading
import sys
import web
import urllib

try:
    from urllib.parse import urlencode
except ImportError:
    from urllib import urlencode

from web.py3helpers import PY2


class RouteTest(unittest.TestCase):
    def testHandlerMethod(self):
        app = web.application()
        
        @app.route('/method')
        def handler_method():
            return 'Hello Method'
            
        response = app.request('/method')
        self.assertEquals(response.data, 'Hello Method')
    
    def testHandlerClass(self):
        app = web.application()
        
        @app.route('/class')
        class HandlerClass:
            def GET(self):
                return 'Hello Class'
            
        response = app.request('/class')
        self.assertEquals(response.data, 'Hello Class')
    
    def testParameters(self):
        app = web.application()
        
        @app.route('/hello/(.*)')
        class HandlerClass():
            def GET(self, name):
                return 'Hello ' + name
            
        response = app.request('/hello/WebPy')
        self.assertEquals(response.data, 'Hello WebPy')
