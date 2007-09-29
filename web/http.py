"""
HTTP Utilities
(from web.py)
"""

__all__ = [
  "expires", "lastmodified", 
  "prefixurl", "modified", 
  "write",
  "changequery", "url",
  "background", "backgrounder",
  "Reloader", "reloader", "profiler",
]

import sys, os, threading, urllib, urlparse
try: import datetime
except ImportError: pass
import net, utils, webapi as web

def prefixurl(base=''):
    """
    Sorry, this function is really difficult to explain.
    Maybe some other time.
    """
    url = web.ctx.path.lstrip('/')
    for i in xrange(url.count('/')): 
        base += '../'
    if not base: 
        base = './'
    return base

def expires(delta):
    """
    Outputs an `Expires` header for `delta` from now. 
    `delta` is a `timedelta` object or a number of seconds.
    """
    if isinstance(delta, (int, long)):
        delta = datetime.timedelta(seconds=delta)
    date_obj = datetime.datetime.utcnow() + delta
    web.header('Expires', net.httpdate(date_obj))

def lastmodified(date_obj):
    """Outputs a `Last-Modified` header for `datetime`."""
    web.header('Last-Modified', net.httpdate(date_obj))

def modified(date=None, etag=None):
    n = web.ctx.env.get('HTTP_IF_NONE_MATCH')
    m = net.parsehttpdate(web.ctx.env.get('HTTP_IF_MODIFIED_SINCE', '').split(';')[0])
    validate = False
    if etag:
        raise NotImplementedError, "no etag support yet"
        # should really be a warning
    if date and m:
        # we subtract a second because 
        # HTTP dates don't have sub-second precision
        if date-datetime.timedelta(seconds=1) <= m:
            validate = True

    if validate: web.ctx.status = '304 Not Modified'
    return not validate

def write(cgi_response):
    """
    Converts a standard CGI-style string response into `header` and 
    `output` calls.
    """
    cgi_response = str(cgi_response)
    cgi_response.replace('\r\n', '\n')
    head, body = cgi_response.split('\n\n', 1)
    lines = head.split('\n')

    for line in lines:
        if line.isspace(): 
            continue
        hdr, value = line.split(":", 1)
        value = value.strip()
        if hdr.lower() == "status": 
            web.ctx.status = value
        else: 
            web.header(hdr, value)

    web.output(body)

def urlencode(query):
    """
    Same as urllib.urlencode, but supports unicode strings.
    
        >>> urlencode({'text':'foo bar'})
        'text=foo+bar'
    """
    query = dict([(k, utils.utf8(v)) for k, v in query.items()])
    return urllib.urlencode(query)

def changequery(query=None, **kw):
    """
    Imagine you're at `/foo?a=1&b=2`. Then `changequery(a=3)` will return
    `/foo?a=3&b=2` -- the same URL but with the arguments you requested
    changed.
    """
    if query is None:
        query = web.input(_method='get')
    for k, v in kw.iteritems():
        if v is None:
            query.pop(k, None)
        else:
            query[k] = v
    out = web.ctx.path
    if query:
        out += '?' + urlencode(query)
    return out

def url(path=None, **kw):
    """
    Makes url by concatinating web.ctx.homepath and path and the 
    query string created using the arguments.
    """
    if path is None:
        path = web.ctx.path
    if path.startswith("/"):
        out = web.ctx.homepath + path
    else:
        out = path

    if kw:
        out += '?' + urlencode(kw)
    
    return out

def background(func):
    """A function decorator to run a long-running function as a background thread."""
    def internal(*a, **kw):
        web.data() # cache it

        tmpctx = web._context[threading.currentThread()]
        web._context[threading.currentThread()] = utils.storage(web.ctx.copy())

        def newfunc():
            web._context[threading.currentThread()] = tmpctx
            func(*a, **kw)
            myctx = web._context[threading.currentThread()]
            for k in myctx.keys():
                if k not in ['status', 'headers', 'output']:
                    try: del myctx[k]
                    except KeyError: pass
        
        t = threading.Thread(target=newfunc)
        background.threaddb[id(t)] = t
        t.start()
        web.ctx.headers = []
        return seeother(changequery(_t=id(t)))
    return internal
background.threaddb = {}

def backgrounder(func):
    def internal(*a, **kw):
        i = web.input(_method='get')
        if '_t' in i:
            try:
                t = background.threaddb[int(i._t)]
            except KeyError:
                return web.notfound()
            web._context[threading.currentThread()] = web._context[t]
            return
        else:
            return func(*a, **kw)
    return internal

class Reloader:
    """
    Before every request, checks to see if any loaded modules have changed on 
    disk and, if so, reloads them.
    """
    def __init__(self, func):
        self.func = func
        self.mtimes = {}
        # cheetah:
        # b = _compiletemplate.bases
        # _compiletemplate = globals()['__compiletemplate']
        # _compiletemplate.bases = b
        
        web.loadhooks['reloader'] = self.check
        # todo:
        #  - replace relrcheck with a loadhook
        #if reloader in middleware:
        #    relr = reloader(None)
        #    relrcheck = relr.check
        #    middleware.remove(reloader)
        #else:
        #    relr = None
        #    relrcheck = lambda: None
        # if relr:
        #     relr.func = wsgifunc
        #     return wsgifunc
        # 
        
    def check(self):
        for mod in sys.modules.values():
            try: 
                mtime = os.stat(mod.__file__).st_mtime
            except (AttributeError, OSError, IOError): 
                continue
            if mod.__file__.endswith('.pyc') and \
               os.path.exists(mod.__file__[:-1]):
                mtime = max(os.stat(mod.__file__[:-1]).st_mtime, mtime)
            if mod not in self.mtimes:
                self.mtimes[mod] = mtime
            elif self.mtimes[mod] < mtime:
                try: 
                    reload(mod)
                    self.mtimes[mod] = mtime
                except ImportError: 
                    pass
        return True
    
    def __call__(self, e, o): 
        self.check()
        return self.func(e, o)

reloader = Reloader

def profiler(app):
    """Outputs basic profiling information at the bottom of each response."""
    from utils import profile
    def profile_internal(e, o):
        out, result = profile(app)(e, o)
        return out + ['<pre>' + net.websafe(result) + '</pre>']
    return profile_internal

if __name__ == "__main__":
    import doctest
    doctest.testmod()
