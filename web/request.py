"""
Request Delegation
(from web.py)
"""

__all__ = ["handle", "nomethod", "autodelegate", "webpyfunc", "run"]

import sys, re, types, os.path, urllib

import http, wsgi, utils, webapi
import webapi as web

def handle(mapping, fvars=None):
    """
    Call the appropriate function based on the url to function mapping in `mapping`.
    If no module for the function is specified, look up the function in `fvars`. If
    `fvars` is empty, using the caller's context.

    `mapping` should be a tuple of paired regular expressions with function name
    substitutions. `handle` will import modules as necessary.
    """
    for url, ofno in utils.group(mapping, 2):
        if isinstance(ofno, tuple): 
            ofn, fna = ofno[0], list(ofno[1:])
        else: 
            ofn, fna = ofno, []
        fn, result = utils.re_subm('^' + url + '$', ofn, web.ctx.path)
        if result: # it's a match
            if fn.split(' ', 1)[0] == "redirect":
                url = fn.split(' ', 1)[1]
                if web.ctx.method == "GET":
                    x = web.ctx.env.get('QUERY_STRING', '')
                    if x: 
                        url += '?' + x
                return http.redirect(url)
            elif '.' in fn: 
                x = fn.split('.')
                mod, cls = '.'.join(x[:-1]), x[-1]
                mod = __import__(mod, globals(), locals(), [""])
                cls = getattr(mod, cls)
            else:
                cls = fn
                mod = fvars
                if isinstance(mod, types.ModuleType): 
                    mod = vars(mod)
                try: 
                    cls = mod[cls]
                except KeyError: 
                    return web.notfound()
            
            meth = web.ctx.method
            if meth == "HEAD":
                if not hasattr(cls, meth): 
                    meth = "GET"
            if not hasattr(cls, meth): 
                return nomethod(cls)
            tocall = getattr(cls(), meth)
            args = list(result.groups())
            for d in re.findall(r'\\(\d+)', ofn):
                args.pop(int(d) - 1)
            return tocall(*([x and urllib.unquote(x) for x in args] + fna))

    return web.notfound()

def nomethod(cls):
    """Returns a `405 Method Not Allowed` error for `cls`."""
    web.ctx.status = '405 Method Not Allowed'
    web.header('Content-Type', 'text/html')
    web.header('Allow', \
           ', '.join([method for method in \
                     ['GET', 'HEAD', 'POST', 'PUT', 'DELETE'] \
                        if hasattr(cls, method)]))

    # commented out for the same reason redirect is
    # return output('method not allowed')

def autodelegate(prefix=''):
    """
    Returns a method that takes one argument and calls the method named prefix+arg,
    calling `notfound()` if there isn't one. Example:

        urls = ('/prefs/(.*)', 'prefs')

        class prefs:
            GET = autodelegate('GET_')
            def GET_password(self): pass
            def GET_privacy(self): pass

    `GET_password` would get called for `/prefs/password` while `GET_privacy` for 
    `GET_privacy` gets called for `/prefs/privacy`.
    
    If a user visits `/prefs/password/change` then `GET_password(self, '/change')`
    is called.
    """
    def internal(self, arg):
        if '/' in arg:
            first, rest = arg.split('/', 1)
            func = prefix + first
            args = ['/' + rest]
        else:
            func = prefix + arg
            args = []
        
        if hasattr(self, func):
            try:
                return getattr(self, func)(*args)
            except TypeError:
                return web.notfound()
        else:
            return web.notfound()
    return internal

def webpyfunc(inp, fvars, autoreload=False):
    """If `inp` is a url mapping, returns a function that calls handle."""
    if not hasattr(inp, '__call__'):
        if autoreload:
            def modname():
                """find name of the module name from fvars."""
                file, name = fvars['__file__'], fvars['__name__']
                if name == '__main__':
                    # Since the __main__ module can't be reloaded, the module has 
                    # to be imported using its file name.
                    name = os.path.splitext(os.path.basename(file))[0]
                return name
    
            mod = __import__(modname(), None, None, [""])
            #@@probably should replace this with some inspect magic
            name = utils.dictfind(fvars, inp)
            func = lambda: handle(getattr(mod, name), mod)
        else:
            func = lambda: handle(inp, fvars)
    else:
        func = inp
    return func

def run(inp, fvars, *middleware):
    """
    Starts handling requests. If called in a CGI or FastCGI context, it will follow
    that protocol. If called from the command line, it will start an HTTP
    server on the port named in the first command line argument, or, if there
    is no argument, on port 8080.

    `input` is a callable, then it's called with no arguments.
    Otherwise, it's a `mapping` object to be passed to `handle(...)`.

    **Caveat:** So that `reloader` will work correctly, input has to be a variable,
    it can't be a tuple passed in directly.

    `middleware` is a list of WSGI middleware which is applied to the resulting WSGI
    function.
    """
    autoreload = http.reloader in middleware
    return wsgi.runwsgi(webapi.wsgifunc(webpyfunc(inp, fvars, autoreload), *middleware))
