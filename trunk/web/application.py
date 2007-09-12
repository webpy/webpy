"""
Web application.
"""
import webapi as web
import webapi, wsgi, utils
from request import nomethod

import urllib

__all__ = ["application", "subdir_application", "subdomain_application", "auto_application"]

class application:
    """Application to delegate requests based on path.

        >>> urls = ("/hello", "hello")
        >>> app = application(urls)
        >>> class hello:
        ...     def GET(self): return "hello"
        >>>
        >>> app.request("/hello")
        "hello"
    """
    def __init__(self, mapping, fvars={}):
        self.mapping = mapping
        self.fvars = fvars

    def request(self, path='/', method='GET', host="0.0.0.0:8080"):
        path, query = urllib.splitquery(path)
        query = query or ""

        homepath = ""
        d = {
            'home': "http://" + host + homepath,
            'homedomain': "http://" + host,
            'homepath': homepath,
            'host': host,
            'ip': '127.0.0.1',
            'method': method,
            'path': path,
            'query': query,
            'output': '',
        }
        env = {
            'REQUEST_METHOD': method,
            'QUERY_STRING': query
        }
        web.ctx.environ = web.ctx.env = env
        web.ctx.update(d)
        return self.handle()

    def handle(self, autoreload=False):
        #TODO: take care of reloading
        fn, args = _match(self.mapping, web.ctx.path)
        return _delegate(fn, self.fvars, args)

    def run(self, *middleware):
        """
        Starts handling requests. If called in a CGI or FastCGI context, it will follow
        that protocol. If called from the command line, it will start an HTTP
        server on the port named in the first command line argument, or, if there
        is no argument, on port 8080.
        
        `middleware` is a list of WSGI middleware which is applied to the resulting WSGI
        function.
        """
        def handle():
            # web.py expects print
            result = self.handle()
            if result:
                print result
            
        return wsgi.runwsgi(webapi.wsgifunc(handle, *middleware))

class subdir_application(application):
    """Application to delegate requests based on directory.

        >>> urls = ("/hello", "hello")
        >>> app = application(urls)
        >>> class hello:
        ...     def GET(self): return "hello"
        >>>
        >>> mapping = ("/foo", app)
        >>> app2 = subdir_application(mapping)
        >>> app2.request("/foo/hello")
        "hello"
    """
    def handle(self, autoreload=False):
        #TODO: take care of reloading
        for dir, what in utils.group(self.mapping, 2):
            if web.ctx.path.startswith(dir + '/'):
                # change paths to make path relative to dir
                web.ctx.home += dir
                web.ctx.homepath += dir
                web.ctx.path = web.ctx.path[len(dir):]
                web.ctx.fullpath = web.ctx.fullpath[len(dir):]
                return _delegate(what, self.fvars)

        return web.notfound()
                
class subdomain_application(application):
    """Application to delegate requests based on the host.

        >>> urls = ("/hello", "hello")
        >>> app = application(urls)
        >>> class hello:
        ...     def GET(self): return "hello"
        >>>
        >>> mapping = ("hello.example.com", app)
        >>> app2 = subdomain_application(mapping)
        >>> app2.request("/hello", host="hello.example.com")
        "hello2"
    """
    def handle(self, autoreload=False):
        #TODO: take care of reloading
        host = web.ctx.host.split(':')[0] #strip port
        fn, args = _match(self.mapping, host)
        return _delegate(fn, self.fvars, args)

class auto_application(application):
    """Application similar to web.application but urls are constructed 
    automatiacally using metaclass.

        >>> app = auto_application()
        >>> class hello(app.page):
        ...     def GET(self): return "hello, world"
        ...
        >>> class foo(app.page):
        ...     path = '/foobar'
        ...     def GET(self): return "foo"
        >>>
        >>> app.request('/hello')
        "hello, world"
        >>> app.request('/foobar')
        "foo"
    """
    def __init__(self):
        self.urls = urls = []
        application.__init__(self, self.urls)

        class metapage(type):
            def __init__(klass, name, bases, attrs):
                type.__init__(klass, name, bases, attrs)
                mod, name = klass.__module__, klass.__name__
                path = getattr(klass, 'path', '/' + name)
                urls.append(path)
                urls.append(mod + '.' + name)

        class page:
            __metaclass__ = metapage

        # clear page from urls
        self.urls[:] = []
        self.page = page

def _delegate(f, fvars, args=[]):
    if f is None:
        return web.notfound()
    elif isinstance(f, application):
        return f.handle()
    elif hasattr(f, '__call__'):
        return f()
    elif isinstance(f, str):
        if '.' in f:
            x = f.split('.')
            mod, cls = '.'.join(x[:-1]), x[-1]
            mod = __import__(mod, globals(), locals(), [""])
            cls = getattr(mod, cls)
        else:
            cls = fvars[f]

        meth = web.ctx.method
        if meth == 'HEAD' and not hasattr(cls, meth):
            meth = 'GET'
        if not hasattr(cls, meth):
            return nomethod(cls)
        tocall = getattr(cls(), meth)
        return tocall(*args)
    else:
        return web.notfound()

def _match(mapping, value):
    for pat, what in utils.group(mapping, 2):
        rx = utils.re_compile('^' + pat + '$')
        result = rx.match(value)
        if result:
            return what, [x and urllib.unquote(x) for x in result.groups()]
    return None, None

if __name__ == "__main__":
    import doctest
    doctest.testmod()
