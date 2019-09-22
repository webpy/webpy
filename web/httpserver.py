from __future__ import print_function

import os
import posixpath
import sys

from . import utils
from . import webapi as web

try:
    from io import BytesIO
except ImportError:
    from StringIO import BytesIO

try:
    from http.server import HTTPServer, SimpleHTTPRequestHandler, BaseHTTPRequestHandler
except ImportError:
    from SimpleHTTPServer import SimpleHTTPRequestHandler
    from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler

try:
    from urllib import parse as urlparse
    from urllib.parse import unquote
except ImportError:
    import urlparse
    from urllib import unquote

__all__ = ["runsimple"]


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

    import SocketServer
    import socket
    import errno
    import traceback

    class WSGIHandler(SimpleHTTPRequestHandler):
        def run_wsgi_app(self):
            protocol, host, path, parameters, query, fragment = urlparse.urlparse(
                "http://dummyhost%s" % self.path
            )

            # we only use path, query
            env = {
                "wsgi.version": (1, 0),
                "wsgi.url_scheme": "http",
                "wsgi.input": self.rfile,
                "wsgi.errors": sys.stderr,
                "wsgi.multithread": 1,
                "wsgi.multiprocess": 0,
                "wsgi.run_once": 0,
                "REQUEST_METHOD": self.command,
                "REQUEST_URI": self.path,
                "PATH_INFO": path,
                "QUERY_STRING": query,
                "CONTENT_TYPE": self.headers.get("Content-Type", ""),
                "CONTENT_LENGTH": self.headers.get("Content-Length", ""),
                "REMOTE_ADDR": self.client_address[0],
                "SERVER_NAME": self.server.server_address[0],
                "SERVER_PORT": str(self.server.server_address[1]),
                "SERVER_PROTOCOL": self.request_version,
            }

            for http_header, http_value in self.headers.items():
                env["HTTP_%s" % http_header.replace("-", "_").upper()] = http_value

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
                        if hasattr(result, "close"):
                            result.close()
                except socket.error as socket_err:
                    # Catch common network errors and suppress them
                    if socket_err.args[0] in (errno.ECONNABORTED, errno.EPIPE):
                        return
                except socket.timeout:
                    return
            except:
                print(traceback.format_exc(), file=web.debug)

            if not self.wsgi_sent_headers:
                # We must write out something!
                self.wsgi_write_data(" ")
            return

        do_POST = run_wsgi_app
        do_PUT = run_wsgi_app
        do_DELETE = run_wsgi_app

        def do_GET(self):
            if self.path.startswith("/static/"):
                SimpleHTTPRequestHandler.do_GET(self)
            else:
                self.run_wsgi_app()

        def wsgi_start_response(self, response_status, response_headers, exc_info=None):
            if self.wsgi_sent_headers:
                raise Exception("Headers already sent and start_response called again!")
            # Should really take a copy to avoid changes in the application....
            self.wsgi_headers = (response_status, response_headers)
            return self.wsgi_write_data

        def wsgi_write_data(self, data):
            if not self.wsgi_sent_headers:
                status, headers = self.wsgi_headers
                # Need to send header prior to data
                status_code = status[: status.find(" ")]
                status_msg = status[status.find(" ") + 1 :]
                self.send_response(int(status_code), status_msg)
                for header, value in headers:
                    self.send_header(header, value)
                self.end_headers()
                self.wsgi_sent_headers = 1
            # Send the data
            self.wfile.write(data)

    class WSGIServer(SocketServer.ThreadingMixIn, HTTPServer):
        def __init__(self, func, server_address):
            HTTPServer.HTTPServer.__init__(self, server_address, WSGIHandler)
            self.app = func
            self.serverShuttingDown = 0

    print("http://%s:%d/" % server_address)
    WSGIServer(func, server_address).serve_forever()


# The WSGIServer instance.
# Made global so that it can be stopped in embedded mode.
server = None


