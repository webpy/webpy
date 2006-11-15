"""
Web API (wrapper around WSGI)
(from web.py)
"""

__all__ = [
    "config",
    "badrequest", "notfound", "gone", "internalerror",
    "header", "output", "flush", "debug",
    "input", "data",
    "setcookie", "cookies",
    "ctx", 
    "loadhooks", "load", "unloadhooks", "unload", "_loadhooks",
    "wsgifunc"
]

import sys, os, cgi, threading, Cookie, pprint, traceback
try: import itertools
except ImportError: pass
from utils import storage, storify, threadeddict, dictadd, intget, lstrips

config = storage()
config.__doc__ = """
A configuration object for various aspects of web.py.

`db_parameters`
   : A dictionary containing the parameters to be passed to `connect`
     when `load()` is called.
`db_printing`
   : Set to `True` if you would like SQL queries and timings to be
     printed to the debug output.

"""

def badrequest():
    """Return a `400 Bad Request` error."""
    ctx.status = '400 Bad Request'
    header('Content-Type', 'text/html')
    return output('bad request')

def notfound():
    """Returns a `404 Not Found` error."""
    ctx.status = '404 Not Found'
    header('Content-Type', 'text/html')
    return output('not found')

def gone():
    """Returns a `410 Gone` error."""
    ctx.status = '410 Gone'
    header('Content-Type', 'text/html')
    return output("gone")

def internalerror():
    """Returns a `500 Internal Server` error."""
    ctx.status = "500 Internal Server Error"
    ctx.headers = [('Content-Type', 'text/html')]
    ctx.output = "internal server error"

def header(hdr, value, unique=False):
    """
    Adds the header `hdr: value` with the response.
    
    If `unique` is True and a header with that name already exists,
    it doesn't add a new one. If `unique` is None and a header with
    that name already exists, it replaces it with this one.
    """
    if unique is True:
        for h, v in ctx.headers:
            if h == hdr: return
    elif unique is False:
        ctx.headers = [h for h in ctx.headers if h[0] != hdr]
    
    ctx.headers.append((hdr, value))

def output(string_):
    """Appends `string_` to the response."""
    if isinstance(string_, unicode): string_ = string_.encode('utf8')
    if ctx.get('flush'):
        ctx._write(string_)
    else:
        ctx.output += str(string_)

def flush():
    ctx.flush = True
    return flush

def input(*requireds, **defaults):
    """
    Returns a `storage` object with the GET and POST arguments. 
    See `storify` for how `requireds` and `defaults` work.
    """
    from cStringIO import StringIO
    def dictify(fs): return dict([(k, fs[k]) for k in fs.keys()])
    
    _method = defaults.pop('_method', 'both')
    
    e = ctx.env.copy()
    out = {}
    if _method.lower() in ['both', 'post']:
        a = {}
        if e['REQUEST_METHOD'] == 'POST':
            a = cgi.FieldStorage(fp = StringIO(data()), environ=e, 
              keep_blank_values=1)
            a = dictify(a)
        out = dictadd(out, a)

    if _method.lower() in ['both', 'get']:
        e['REQUEST_METHOD'] = 'GET'
        a = dictify(cgi.FieldStorage(environ=e, keep_blank_values=1))
        out = dictadd(out, a)
    
    try:
        return storify(out, *requireds, **defaults)
    except KeyError:
        badrequest()
        raise StopIteration

def data():
    """Returns the data sent with the request."""
    if 'data' not in ctx:
        cl = intget(ctx.env.get('CONTENT_LENGTH'), 0)
        ctx.data = ctx.env['wsgi.input'].read(cl)
    return ctx.data

def setcookie(name, value, expires="", domain=None):
    """Sets a cookie."""
    if expires < 0: 
        expires = -1000000000 
    kargs = {'expires': expires, 'path':'/'}
    if domain: 
        kargs['domain'] = domain
    # @@ should we limit cookies to a different path?
    cookie = Cookie.SimpleCookie()
    cookie[name] = value
    for key, val in kargs.iteritems(): 
        cookie[name][key] = val
    header('Set-Cookie', cookie.items()[0][1].OutputString())

def cookies(*requireds, **defaults):
    """
    Returns a `storage` object with all the cookies in it.
    See `storify` for how `requireds` and `defaults` work.
    """
    cookie = Cookie.SimpleCookie()
    cookie.load(ctx.env.get('HTTP_COOKIE', ''))
    try:
        return storify(cookie, *requireds, **defaults)
    except KeyError:
        badrequest()
        raise StopIteration

def debug(*args):
    """
    Prints a prettyprinted version of `args` to stderr.
    """
    try: 
        out = ctx.environ['wsgi.errors']
    except: 
        out = sys.stderr
    for arg in args:
        print >> out, pprint.pformat(arg)
    return ''

def _debugwrite(x):
    try: 
        out = ctx.environ['wsgi.errors']
    except: 
        out = sys.stderr
    out.write(x)
debug.write = _debugwrite

