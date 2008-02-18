"""
Web API (wrapper around WSGI)
(from web.py)
"""

__all__ = [
    "config",
    "header", "debug",
    "input", "data",
    "setcookie", "cookies",
    "ctx", 
    "HTTPError", 
    "BadRequest", "NotFound", "Gone", 
    "badrequest", "notfound", "gone", "internalerror",
    "Redirect", "Found", "SeeOther", "TempRedirect",
    "redirect", "found", "seeother", "tempredirect", 
    "NoMethod", "nomethod",
]

import sys, cgi, Cookie, pprint, urlparse
from utils import storage, storify, threadeddict, dictadd, intget, utf8

config = storage()
config.__doc__ = """
A configuration object for various aspects of web.py.

`db_parameters`
   : A dictionary containing the parameters to be passed to `connect`
     when `load()` is called.
`db_printing`
   : Set to `True` if you would like SQL queries and timings to be
     printed to the debug output.
`session_parameters`
   : A dictionary containing session parameters
    cookie_name, cookie_domain, timeout, 
    ignore_change_ip, ignore_expiry, expired_message
"""

class HTTPError(Exception):
    def __init__(self, status, headers, data=""):
        ctx.status = status
        for k, v in headers.items():
            header(k, v)
        self.data = data
        Exception.__init__(self, status)

class BadRequest(HTTPError):
    """`400 Bad Request` error."""
    def __init__(self):
        status = "400 Bad Request"
        headers = {'Content-Type': 'text/html'}
        data = 'bad request'
        HTTPError.__init__(self, status, headers, data)

badrequest = BadRequest

class NotFound(HTTPError):
    """`404 Not Found` error."""
    def __init__(self):
        status = '404 Not Found'
        headers = {'Content-Type': 'text/html'}
        data = 'not found'
        HTTPError.__init__(self, status, headers, data)

notfound = NotFound

class Gone(HTTPError):
    """`410 Gone` error."""
    def __init__(self):
        status = '410 Gone'
        headers = {'Content-Type': 'text/html'}
        data = 'gone'
        HTTPError.__init__(self, status, headers, data)

gone = Gone

class Redirect(HTTPError):
    """A `301 Moved Permanently` redirect."""
    def __init__(self, url, status='301 Moved Permanently'):
        """
        Returns a `status` redirect to the new URL. 
        `url` is joined with the base URL so that things like 
        `redirect("about") will work properly.
        """
        newloc = urlparse.urljoin(ctx.path, url)

        if newloc.startswith('/'):
            newloc = ctx.home + newloc

        headers = {
            'Content-Type': 'text/html',
            'Location': newloc
        }
        HTTPError.__init__(self, status, headers, "")

redirect = Redirect

class Found(Redirect):
    """A `302 Found` redirect."""
    def __init__(self, url):
        Redirect.__init__(self, url, '302 Found')

found = Found

class SeeOther(Redirect):
    """A `303 See Other` redirect."""
    def __init__(self, url):
        Redirect.__init__(self, url, '303 See Other')
    
seeother = SeeOther

class TempRedirect(Redirect):
    """A `307 Temporary Redirect` redirect."""
    def __init__(self, url):
        Redirect.__init__(self, url, '307 Temporary Redirect')

tempredirect = TempRedirect

class NoMethod(HTTPError):
    """A `405 Method Not Allowed` error."""
    def __init__(self, cls=None):
        status = '405 Method Not Allowed'
        headers = {}
        headers['Content-Type'] = 'text/html'
        
        methods = ['GET', 'HEAD', 'POST', 'PUT', 'DELETE']
        if cls:
            methods = [method for method in methods if hasattr(cls, method)]

        headers['Allow'] = ', '.join(methods)
        data = None
        HTTPError.__init__(self, status, headers, data)
        
nomethod = NoMethod

def internalerror():
    """Returns a `500 Internal Server` error."""
    ctx.status = "500 Internal Server Error"
    ctx.headers = [('Content-Type', 'text/html')]
    return "internal server error"

def header(hdr, value, unique=False):
    """
    Adds the header `hdr: value` with the response.
    
    If `unique` is True and a header with that name already exists,
    it doesn't add a new one. 
    """
    hdr, value = utf8(hdr), utf8(value)
    # protection against HTTP response splitting attack
    if '\n' in hdr or '\r' in hdr or '\n' in value or '\r' in value:
        raise ValueError, 'invalid characters in header'
        
    if unique is True:
        for h, v in ctx.headers:
            if h.lower() == hdr.lower(): return
    
    ctx.headers.append((hdr, value))

def input(*requireds, **defaults):
    """
    Returns a `storage` object with the GET and POST arguments. 
    See `storify` for how `requireds` and `defaults` work.
    """
    from cStringIO import StringIO
    def dictify(fs): return dict([(k, fs[k]) for k in fs.keys()])
    
    _method = defaults.pop('_method', 'both')
    
    e = ctx.env.copy()
    a = b = {}
    
    if _method.lower() in ['both', 'post']:
        if e['REQUEST_METHOD'] == 'POST':
            a = cgi.FieldStorage(fp = StringIO(data()), environ=e, 
              keep_blank_values=1)
            a = dictify(a)

    if _method.lower() in ['both', 'get']:
        e['REQUEST_METHOD'] = 'GET'
        b = dictify(cgi.FieldStorage(environ=e, keep_blank_values=1))

    out = dictadd(b, a)
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

def setcookie(name, value, expires="", domain=None, secure=False):
    """Sets a cookie."""
    if expires < 0: 
        expires = -1000000000 
    kargs = {'expires': expires, 'path':'/'}
    if domain: 
        kargs['domain'] = domain
    if secure:
        kargs['secure'] = secure
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

ctx = context = threadeddict()

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