def runsimple(func, server_address=("0.0.0.0", 8080)):
    """
    Runs [CherryPy][cp] WSGI server hosting WSGI app `func`.
    The directory `static/` is hosted statically.

    [cp]: http://www.cherrypy.org
    """
    global server
    func = StaticMiddleware(func)
    func = LogMiddleware(func)

    server = WSGIServer(server_address, func)

    if "/" in server_address[0]:
        print("%s" % server_address)
    else:
        if server.ssl_adapter:
            print("https://%s:%d/" % server_address)
        else:
            print("http://%s:%d/" % server_address)

    try:
        server.start()
    except (KeyboardInterrupt, SystemExit):
        server.stop()
        server = None


def WSGIServer(server_address, wsgi_app):
    """Creates CherryPy WSGI server listening at `server_address` to serve `wsgi_app`.
    This function can be overwritten to customize the webserver or use a different webserver.
    """
    from cheroot import wsgi

    server = wsgi.Server(server_address, wsgi_app, server_name="localhost")
    server.nodelay = not sys.platform.startswith(
        "java"
    )  # TCP_NODELAY isn't supported on the JVM
    return server


class StaticApp(SimpleHTTPRequestHandler):
    """WSGI application for serving static files."""

    def __init__(self, environ, start_response):
        self.headers = []
        self.environ = environ
        self.start_response = start_response
        self.directory = os.getcwd()

    def send_response(self, status, msg=""):
        # the int(status) call is needed because in Py3 status is an enum.IntEnum and we need the integer behind
        self.status = str(int(status)) + " " + msg

    def send_header(self, name, value):
        self.headers.append((name, value))

    def end_headers(self):
        pass

    def log_message(*a):
        pass

    def __iter__(self):
        environ = self.environ

        self.path = environ.get("PATH_INFO", "")
        self.client_address = (
            environ.get("REMOTE_ADDR", "-"),
            environ.get("REMOTE_PORT", "-"),
        )
        self.command = environ.get("REQUEST_METHOD", "-")

        self.wfile = BytesIO()  # for capturing error

        try:
            path = self.translate_path(self.path)
            etag = '"%s"' % os.path.getmtime(path)
            client_etag = environ.get("HTTP_IF_NONE_MATCH")
            self.send_header("ETag", etag)
            if etag == client_etag:
                self.send_response(304, "Not Modified")
                self.start_response(self.status, self.headers)
                raise StopIteration()
        except OSError:
            pass  # Probably a 404

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


class StaticMiddleware:
    """WSGI middleware for serving static files."""

    def __init__(self, app, prefix="/static/"):
        self.app = app
        self.prefix = prefix

    def __call__(self, environ, start_response):
        path = environ.get("PATH_INFO", "")
        path = self.normpath(path)

        if path.startswith(self.prefix):
            return StaticApp(environ, start_response)
        else:
            return self.app(environ, start_response)

    def normpath(self, path):
        path2 = posixpath.normpath(unquote(path))
        if path.endswith("/"):
            path2 += "/"
        return path2


class LogMiddleware:
    """WSGI middleware for logging the status."""

    def __init__(self, app):
        self.app = app
        self.format = '%s - - [%s] "%s %s %s" - %s'

        f = BytesIO()

        class FakeSocket:
            def makefile(self, *a):
                return f

        # take log_date_time_string method from BaseHTTPRequestHandler
        self.log_date_time_string = BaseHTTPRequestHandler(
            FakeSocket(), None, None
        ).log_date_time_string

    def __call__(self, environ, start_response):
        def xstart_response(status, response_headers, *args):
            out = start_response(status, response_headers, *args)
            self.log(status, environ)
            return out

        return self.app(environ, xstart_response)

    def log(self, status, environ):
        outfile = environ.get("wsgi.errors", web.debug)
        req = environ.get("PATH_INFO", "_")
        protocol = environ.get("ACTUAL_SERVER_PROTOCOL", "-")
        method = environ.get("REQUEST_METHOD", "-")
        host = "%s:%s" % (
            environ.get("REMOTE_ADDR", "-"),
            environ.get("REMOTE_PORT", "-"),
        )

        time = self.log_date_time_string()

        msg = self.format % (host, time, protocol, method, req, status)
        print(utils.safestr(msg), file=outfile)