class _outputter:
    """Wraps `sys.stdout` so that print statements go into the response."""
    def __init__(self, file): self.file = file
    def write(self, string_): 
        if hasattr(ctx, 'output'): 
            return output(string_)
        else:
            self.file.write(string_)
    def __getattr__(self, attr): return getattr(self.file, attr)
    def __getitem__(self, item): return self.file[item]

def _capturedstdout():
    sysstd = sys.stdout
    while hasattr(sysstd, 'file'):
        if isinstance(sys.stdout, _outputter): return True
        sysstd = sysstd.file
    if isinstance(sys.stdout, _outputter): return True    
    return False

if not _capturedstdout():
    sys.stdout = _outputter(sys.stdout)

_context = {threading.currentThread(): storage()}
ctx = context = threadeddict(_context)

ctx.__doc__ = """
A `storage` object containing various information about the request:
  
`environ` (aka `env`)
   : A dictionary containing the standard WSGI environment variables.

`host`
   : The domain (`Host` header) requested by the user.

`home`
   : The base path for the application.

`ip`
   : The IP address of the requester.

`method`
   : The HTTP method used.

`path`
   : The path request.
   
`query`
   : If there are no query arguments, the empty string. Otherwise, a `?` followed
     by the query string.

`fullpath`
   : The full path requested, including query arguments (`== path + query`).

### Response Data

`status` (default: "200 OK")
   : The status code to be used in the response.

`headers`
   : A list of 2-tuples to be used in the response.

`output`
   : A string to be used as the response.
"""

loadhooks = {}
_loadhooks = {}

def load():
    """
    Loads a new context for the thread.
    
    You can ask for a function to be run at loadtime by 
    adding it to the dictionary `loadhooks`.
    """
    _context[threading.currentThread()] = storage()
    ctx.status = '200 OK'
    ctx.headers = []
    if config.get('db_parameters'):
        import db
        db.connect(**config.db_parameters)
    
    for x in loadhooks.values(): x()

def _load(env):
    load()
    ctx.output = ''
    ctx.environ = ctx.env = env
    ctx.host = env.get('HTTP_HOST')
    ctx.homedomain = 'http://' + env.get('HTTP_HOST', '[unknown]')
    ctx.homepath = os.environ.get('REAL_SCRIPT_NAME', env.get('SCRIPT_NAME', ''))
    ctx.home = ctx.homedomain + ctx.homepath
    ctx.ip = env.get('REMOTE_ADDR')
    ctx.method = env.get('REQUEST_METHOD')
    ctx.path = env.get('PATH_INFO')
    # http://trac.lighttpd.net/trac/ticket/406 requires:
    if env.get('SERVER_SOFTWARE', '').startswith('lighttpd/'):
        ctx.path = lstrips(env.get('REQUEST_URI').split('?')[0], 
                           os.environ.get('REAL_SCRIPT_NAME', env.get('SCRIPT_NAME', '')))

    if env.get('QUERY_STRING'):
        ctx.query = '?' + env.get('QUERY_STRING', '')
    else:
        ctx.query = ''
    
    ctx.fullpath = ctx.path + ctx.query
    for x in _loadhooks.values(): x()

unloadhooks = {}

def unload():
    """
    Unloads the context for the thread.
    
    You can ask for a function to be run at loadtime by
    adding it ot the dictionary `unloadhooks`.
    """
    for x in unloadhooks.values(): x()
    # ensures db cursors and such are GCed promptly
    del _context[threading.currentThread()]

def _unload():
    unload()

def wsgifunc(func, *middleware):
    """Returns a WSGI-compatible function from a webpy-function."""
    middleware = list(middleware)
    
    def wsgifunc(env, start_resp):
        _load(env)
        try:
            result = func()
        except StopIteration:
            result = None
        except:
            print >> debug, traceback.format_exc()
            result = internalerror()
        
        is_generator = result and hasattr(result, 'next')
        if is_generator:
            # wsgi requires the headers first
            # so we need to do an iteration
            # and save the result for later
            try:
                firstchunk = result.next()
            except StopIteration:
                firstchunk = ''

        status, headers, output = ctx.status, ctx.headers, ctx.output
        ctx._write = start_resp(status, headers)

        # and now, the fun:
        
        def cleanup():
            # we insert this little generator
            # at the end of our itertools.chain
            # so that it unloads the request
            # when everything else is done
            
            yield '' # force it to be a generator
            _unload()

        # result is the output of calling the webpy function
        #   it could be a generator...
        
        if is_generator:
            if firstchunk is flush:
                # oh, it's just our special flush mode
                # ctx._write is set up, so just continue execution
                try:
                    result.next()
                except StopIteration:
                    pass

                _unload()
                return []
            else:
                return itertools.chain([firstchunk], result, cleanup())
        
        #   ... but it's usually just None
        # 
        # output is the stuff in ctx.output
        #   it's usually a string...
        if isinstance(output, str): #@@ other stringlikes?
            _unload()
            return [output] 
        #   it could be a generator...
        elif hasattr(output, 'next'):
            return itertools.chain(output, cleanup())
        else:
            _unload()
            raise Exception, "Invalid ctx.output"
    
    for mw_func in middleware: 
        wsgifunc = mw_func(wsgifunc)
    
    return wsgifunc
