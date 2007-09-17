"""
Web application.
"""
import webapi as web
import webapi, wsgi, utils
from request import nomethod

import urllib

__all__ = [
    "application", "auto_application",
    "subdir_application", "subdomain_application", 
    "combine_applications",
    "loadhook", "unloadhook"
]

class NotFound(Exception): 
    """Exception raised when an application can't handle a request."""
    pass

class application:
    """Application to delegate requests based on path.

        >>> urls = ("/hello", "hello")
        >>> app = application(urls, globals())
        >>> class hello:
        ...     def GET(self): return "hello"
        >>>
        >>> app.request("/hello")
        "hello"
    """
    def __init__(self, mapping=(), fvars={}):
        self.mapping = mapping
        self.fvars = fvars
        self.processors = []
        
    def add_mapping(self, pattern, classname):
        self.mapping += (pattern, classname)
        
    def add_processor(self, processor):
        """Adds a processor to the application. 
        
            >>> urls = ("/(.*)", "echo")
            >>> app = web.application(urls, globals())
            >>> class echo:
            ...     def GET(self, name): return name
            ...
            >>>
            >>> def hello(handler): return "hello, " +  handler()
            >>> app.add_processor(hello)
            >>> app.request("/web.py")
            "hello, web.py"
        """
        self.processors.append(processor)

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
        fn, args = self._match(self.mapping, web.ctx.path)
        return self._delegate(fn, self.fvars, args)
        
    def xhandle(self):
        def process(processors):
            if processors:
                p, processors = processors[0], processors[1:]
                return p(lambda: process(processors))
            else:
                return self.handle()
                
        # processors must be applied in the resvere order.
        return process(self.processors[::-1])
        
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
            try:
                result = self.xhandle()
                # web.py expects print
                if result:
                    print result
            except NotFound:
                web.notfound()
            
        return wsgi.runwsgi(webapi.wsgifunc(handle, *middleware))

    def _delegate(self, f, fvars, args=[]):
        if f is None:
            raise NotFound
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

    def _match(self, mapping, value):
        for pat, what in utils.group(mapping, 2):
            rx = utils.re_compile('^' + pat + '$')
            result = rx.match(value)
            if result:
                return what, [x and urllib.unquote(x) for x in result.groups()]
        return None, None

class auto_application(application):
    """Application similar to `application` but urls are constructed 
    automatiacally using metaclass.

        >>> app = auto_application()
        >>> class hello(app.page):
        ...     def GET(self): return "hello, world"
        ...
        >>> class foo(app.page):
        ...     path = '/foo/.*'
        ...     def GET(self): return "foo"
        >>>
        >>> app.request('/hello')
        "hello, world"
        >>> app.request('/foo/bar')
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

                # path can be specified as None to ignore that class
                # typically required to create a abstract base class.
                if path is not None:
                    urls.append(path)
                    urls.append(mod + '.' + name)

        class page:
            path = None
            __metaclass__ = metapage

        self.page = page

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
                return self._delegate(what, self.fvars)

        raise NotFound
                
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
        fn, args = self._match(self.mapping, host)
        return self._delegate(fn, self.fvars, args)

class combine_applications(application):
    """Combines a list of applications into single application.
    
        >>> app1 = auto_application()
        >>> class foo(app1.page):
        ...     def GET(self): return "foo"
        ...
        >>> app2 = auto_application()
        >>> class bar(app2.page):
        ...     def GET(self): return "bar"
        ...
        >>> app = combine_applications(app1, app2)
        >>> app.request('/foo')
        "foo"
        >>> app.request('/bar')
        "bar"
        >>> app.request("/hello")
        Traceback (most recent call last):
            ...
        NotFound
    """
    def __init__(self, *apps):
        self.apps = apps
        application.__init__(self)
        
    def handle(self, autoreload=False):
        for a in self.apps:
            try:
                return a.handle()
            except NotFound:
                pass
        raise NotFound
        
def loadhook(h):
    """Converts a load hook into an application processor.
    
        >>> app = web.auto_application()
        >>> def f(): "something done before handling request"
        ...
        >>> app.add_processor(loadhook(f))
    """
    def processor(handler):
        h()
        return handler()
        
    return processor
    
def unloadhook(h):
    """Converts an unload hook into an application processor.
    
        >>> app = web.auto_application()
        >>> def f(): "something done after handling request"
        ...
        >>> app.add_processor(unloadhook(f))    
    """
    def processor(handler):
        try:
            return handler()
        finally:
            h()
            
    return processor

if __name__ == "__main__":
    import doctest
    doctest.testmod()
