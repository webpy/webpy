__all__ = ["runsimple"]

import sys, os
import webapi as web
import net

def runbasic(func, server_address=("0.0.0.0", 8080)):
    """
    Runs a simple HTTP server hosting WSGI app `func`. The directory `static/` 
    is hosted statically.

    Based on [WsgiServer][ws] from [Colin Stewart][cs].
    
  [ws]: http://www.owlfish.com/software/wsgiutils/documentation/wsgi-server-api.html
  [cs]: http://www.owlfish.com/
    """
    # Copyright (c) 2004 Colin Stewart (http://www.owlfish.com/)
    # Modified somewhat for simplicity
    # Used under the modified BSD license:
    # http://www.xfree86.org/3.3.6/COPYRIGHT2.html#5

    import SimpleHTTPServer, SocketServer, BaseHTTPServer, urlparse
    import socket, errno
    import traceback

    class WSGIHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):
        def run_wsgi_app(self):
            protocol, host, path, parameters, query, fragment = \
                urlparse.urlparse('http://dummyhost%s' % self.path)

            # we only use path, query
            env = {'wsgi.version': (1, 0)
                   ,'wsgi.url_scheme': 'http'
                   ,'wsgi.input': self.rfile
                   ,'wsgi.errors': sys.stderr
                   ,'wsgi.multithread': 1
                   ,'wsgi.multiprocess': 0
                   ,'wsgi.run_once': 0
                   ,'REQUEST_METHOD': self.command
                   ,'REQUEST_URI': self.path
                   ,'PATH_INFO': path
                   ,'QUERY_STRING': query
                   ,'CONTENT_TYPE': self.headers.get('Content-Type', '')
                   ,'CONTENT_LENGTH': self.headers.get('Content-Length', '')
                   ,'REMOTE_ADDR': self.client_address[0]
                   ,'SERVER_NAME': self.server.server_address[0]
                   ,'SERVER_PORT': str(self.server.server_address[1])
                   ,'SERVER_PROTOCOL': self.request_version
                   }

            for http_header, http_value in self.headers.items():
                env ['HTTP_%s' % http_header.replace('-', '_').upper()] = \
                    http_value

            # Setup the state
            self.wsgi_sent_headers = 0
            self.wsgi_headers = []

            try:
                # We have there environment, now invoke the application
                result = self.server.app(env, self.wsgi_start_response)
                try:
                    try:
                        for data in result:
                            if data: 
                                self.wsgi_write_data(data)
                    finally:
                        if hasattr(result, 'close'): 
                            result.close()
                except socket.error, socket_err:
                    # Catch common network errors and suppress them
                    if (socket_err.args[0] in \
                       (errno.ECONNABORTED, errno.EPIPE)): 
                        return
                except socket.timeout, socket_timeout: 
                    return
            except:
                print >> web.debug, traceback.format_exc(),

            if (not self.wsgi_sent_headers):
                # We must write out something!
                self.wsgi_write_data(" ")
            return

        do_POST = run_wsgi_app
        do_PUT = run_wsgi_app
        do_DELETE = run_wsgi_app

        def do_GET(self):
            if self.path.startswith('/static/'):
                SimpleHTTPServer.SimpleHTTPRequestHandler.do_GET(self)
            else:
                self.run_wsgi_app()

        def wsgi_start_response(self, response_status, response_headers, 
                              exc_info=None):
            if (self.wsgi_sent_headers):
                raise Exception \
                      ("Headers already sent and start_response called again!")
            # Should really take a copy to avoid changes in the application....
            self.wsgi_headers = (response_status, response_headers)
            return self.wsgi_write_data

        def wsgi_write_data(self, data):
            if (not self.wsgi_sent_headers):
                status, headers = self.wsgi_headers
                # Need to send header prior to data
                status_code = status[:status.find(' ')]
                status_msg = status[status.find(' ') + 1:]
                self.send_response(int(status_code), status_msg)
                for header, value in headers:
                    self.send_header(header, value)
                self.end_headers()
                self.wsgi_sent_headers = 1
            # Send the data
            self.wfile.write(data)

    class WSGIServer(SocketServer.ThreadingMixIn, BaseHTTPServer.HTTPServer):
        def __init__(self, func, server_address):
            BaseHTTPServer.HTTPServer.__init__(self, 
                                               server_address, 
                                               WSGIHandler)
            self.app = func
            self.serverShuttingDown = 0

    print "http://%s:%d/" % server_address
    WSGIServer(func, server_address).serve_forever()

def runsimple(func, server_address=("0.0.0.0", 8080)):
    """
    Runs [CherryPy][cp] WSGI server hosting WSGI app `func`. 
    The directory `static/` is hosted statically.

    [cp]: http://www.cherrypy.org
    """
    from wsgiserver import CherryPyWSGIServer
    from SimpleHTTPServer import SimpleHTTPRequestHandler
    from BaseHTTPServer import BaseHTTPRequestHandler

    class StaticApp(SimpleHTTPRequestHandler):
        """WSGI application for serving static files."""
        def __init__(self, environ, start_response):
            self.headers = []
            self.environ = environ
            self.start_response = start_response

        def send_response(self, status, msg=""):
            self.status = str(status) + " " + msg

        def send_header(self, name, value):
            self.headers.append((name, value))

        def end_headers(self):
            pass

        def log_message(*a): pass

        def __iter__(self):
            environ = self.environ

            self.path = environ.get('PATH_INFO', '')
            self.client_address = environ.get('REMOTE_ADDR','-'), \
                                  environ.get('REMOTE_PORT','-')
            self.command = environ.get('REQUEST_METHOD', '-')

            from cStringIO import StringIO
            self.wfile = StringIO() # for capturing error

            f = self.send_head()
            self.start_response(self.status, self.headers)

            if f:
                block_size = 16 * 1024
                while True:
                    buf = f.read(block_size)
                    if not buf:
                        break
                    yield buf
                f.close()
            else:
                value = self.wfile.getvalue()
                yield value
                    
    class WSGIWrapper(BaseHTTPRequestHandler):
        """WSGI wrapper for logging the status and serving static files."""
        def __init__(self, app):
            self.app = app
            self.format = '%s - - [%s] "%s %s %s" - %s'

        def __call__(self, environ, start_response):
            def xstart_response(status, response_headers, *args):
                write = start_response(status, response_headers, *args)
                self.log(status, environ)
                return write

            path = environ.get('PATH_INFO', '')
            if path.startswith('/static/'):
                return StaticApp(environ, xstart_response)
            else:
                return self.app(environ, xstart_response)

        def log(self, status, environ):
            outfile = environ.get('wsgi.errors', web.debug)
            req = environ.get('PATH_INFO', '_')
            protocol = environ.get('ACTUAL_SERVER_PROTOCOL', '-')
            method = environ.get('REQUEST_METHOD', '-')
            host = "%s:%s" % (environ.get('REMOTE_ADDR','-'), 
                              environ.get('REMOTE_PORT','-'))

            #@@ It is really bad to extend from 
            #@@ BaseHTTPRequestHandler just for this method
            time = self.log_date_time_string()

            print >> outfile, self.format % (host, time, protocol, 
                                             method, req, status)
            
    func = WSGIWrapper(func)
    server = CherryPyWSGIServer(server_address, func, server_name="localhost")

    print "http://%s:%d/" % server_address
    try:
        server.start()
    except KeyboardInterrupt:
        server.stop()
