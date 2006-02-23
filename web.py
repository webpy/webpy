#!/usr/bin/env python
"""web.py: makes web apps (http://webpy.org)"""
__version__ = "0.135"
__license__ = "Affero General Public License, Version 1"
__author__ = "Aaron Swartz <me@aaronsw.com>"

from __future__ import generators

# long term todo:
#   - new form system
#   - new templating system
#   - unit tests?

# todo:
#   - get rid of upvars
#   - provide an option to use .write()
#   - add ip:port support
#   - allow people to do $self.id from inside a reparam
#   - add sqlite support
#   - make storage a subclass of dictionary
#   - convert datetimes, floats in WebSafe
#   - locks around memoize
#   - fix memoize to use cacheify style techniques
#   - merge curval query with the insert
#   - figure out how to handle squid, etc. for web.ctx.ip

import os, os.path, sys, time, types, traceback
import cgi, re, urllib, urlparse, Cookie, pprint
from threading import currentThread
from tokenize import tokenprog
iters = (list, tuple)
if hasattr(__builtins__, 'set'): iters += (set,)
try: from sets import Set; iters += (Set,)
except ImportError: pass
try: import datetime, itertools
except ImportError: pass
try:
    from Cheetah.Compiler import Compiler
    from Cheetah.Filters import Filter
    _hasTemplating = True
except ImportError:
    _hasTemplating = False

try:
    from DBUtils.PooledDB import PooledDB
    _hasPooling = True
except ImportError:
    _hasPooling = False

# hack for compatibility with Python 2.3:
if not hasattr(traceback, 'format_exc'):
    from cStringIO import StringIO
    def format_exc(limit=None):
        s = StringIO()
        traceback.print_exc(limit, s)
        return s.getvalue()
    traceback.format_exc = format_exc

## general utils

def _strips(direction, text, remove):
    if direction == 'l': 
        if text.startswith(remove): return text[len(remove):]
    elif direction == 'r':
        if text.endswith(remove): return text[:-len(remove)]
    else: 
        raise "WrongDirection", "Needs to be r or l."
    return text

def rstrips(text, remove):
    """removes the string `remove` from the right of `text`"""
    return _strips('r', text, remove)
def lstrips(text, remove):
    """removes the string `remove` from the right of `text`"""
    return _strips('l', text, remove)
def strips(a, b):
    """removes the string `remove` from the both sides of `text`"""
    return rstrips(lstrips(a,b),b)

def autoassign(self, locals):
    """
    Automatically assigns local variables to `self`.
    Generally used in `__init__` methods, as in:

        def __init__(self, foo, bar, baz=1): autoassign(self, locals())
    """
    #locals = sys._getframe(1).f_locals
    #self = locals['self']
    for (k, v) in locals.iteritems():
        if k == 'self': continue
        setattr(self, k, v)

class Storage(dict):
    """
    A Storage object is like a dictionary except `obj.foo` can be used
    instead of `obj['foo']`. Create one by doing `storage({'a':1})`.
    """
    def __getattr__(self, k): 
        if self.has_key(k): return self[k]
        raise AttributeError, repr(k)
    def __setattr__(self, k, v): self[k] = v
    def __repr__(self): return '<Storage '+dict.__repr__(self)+'>'

storage = Storage

def storify(f, *requireds, **defaults):
    """
    Creates a `storage` object from dictionary d, raising `KeyError` if
    d doesn't have all of the keys in `requireds` and using the default 
    values for keys found in `defaults`.

    For example, `storify({'a':1, 'c':3}, b=2, c=0)` will return the equivalent of
    `storage({'a':1, 'b':2, 'c':3})`.
    """
    stor = Storage()

    for k in requireds + tuple(f.keys()):
        v = f[k]
        if isinstance(v, list): v = v[-1]
        if hasattr(v, 'value'): v = v.value
        setattr(stor, k, v)

    for (k,v) in defaults.iteritems():
        result = v
        if hasattr(stor, k): result = stor[k]
        if v == () and not isinstance(result, tuple): result = (result,)
        setattr(stor, k, result)
    
    return stor

class memoize:
    """
    "Memoizes" a function, caching its return values for each input.
    """
    def __init__(self, func): self.func = func; self.cache = {}
    def __call__(self, *a, **k):
        key = (a, tuple(k.items()))
        if key not in self.cache: self.cache[key] = self.func(*a, **k)
        return self.cache[key]

re_compile = memoize(re.compile) #@@ threadsafe?
re_compile.__doc__ = """
A memoized version of re.compile.
"""

class _re_subm_proxy:       
    def __init__(self): self.match = None
    def __call__(self, match): self.match = match; return ''

def re_subm(pat, repl, string):
    """Like re.sub, but returns the replacement _and_ the match object."""
    r = re_compile(pat)
    proxy = _re_subm_proxy()
    r.sub(proxy.__call__, string)
    return r.sub(repl, string), proxy.match

def group(seq, size): 
    """
    Returns an iterator over a series of lists of length size from iterable.

    For example, `list(group([1,2,3,4], 2))` returns `[[1,2],[3,4]]`.
    """
    if not hasattr(seq, 'next'):  seq = iter(seq)
    while True: yield [seq.next() for i in xrange(size)]

class iterbetter:
    """
    Returns an object that can be used as an iterator 
    but can also be used via __getitem__ (although it 
    cannot go backwards -- that is, you cannot request 
    `iterbetter[0]` after requesting `iterbetter[1]`).
    """
    def __init__(self, iterator): self.i, self.c = iterator, 0
    def __iter__(self): 
        while 1: yield self.i.next(); self.c += 1
    def __getitem__(self, i):
        #todo: slices
        if i > self.c: raise KeyError, "already passed "+str(i)
        try:
            while i < self.c: self.i.next(); self.c += 1
            # now self.c == i
            self.c += 1; return self.i.next()
        except StopIteration: raise KeyError, repr(i)

def dictreverse(d):
    """Takes a dictionary like `{1:2, 3:4}` and returns `{2:1, 4:3}`."""
    return dict([(v,k) for k,v in d.iteritems()])

def dictfind(dictionary, element):
    """
    Returns a key whose value in `dictionary` is `element` 
    or, if none exists, None.
    """
    for (k,v) in dictionary.iteritems():
        if element is v: return k

def dictincr(dictionary, element):
    """
    Increments `element` in `dictionary`, 
    setting it to one if it doesn't exist.
    """
    dictionary.setdefault(element, 0)
    dictionary[element] += 1
    return dictionary[element]

def dictadd(a, b):
    """Returns a dictionary consisting of the keys in `a` and `b`."""
    result = {}
    result.update(a)
    result.update(b)
    return result

sumdicts = dictadd # deprecated

def listget(l, n, default=None):
    """Returns `l[n]` if it exists, `default` otherwise."""
    if len(l)-1 < n: return default
    return l[n]

def upvars(n=2):
    """Guido van Rossum doesn't want you to use this function."""
    return dictadd(
      sys._getframe(n).f_globals,
      sys._getframe(n).f_locals)

class capturestdout:
    """
    Captures everything func prints to stdout and returns it instead.

    **WARNING:** Not threadsafe!
    """
    def __init__(self, func): self.func = func
    def __call__(self, *args, **kw):
        from cStringIO import StringIO
        # Not threadsafe!
        out = StringIO()
        oldstdout = sys.stdout
        sys.stdout = out
        try: self.func(*args, **kw)
        finally: sys.stdout = oldstdout
        return out.getvalue()

class profile:
    """
    Profiles `func` and returns a tuple containing its output
    and a string with human-readable profiling information.
    """
    def __init__(self, func): self.func = func
    def __call__(self, *args, **kw):
        import hotshot, hotshot.stats, tempfile, time
        temp = tempfile.NamedTemporaryFile()
        prof = hotshot.Profile(temp.name)

        stime = time.time()
        result = prof.runcall(self.func, *args)
        stime = time.time() - stime

        prof.close()
        stats = hotshot.stats.load(temp.name)
        stats.strip_dirs()
        stats.sort_stats('time', 'calls')
        x =  '\n\ntook '+ str(stime) + ' seconds\n'
        x += capturestdout(stats.print_stats)(40)
        x += capturestdout(stats.print_callers)()
        return result, x

def tryall(context, prefix=None):
    """
    Tries a series of functions and prints their results. 
    `context` is a dictionary mapping names to values; 
    the value will only be tried if it's callable.

    For example, you might have a file `test/stuff.py` 
    with a series of functions testing various things in it. 
    At the bottom, have a line:

        if __name__ == "__main__": tryall(globals())

    Then you can run `python test/stuff.py` and get the results of 
    all the tests.
    """
    context = context.copy() # vars() would update
    results = {}
    for (k, v) in context.iteritems():
        if not hasattr(v, '__call__'): continue
        if prefix and not k.startswith(prefix): continue
        print k+':',
        try:
            r = v()
            dictincr(results, r)
            print r
        except:
            print 'ERROR'
            dictincr(results, 'ERROR')
            print '   '+'\n   '.join(traceback.format_exc().split('\n'))
        
    print '-'*40
    print 'results:'
    for (k, v) in results.iteritems():
        print ' '*2, str(k)+':', v

class threadeddict:
    """
    Takes a dictionary that maps threads to objects. 
    When a thread tries to get or set an attribute or item 
    of the threadeddict, it passes it on to the object 
    for that thread in dictionary.
    """
    def __init__(self, d): self.__dict__['_threadeddict__d'] = d
    def __getattr__(self, a): return getattr(self.__d[currentThread()], a)
    def __getitem__(self, i): return self.__d[currentThread()][i]
    def __setattr__(self, a, v): return setattr(self.__d[currentThread()], a, v)
    def __setitem__(self, i, v): self.__d[currentThread()][i] = v
    def __hash__(self): return hash(self.__d[currentThread()])

## url utils

def prefixurl(base=''):
    """
    Sorry, this function is really difficult to explain.
    Maybe some other time.
    """
    url = context.path.lstrip('/')
    for i in xrange(url.count('/')): base += '../'
    if not base: base = './'
    return base

urlquote = urllib.quote

## formatting

try:
    from markdown import markdown # http://webpy.org/markdown.py
except ImportError: pass

r_url = re_compile('(?<!\()(http://(\S+))')
def safemarkdown(text):
    """
    Converts text to HTML following the rules of Markdown, but blocking any
    outside HTML input, so that only the things supported by Markdown
    can be used. Also converts raw URLs to links.

    (requires [markdown.py](http://webpy.org/markdown.py))
    """
    if text:
        text = text.replace('<', '&lt;')
        # TODO: automatically get page title?
        text = r_url.sub(r'<\1>', text)
        text = markdown(text)
        return text

## db api

def _interpolate(format):
    """
    Takes a format string and returns a list of 2-tuples of the form
    (boolean, string) where boolean says whether string should be evaled
    or not.
    
    from http://lfw.org/python/Itpl.py (public domain, Ka-Ping Yee)
    """
    def matchorfail(text, pos):
        match = tokenprog.match(text, pos)
        if match is None:
            raise ItplError(text, pos)
        return match, match.end()
    
    namechars = "abcdefghijklmnopqrstuvwxyz" \
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_";
    chunks = []
    pos = 0

    while 1:
        dollar = format.find("$", pos)
        if dollar < 0: break
        nextchar = format[dollar+1]

        if nextchar == "{":
            chunks.append((0, format[pos:dollar]))
            pos, level = dollar+2, 1
            while level:
                match, pos = matchorfail(format, pos)
                tstart, tend = match.regs[3]
                token = format[tstart:tend]
                if token == "{": level = level+1
                elif token == "}": level = level-1
            chunks.append((1, format[dollar+2:pos-1]))

        elif nextchar in namechars:
            chunks.append((0, format[pos:dollar]))
            match, pos = matchorfail(format, dollar+1)
            while pos < len(format):
                if format[pos] == "." and \
                    pos+1 < len(format) and format[pos+1] in namechars:
                    match, pos = matchorfail(format, pos+1)
                elif format[pos] in "([":
                    pos, level = pos+1, 1
                    while level:
                        match, pos = matchorfail(format, pos)
                        tstart, tend = match.regs[3]
                        token = format[tstart:tend]
                        if token[0] in "([": level = level+1
                        elif token[0] in ")]": level = level-1
                else: break
            chunks.append((1, format[dollar+1:pos]))

        else:
            chunks.append((0, format[pos:dollar+1]))
            pos = dollar + 1 + (nextchar == "$")

    if pos < len(format): chunks.append((0, format[pos:]))
    return chunks

def sqlors(left, lst):
    """
    `left is a SQL clause like `tablename.arg = ` 
    and `lst` is a list of values. Returns a reparam-style
    pair featuring the SQL that ORs together the clause
    for each item in the lst.
    
    For example:
    
        web.sqlors('foo =', [1,2,3])
    
    would result in:
    
        foo = 1 OR foo = 2 OR foo = 3
    
    contributed by Steven Huffman <http://spez.name>
    """
    if isinstance(lst, iters) and len(lst) == 1: lst = lst[0]
    if isinstance(lst, iters):
        return '(' + left + (' OR ' + left).join([aparam() for x in lst]) + ")", lst
    elif not list: return "", []
    else:
        return left + aparam(), [lst,]

class UnknownParamstyle(Exception): pass
def aparam():
    """Use in a SQL string to make a spot for a db value."""
    p = ctx.db_module.paramstyle
    if p == 'qmark': return '?'
    elif p == 'numeric': return ':1'
    elif p in ['format', 'pyformat']: return '%s'
    raise UnknownParamstyle, p

def reparam(s, d):
    """
    Takes a string and a dictionary and interpolates the string
    using values from the dictionary. Returns a 2-tuple containing
    the a string with `aparam()`s in it and a list of the matching values.
    
    You can pass this sort of thing as a clause in any db function.
    Otherwise, you can pass a dictionary to the keyword argument `vars`
    and the function will call reparam for you.
    """
    vals = []
    result = []
    for live, chunk in _interpolate(s):
        if live:
            result.append(aparam())
            vals.append(eval(chunk, d))
        else: result.append(chunk)
    return ''.join(result), vals

class UnknownDB(Exception): pass
def connect(dbn, **kw):
    """
    Connects to the specified database. 
    db currently must be "postgres" or "mysql". 
    If DBUtils is installed, connection pooling will be used.
    """
    if dbn == "postgres": 
        try: import psycopg2 as db
        except ImportError: 
            try: import psycopg as db
            except ImportError: import pgdb as db
        kw['password'] = kw['pw']
        del kw['pw']
        kw['database'] = kw['db']
        del kw['db']
    elif dbn == "mysql":
        import MySQLdb as db
        kw['passwd'] = kw['pw']
        del kw['pw']
        db.paramstyle = 'pyformat' # it's both, like psycopg
    else: raise UnknownDB, dbn
    ctx.db_name = dbn
    ctx.db_module = db
    ctx.db_transaction = False
    if _hasPooling:
        if 'db' not in globals(): globals()['db'] = PooledDB(dbapi=db, **kw)
        ctx.db = globals()['db'].connection()
    else:
        ctx.db = db.connect(**kw)
    ctx.dbq_count = 0
    if globals().get('db_printing'):
        def db_execute(cur, q, d=None):
            ctx.dbq_count += 1
            try: outq = q % tuple(d)
            except: outq = q
            print>>debug, str(ctx.dbq_count)+':', outq
            a = time.time()
            out = cur.execute(q, d)
            b = time.time()
            print>>debug, '(%s)' % round(b-a, 2)
            return out
        ctx.db_execute = db_execute
    else:
        ctx.db_execute = lambda cur, q, d=None: cur.execute(q, d)
    return ctx.db

def transact():
    """Start a transaction."""
    # commit everything up to now, so we don't rollback it later
    ctx.db.commit()
    ctx.db_transaction = True

def commit():
    """Commits a transaction."""
    ctx.db.commit()
    ctx.db_transaction = False

def rollback():
    """Rolls back a transaction."""
    ctx.db.rollback()
    ctx.db_transaction = False    

def query(q, vars=None, processed=False):
    """
    Execute SQL query `q` using dictionary `vars` to interpolate it.
    If `processed=True`, `vars` is a `reparam`-style list to use 
    instead of interpolating.
    """
    if vars is None: vars = {}
    d = ctx.db.cursor()

    if not processed: q, vars = reparam(q, vars)
    ctx.db_execute(d, q, vars)
    if d.description:
        names = [x[0] for x in d.description]
        def iterwrapper():
            x = d.fetchone()
            while x:
                yield Storage(dict(zip(names, x)))
                x = d.fetchone()
        out = iterbetter(iterwrapper())
        out.__len__ = lambda: int(d.rowcount)
        out.list = lambda: [Storage(dict(zip(names, x))) for x in d.fetchall()]
    else:
        out = d.rowcount
    
    if not ctx.db_transaction: ctx.db.commit()    
    return out

def sqllist(l):
    """
    If a list, converts it to a comma-separated string. 
    Otherwise, returns the string.
    """
    if isinstance(l, str): return l
    else: return ', '.join(l)

def select(tables, vars=None, what='*', where=None, order=None, group=None, 
           limit=None, offset=None):
    """
    Selects `what` from `tables` with clauses `where`, `order`, 
    `group`, `limit`, and `offset. Uses vars to interpolate. 
    Otherwise, each clause can take a reparam-style list.
    """
    if vars is None: vars = {}
    values = []
    qout = "SELECT "+what+" FROM "+sqllist(tables)

    for (sql, val) in (
      ('WHERE', where), 
      ('GROUP BY', group), 
      ('ORDER BY', order), 
      ('LIMIT', limit), 
      ('OFFSET', offset)):
        if isinstance(val, (int, long)):
            if sql == 'WHERE':
                nquery, nvalue = 'id = '+aparam(), [val]
            else:
                nquery, nvalue = str(val), ()
        elif isinstance(val, (list, tuple)) and len(val) == 2:
            nquery, nvalue = val
        elif val:
            nquery, nvalue = reparam(val, vars)
        else: continue
        qout += " "+sql+" " + nquery
        values.extend(nvalue)
    return query(qout, values, processed=True)

def insert(tablename, seqname=None, **values):
    """
    Inserts `values` into `tablename`. Returns current sequence ID.
    Set `seqname` to the ID if it's not the default, or to `False`
    if there isn't one.
    """
    d = ctx.db.cursor()

    if values:
        q, v = "INSERT INTO %s (%s) VALUES (%s)" % (
            tablename,
            ", ".join(values.keys()),
            ', '.join([aparam() for x in values])
        ), values.values()
    else:
        q, v = "INSERT INTO %s DEFAULT VALUES" % tablename, None

    if seqname is False: pass
    elif ctx.db_name == "postgres": 
        if seqname is None: seqname = tablename + "_id_seq"
        q += "; SELECT currval('%s')" % seqname
    elif ctx.db_name == "mysql":
        ctx.db_execute(d, q, v)
        q = "SELECT last_insert_id()"
        v = ()
    elif ctx.db_name == "sqlite":
        # not really the same...
        q += "; SELECT last_insert_rowid()"

    ctx.db_execute(d, q, v)
    try: out = d.fetchone()[0]
    except: out = None
    
    if not ctx.db_transaction: ctx.db.commit()
    return out

def update(tables, where, vars=None, **values):
    """
    Update `tables` with clause `where` (interpolated using `vars`)
    and setting `values`.
    """
    if vars is None: vars = {}
    if isinstance(where, (int, long)):
        vars = [where]
        where = "id = "+aparam()
    elif isinstance(where, (list, tuple)) and len(where) == 2:
        where, vars = where
    else:
        where, vars = reparam(where, vars)
    
    d = ctx.db.cursor()
    ctx.db_execute(d, "UPDATE %s SET %s WHERE %s" % (
        sqllist(tables),
        ', '.join([k+'='+aparam() for k in values.keys()]),
        where),
    values.values()+vars)
    
    if not ctx.db_transaction: ctx.db.commit()        
    return d.rowcount

def delete(table, where, using=None, vars=None):
    """
    Deletes from `table` with clauses `where` and `using`.
    """
    if vars is None: vars = {}
    d = ctx.db.cursor()

    if isinstance(where, (int, long)):
        vars = [where]
        where = "id = "+aparam()
    elif isinstance(where, (list, tuple)) and len(where) == 2:
        where, vars = val
    else:
        where, vars = reparam(where, vars)
    q = 'DELETE FROM %s WHERE %s' % (table, where)
    if using: q += ' USING '+sqllist(using)
    ctx.db_execute(d, q, vars)

    if not ctx.db_transaction: ctx.db.commit()        
    return d.rowcount

## request handlers

def handle(mapping, fvars=None):
    """
    Call the appropriate function based on the url to function mapping in `mapping`.
    If no module for the function is specified, look up the function in `fvars`. If
    `fvars` is empty, using the caller's context.

    `mapping` should be a tuple of paired regular expressions with function name
    substitutions. `handle` will import modules as necessary.
    """
    for url, ofno in group(mapping, 2):
        if isinstance(ofno, tuple): ofn, fna = ofno[0], list(ofno[1:])
        else: ofn, fna = ofno, []
        fn, result = re_subm('^'+url+'$', ofn, context.path)
        if result: # it's a match
            if fn.split(' ', 1)[0] == "redirect":
                url = fn.split(' ', 1)[1]
                if context.method == "GET":
                    x = context.environ.get('QUERY_STRING', '')
                    if x: url += '?'+x
                return redirect(url)
            elif '.' in fn: 
                x = fn.split('.')
                mod, cls = '.'.join(x[:-1]), x[-1]
                mod = __import__(mod, globals(), locals(), [""])
                cls = getattr(mod, cls)
            else:
                cls = fn
                mod = fvars or upvars()
                if isinstance(mod, types.ModuleType): mod = vars(mod)
                try: cls = mod[cls]
                except KeyError: return notfound()
            
            meth = context.method
            if meth == "HEAD":
                if not hasattr(cls, meth): meth = "GET"
            if not hasattr(cls, meth): return nomethod(cls)
            tocall = getattr(cls(), meth)
            args = list(result.groups())
            for d in re.findall(r'\\(\d+)', ofn):
                args.pop(int(d)-1)
            return tocall(*([urllib.unquote(x) for x in args]+fna))

    return notfound()

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
    """
    def internal(self, arg):
        func = prefix+arg
        if hasattr(self, func): return getattr(self, func)()
        else: return notfound()
    return internal

## http defaults

def expires(delta):
    """
    Outputs an `Expires` header for `delta` from now. 
    `delta` is a `timedelta` object or a number of seconds.
    """
    try: datetime
    except NameError: raise Exception, "requires Python 2.3 or later"
    if isinstance(delta, (int, long)):
        delta = datetime.timedelta(seconds=delta)
    o = datetime.datetime.utcnow() + delta
    header('Expires', o.strftime("%a, %d %b %Y %T GMT"))

def lastmodified(d):
    """Outputs a `Last-Modified` header for `datetime`."""
    header('Last-Modified', d.strftime("%a, %d %b %Y %T GMT"))

"""
By default, these all return simple error messages that send very short messages 
(like "bad request") to the user. They can and should be overridden 
to return nicer ones.
"""
    
def redirect(url, status='301 Moved Permanently'):
    """
    Returns a `status` redirect to the new URL. 
    `url` is joined with the base URL so that things like 
    `redirect("about") will work properly.
    """
    newloc = urlparse.urljoin(context.home + context.path, url)
    context.status = status
    header('Content-Type', 'text/html')
    header('Location', newloc)
    # seems to add a three-second delay for some reason:
    # output('<a href="'+ newloc + '">moved permanently</a>')

def found(url):
    """A `302 Found` redirect."""
    return redirect(url, '302 Found')

def seeother(url):
    """A `303 See Other` redirect."""
    return redirect(url, '303 See Other')

def tempredirect(url):
    """A `307 Temporary Redirect` redirect."""
    return redirect(url, '307 Temporary Redirect')

def badrequest():
    """Return a `400 Bad Request` error."""
    context.status = '400 Bad Request'
    header('Content-Type', 'text/html')
    return output('bad request')

def notfound():
    """Returns a `404 Not Found` error."""
    context.status = '404 Not Found'
    header('Content-Type', 'text/html')
    return output('not found')

def nomethod(cls):
    """Returns a `405 Method Not Allowed` error for `cls`."""
    context.status = '405 Method Not Allowed'
    header('Content-Type', 'text/html')
    header("Allow", ', '.join([x for x in ['GET', 'HEAD', 'POST', 'PUT', 'DELETE'] if hasattr(cls, x)]))
    return output('method not allowed')

def gone():
    """Returns a `410 Gone` error."""
    context.status = '410 Gone'
    header('Content-Type', 'text/html')
    return output("gone")

def internalerror():
    """Returns a `500 Internal Server` error."""
    context.status = "500 Internal Server Error"
    context.headers = [('Content-Type', 'text/html')]
    context.output = "internal server error"


# adapted from Django <djangoproject.com> 
# Copyright (c) 2005, the Lawrence Journal-World
# Used under the modified BSD license:
# http://www.xfree86.org/3.3.6/COPYRIGHT2.html#5

DJANGO_500_PAGE = """#import inspect
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">
<html lang="en">
<head>
  <meta http-equiv="content-type" content="text/html; charset=utf-8" />
  <meta name="robots" content="NONE,NOARCHIVE" />
  <title>$exception_type at $context.path</title>
  <style type="text/css">
    html * { padding:0; margin:0; }
    body * { padding:10px 20px; }
    body * * { padding:0; }
    body { font:small sans-serif; }
    body>div { border-bottom:1px solid #ddd; }
    h1 { font-weight:normal; }
    h2 { margin-bottom:.8em; }
    h2 span { font-size:80%; color:#666; font-weight:normal; }
    h3 { margin:1em 0 .5em 0; }
    h4 { margin:0 0 .5em 0; font-weight: normal; }
    table { border:1px solid #ccc; border-collapse: collapse; background:white; }
    tbody td, tbody th { vertical-align:top; padding:2px 3px; }
    thead th { padding:1px 6px 1px 3px; background:#fefefe; text-align:left; font-weight:normal; font-size:11px; border:1px solid #ddd; }
    tbody th { text-align:right; color:#666; padding-right:.5em; }
    table.vars { margin:5px 0 2px 40px; }
    table.vars td, table.req td { font-family:monospace; }
    table td.code { width:100%;}
    table td.code div { overflow:hidden; }
    table.source th { color:#666; }
    table.source td { font-family:monospace; white-space:pre; border-bottom:1px solid #eee; }
    ul.traceback { list-style-type:none; }
    ul.traceback li.frame { margin-bottom:1em; }
    div.context { margin: 10px 0; }
    div.context ol { padding-left:30px; margin:0 10px; list-style-position: inside; }
    div.context ol li { font-family:monospace; white-space:pre; color:#666; cursor:pointer; }
    div.context ol.context-line li { color:black; background-color:#ccc; }
    div.context ol.context-line li span { float: right; }
    div.commands { margin-left: 40px; }
    div.commands a { color:black; text-decoration:none; }
    #summary { background: #ffc; }
    #summary h2 { font-weight: normal; color: #666; }
    #explanation { background:#eee; }
    #template, #template-not-exist { background:#f6f6f6; }
    #template-not-exist ul { margin: 0 0 0 20px; }
    #traceback { background:#eee; }
    #requestinfo { background:#f6f6f6; padding-left:120px; }
    #summary table { border:none; background:transparent; }
    #requestinfo h2, #requestinfo h3 { position:relative; margin-left:-100px; }
    #requestinfo h3 { margin-bottom:-1em; }
    .error { background: #ffc; }
    .specific { color:#cc3300; font-weight:bold; }
  </style>
  <script type="text/javascript">
  //<!--
    function getElementsByClassName(oElm, strTagName, strClassName){
        // Written by Jonathan Snook, http://www.snook.ca/jon; Add-ons by Robert Nyman, http://www.robertnyman.com
        var arrElements = (strTagName == "*" && document.all)? document.all :
        oElm.getElementsByTagName(strTagName);
        var arrReturnElements = new Array();
        strClassName = strClassName.replace(/\-/g, "\\-");
        var oRegExp = new RegExp("(^|\\s)" + strClassName + "(\\s|$)");
        var oElement;
        for(var i=0; i<arrElements.length; i++){
            oElement = arrElements[i];
            if(oRegExp.test(oElement.className)){
                arrReturnElements.push(oElement);
            }
        }
        return (arrReturnElements)
    }
    function hideAll(elems) {
      for (var e = 0; e < elems.length; e++) {
        elems[e].style.display = 'none';
      }
    }
    window.onload = function() {
      hideAll(getElementsByClassName(document, 'table', 'vars'));
      hideAll(getElementsByClassName(document, 'ol', 'pre-context'));
      hideAll(getElementsByClassName(document, 'ol', 'post-context'));
    }
    function toggle() {
      for (var i = 0; i < arguments.length; i++) {
        var e = document.getElementById(arguments[i]);
        if (e) {
          e.style.display = e.style.display == 'none' ? 'block' : 'none';
        }
      }
      return false;
    }
    function varToggle(link, id) {
      toggle('v' + id);
      var s = link.getElementsByTagName('span')[0];
      var uarr = String.fromCharCode(0x25b6);
      var darr = String.fromCharCode(0x25bc);
      s.innerHTML = s.innerHTML == uarr ? darr : uarr;
      return false;
    }
    //-->
  </script>
</head>
<body>

<div id="summary">
  <h1>$exception_type at $context.path</h1>
  <h2>$exception_value</h2>
  <table><tr>
    <th>Python</th>
    <td>$lastframe.filename in $lastframe.function, line $lastframe.lineno</td>
  </tr><tr>
    <th>Web</th>
    <td>$context.method $context.home$context.path</td>
  </tr></table>
</div>
<div id="traceback">
  <h2>Traceback <span>(innermost first)</span></h2>
  <ul class="traceback">
    #for frame in $frames
      <li class="frame">
        <code>$frame.filename</code> in <code>$frame.function</code>

        #if $frame.context_line
          <div class="context" id="c$frame.id">
            #if $frame.pre_context
              <ol start="$frame.pre_context_lineno" class="pre-context" id="pre$frame.id">#for line in $frame.pre_context#<li onclick="toggle('pre$frame.id', 'post$frame.id')">$line</li>#end for#</ol>
            #end if
            <ol start="$frame.lineno" class="context-line"><li onclick="toggle('pre$frame.id', 'post$frame.id')">$frame.context_line <span>...</span></li></ol>
            #if $frame.post_context
              <ol start='$(frame.lineno+1)' class="post-context" id="post$frame.id">#for line in $frame.post_context#<li onclick="toggle('pre$frame.id', 'post$frame.id')">$line</li>#end for#</ol>
            #end if
          </div>
        #end if

        #if $frame.vars
          <div class="commands">
              <a href='#' onclick="return varToggle(this, '$frame.id')"><span>&#x25b6;</span> Local vars</a>## $inspect.formatargvalues(*inspect.getargvalues(frame['tb'].tb_frame))
          </div>
          <table class="vars" id="v$frame.id">
            <thead>
              <tr>
                <th>Variable</th>
                <th>Value</th>
              </tr>
            </thead>
            <tbody>
              #set frameitems = $frame.vars
              #silent frameitems.sort(lambda x,y: cmp(x[0], y[0]))
              #for (key, val) in frameitems
                <tr>
                  <td>$key</td>
                  <td class="code"><div>$prettify(val)</div></td>
                </tr>
              #end for
            </tbody>
          </table>
        #end if
      </li>
    #end for
  </ul>
</div>

<div id="requestinfo">
  #if $context_.output or $context_.headers
    <h2>Response so far</h2>
    <h3>HEADERS</h3>
    #if $context.headers
      <p class="req"><code>
      #for (k, v) in $context_.headers
        $k: $v<br />
      #end for
      
      </code></p>
    #else
      <p>No headers.</p>
    #end if
    <h3>BODY</h3>
    <p class="req" style="padding-bottom: 2em"><code>
    $context_.output
    </code></p>
  #end if
  
  <h2>Request information</h2>

  <h3>INPUT</h3>
  #if $input_
    <table class="req">
      <thead>
        <tr>
          <th>Variable</th>
          <th>Value</th>
        </tr>
      </thead>
      <tbody>
        #set myitems = $input_.items()
        #silent myitems.sort(lambda x,y: cmp(x[0], y[0]))
        #for (key, val) in myitems
          <tr>
            <td>$key</td>
            <td class="code"><div>$val</div></td>
          </tr>
        #end for
      </tbody>
    </table>
  #else
  <p>No input data.</p>
  #end if

  <h3 id="cookie-info">COOKIES</h3>
  #if $cookies_
    <table class="req">
      <thead>
        <tr>
          <th>Variable</th>
          <th>Value</th>
        </tr>
      </thead>
      <tbody>
        #for (key, val) in $cookies_.items()
          <tr>
            <td>$key</td>
            <td class="code"><div>$val</div></td>
          </tr>
        #end for
      </tbody>
    </table>
  #else
    <p>No cookie data</p>
  #end if

  <h3 id="meta-info">META</h3>
  <table class="req">
    <thead>
      <tr>
        <th>Variable</th>
        <th>Value</th>
      </tr>
    </thead>
    <tbody>
      #set myitems = $context_.items()
      #silent myitems.sort(lambda x,y: cmp(x[0], y[0]))
      #for (key, val) in $myitems
      #if not $key.startswith('_') and $key not in ['env', 'output', 'headers', 'environ', 'status', 'db_execute']
        <tr>
          <td>$key</td>
          <td class="code"><div>$prettify($val)</div></td>
        </tr>
      #end if
      #end for
    </tbody>
  </table>

  <h3 id="meta-info">ENVIRONMENT</h3>
  <table class="req">
    <thead>
      <tr>
        <th>Variable</th>
        <th>Value</th>
      </tr>
    </thead>
    <tbody>
      #set myitems = $context_.environ.items()
      #silent myitems.sort(lambda x,y: cmp(x[0], y[0]))  
      #for (key, val) in $myitems
        <tr>
          <td>$key</td>
          <td class="code"><div>$prettify($val)</div></td>
        </tr>
      #end for
    </tbody>
  </table>

</div>

<div id="explanation">
  <p>
    You're seeing this error because you have <code>web.internalerror</code>
    set to <code>web.debugerror</code>. Change that if you want a different one.
  </p>
</div>

</body>
</html>"""

def djangoerror():
    def _get_lines_from_file(filename, lineno, context_lines):
        """
        Returns context_lines before and after lineno from file.
        Returns (pre_context_lineno, pre_context, context_line, post_context).
        """
        try:
            source = open(filename).readlines()
            lower_bound = max(0, lineno - context_lines)
            upper_bound = lineno + context_lines

            pre_context = [line.strip('\n') for line in source[lower_bound:lineno]]
            context_line = source[lineno].strip('\n')
            post_context = [line.strip('\n') for line in source[lineno+1:upper_bound]]

            return lower_bound, pre_context, context_line, post_context
        except (OSError, IOError):
            return None, [], None, []    
    
    exception_type, exception_value, tb = sys.exc_info()
    frames = []
    while tb is not None:
        filename = tb.tb_frame.f_code.co_filename
        function = tb.tb_frame.f_code.co_name
        lineno = tb.tb_lineno - 1
        pre_context_lineno, pre_context, context_line, post_context = _get_lines_from_file(filename, lineno, 7)
        frames.append({
            'tb': tb,
            'filename': filename,
            'function': function,
            'lineno': lineno,
            'vars': tb.tb_frame.f_locals.items(),
            'id': id(tb),
            'pre_context': pre_context,
            'context_line': context_line,
            'post_context': post_context,
            'pre_context_lineno': pre_context_lineno,
        })
        tb = tb.tb_next
    lastframe = frames[-1]
    frames.reverse()
    urljoin = urlparse.urljoin
    input_ = input()
    cookies_ = cookies()
    context_ = context
    def prettify(x):
        try: out = pprint.pformat(x)
        except Exception, e: out = '[could not display: <'+e.__class__.__name__+': '+str(e)+'>]'
        return out
    return render(DJANGO_500_PAGE, asTemplate=True, isString=True)

def debugerror():
    """
    A replacement for `internalerror` that presents a nice page with lots
    of debug information for the programmer.

    (Based on the beautiful 500 page from [Django](http://djangoproject.com/), 
    designed by [Wilson Miner](http://wilsonminer.com/).)

    Requires [Cheetah](http://cheetahtemplate.org/).
    """
    # need to do django first, so it can get the old stuff
    if _hasTemplating:
        out = str(djangoerror())
    else:
        # Cheetah isn't installed
        out = """<p>You've set web.py to use the fancier debugerror error messages,
but these messages require you install the Cheetah template 
system. For more information, see 
<a href="http://webpy.org/">the web.py website</a>.</p>

<p>In the meantime, here's a plain old error message:</p>

<pre>%s</pre>

<p>(If it says something about 'Compiler', then it's probably
because you're trying to use templates and you haven't
installed Cheetah. See above.)</p>
""" % htmlquote(traceback.format_exc())
    context.status = "500 Internal Server Error"
    context.headers = [('Content-Type', 'text/html')]
    context.output = out


## rendering

r_include = re_compile(r'(?!\\)#include \"(.*?)\"($|#)', re.M)
def __compiletemplate(template, base=None, isString=False):
    if isString: text = template
    else: text = open('templates/'+template).read()
    # implement #include at compile-time
    def do_include(match):
        text = open('templates/'+match.groups()[0]).read()
        return text
    while r_include.findall(text): text = r_include.sub(do_include, text)

    execspace = _compiletemplate.bases.copy()
    c = Compiler(source=text, mainClassName='GenTemplate')
    c.addImportedVarNames(execspace.keys())
    exec str(c) in execspace
    if base: _compiletemplate.bases[base] = execspace['GenTemplate']

    return execspace['GenTemplate']

_compiletemplate = memoize(__compiletemplate)
_compiletemplate.bases = {}

def htmlquote(s):
    """Encodes `s` for raw use in HTML."""
    s = s.replace("&", "&amp;") # Must be done first!
    s = s.replace("<", "&lt;")
    s = s.replace(">", "&gt;")
    s = s.replace("'", "&#39;")
    s = s.replace('"', "&quot;")
    return s

if _hasTemplating:
    class WebSafe(Filter):
        def filter(selv, val, **kw): 
            if val is None: return ''
            return htmlquote(str(val))

def render(template, terms=None, asTemplate=False, base=None, isString=False): 
    """
    Renders a template, caching where it can.
    
    `template` is the name of a file containing the a template in
    the `templates/` folder, unless `isString`, in which case it's the template
    itself.

    `terms` is a dictionary used to fill the template. If it's None, then
    the caller's local variables are used instead, plus context, if it's not already 
    set, is set to `context`.

    If asTemplate is False, it `output`s the template directly. Otherwise,
    it returns the template object.

    If the template is a potential base template (that is, something other templates)
    can extend, then base should be a string with the name of the template. The
    template will be cached and made available for future calls to `render`.

    Requires [Cheetah](http://cheetahtemplate.org/).
    """
    # terms=['var1', 'var2'] means grab those variables
    if isinstance(terms, list):
        new = {}; old = upvars()
        for k in terms: new[k] = old[k]
        terms = new
    # default: grab all locals
    elif terms is None:
        terms = {'context': context}
        terms.update(sys._getframe(1).f_locals)
    # terms=d means use d as the searchList
    if not isinstance(terms, tuple): 
        terms = (terms,)
    
    if not isString and template.endswith('.html'): header('Content-Type','text/html; charset=utf-8')
        
    t = _compiletemplate(template, base=base, isString=isString)
    t = t(searchList=terms, filter=WebSafe)
    if asTemplate: return t
    else: return output(str(t))

## input forms

def input(*requireds, **defaults):
    """
    Returns a `storage` object with the GET and POST arguments. 
    See `storify` for how `requireds` and `defaults` work.
    """
    if not hasattr(context, '_inputfs'): context._inputfs = cgi.FieldStorage(fp = context.environ['wsgi.input'],environ=context.environ, keep_blank_values=1)
    return storify(context._inputfs, *requireds, **defaults)

## cookies

def setcookie(name, value, expires="", domain=None):
    """Sets a cookie."""
    if expires < 0: expires = -1000000000 
    kargs = {'expires': expires, 'path':'/'}
    if domain: kargs['domain'] = domain
    # @@ should we limit cookies to a different path?
    c = Cookie.SimpleCookie()
    c[name] = value
    for key, val in kargs.iteritems(): c[name][key] = val
    header('Set-Cookie', c.items()[0][1].OutputString())

def cookies(*requireds, **defaults):
    """
    Returns a `storage` object with all the cookies in it.
    See `storify` for how `requireds` and `defaults` work.
    """
    c = Cookie.SimpleCookie()
    c.load(context.environ.get('HTTP_COOKIE', ''))
    return storify(c, *requireds, **defaults)

## WSGI Sugar

def header(h, v):
    """Adds the header `h: v` with the response."""
    context.headers.append((h, v))
def output(s):
    """Appends `s` to the response."""
    context.output += str(s)

def write(t):
    """Converts a standard CGI-style string response into `header` and `output` calls."""
    t = str(t)
    t.replace('\r\n', '\n')
    head, body = t.split('\n\n', 1)
    lines = head.split('\n')
    
    for line in lines:
        if line.isspace(): continue
        h, v = line.split(":", 1)
        v = v.strip()
        if h.lower() == "status": context.status = v
        else: header(h, v)

    output(body)

def webpyfunc(inp, fvars=None, autoreload=False):
    """If `inp` is a url mapping, returns a function that calls handle."""
    if not fvars: fvars = upvars()
    if not hasattr(inp, '__call__'):
        if autoreload:
            # black magic to make autoreload work:
            mod = __import__(fvars['__file__'].split(os.path.sep).pop().split('.')[0])
            #@@probably should replace this with some inspect magic
            name = dictfind(fvars, inp)
            func = lambda: handle(getattr(mod, name), mod)
        else:
            func = lambda: handle(inp, fvars)
    else:
        func = inp
    return func

def wsgifunc(func, *middleware):
    """Returns a WSGI-compatible function from a webpy-function."""
    middleware = list(middleware)
    if reloader in middleware:
        relr = reloader(None)
        relrcheck = relr.check
        middleware.remove(reloader)
    else:
        relr = None
        relrcheck = lambda: None
    
    def wsgifunc(e, r):
        _load(e)
        relrcheck()
        try: result = func()
        except StopIteration: result = None
        is_generator = result and hasattr(result, 'next')
        if is_generator:
            # we need to give wsgi back the headers first,
            # so we need to do at iteration
            try: firstchunk = result.next()
            except StopIteration: firstchunk = ''
        status, headers, output = ctx.status, ctx.headers, ctx.output
        _unload()
        r(status, headers)
        if is_generator: return itertools.chain([firstchunk], result)
        elif isinstance(output, str): return [output] #@@ other stringlikes?
        elif hasattr(output, 'next'): return output
        else: raise Exception, "Invalid web.context.output"
    
    for x in middleware: wsgifunc = x(wsgifunc)
    
    if relr:
        relr.func = wsgifunc
        return wsgifunc
    return wsgifunc

def run(inp, *middleware):
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
    autoreload = reloader in middleware
    fvars = upvars()
    return runwsgi(wsgifunc(webpyfunc(inp, fvars, autoreload), *middleware))

def runwsgi(func):
    """
    Runs a WSGI-compatible function using FCGI, SCGI, or a simple web server,
    as appropriate.
    """
    #@@ improve detection
    if os.environ.has_key('SERVER_SOFTWARE'): # cgi
        os.environ['FCGI_FORCE_CGI'] = 'Y'

    if (os.environ.has_key('PHP_FCGI_CHILDREN') #lighttpd fastcgi
      or os.environ.has_key('SERVER_SOFTWARE')):
        import flup.server.fcgi
        return runfcgi(func)

    if 'scgi' in sys.argv:
        import flup.server.scgi
        return runscgi(func)

    # command line:
    return runsimple(func, listget(sys.argv, 1, 8080))
    
def runsimple(func, port=8080):
    """
    Runs a simple HTTP server hosting WSGI app `func`. The directory `static/` is
    hosted statically.

    Based on [WsgiServer](http://www.owlfish.com/software/wsgiutils/documentation/wsgi-server-api.html) 
    from [Colin Stewart](http://www.owlfish.com/).
    """
    # Copyright (c) 2004 Colin Stewart (http://www.owlfish.com/)
    # Modified somewhat for simplicity
    # Used under the modified BSD license:
    # http://www.xfree86.org/3.3.6/COPYRIGHT2.html#5

    import SimpleHTTPServer, SocketServer, BaseHTTPServer, urlparse
    import sys, socket, errno
    import traceback

    class WSGIHandler (SimpleHTTPServer.SimpleHTTPRequestHandler):
        def runWSGIApp(self):
            protocol, host, path, parameters, query, fragment = urlparse.urlparse ('http://dummyhost%s' % self.path)
            # we only use path, query
            env = {'wsgi.version': (1,0)
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
                   ,'CONTENT_TYPE': self.headers.get ('Content-Type', '')
                   ,'CONTENT_LENGTH': self.headers.get ('Content-Length', '')
                   ,'REMOTE_ADDR': self.client_address[0]
                   ,'SERVER_NAME': self.server.server_address [0]
                   ,'SERVER_PORT': str (self.server.server_address [1])
                   ,'SERVER_PROTOCOL': self.request_version
                   }

            for httpHeader, httpValue in self.headers.items():
                env ['HTTP_%s' % httpHeader.replace ('-', '_').upper()] = httpValue

            # Setup the state
            self.wsgiSentHeaders = 0
            self.wsgiHeaders = []

            try:
                # We have there environment, now invoke the application
                result = self.server.app(env, self.wsgiStartResponse)
                try:
                    try:
                        for data in result:
                            if data: self.wsgiWriteData (data)
                    finally:
                        if hasattr(result, 'close'): result.close()
                except socket.error, socketErr:
                    # Catch common network errors and suppress them
                    if (socketErr.args[0] in (errno.ECONNABORTED, errno.EPIPE)): return
                except socket.timeout, socketTimeout: return
            except:
                print >> debug, traceback.format_exc(),
                internalerror()
                if not self.wsgiSentHeaders:
                    self.wsgiStartResponse(ctx.status, ctx.headers)
                self.wsgiWriteData(ctx.output)

            if (not self.wsgiSentHeaders):
                # We must write out something!
                self.wsgiWriteData(" ")
            return

        do_POST = runWSGIApp

        def do_GET(self):
            if self.path.startswith('/static/'):
                SimpleHTTPServer.SimpleHTTPRequestHandler.do_GET(self)
            else:
                self.runWSGIApp()

        def wsgiStartResponse (self, response_status, response_headers, exc_info=None):
            if (self.wsgiSentHeaders):
                raise Exception ("Headers already sent and start_response called again!")
            # Should really take a copy to avoid changes in the application....
            self.wsgiHeaders = (response_status, response_headers)
            return self.wsgiWriteData

        def wsgiWriteData (self, data):
            if (not self.wsgiSentHeaders):
                status, headers = self.wsgiHeaders
                # Need to send header prior to data
                statusCode = status [:status.find (' ')]
                statusMsg = status [status.find (' ') + 1:]
                self.send_response (int (statusCode), statusMsg)
                for header, value in headers:
                    self.send_header (header, value)
                self.end_headers()
                self.wsgiSentHeaders = 1
            # Send the data
            self.wfile.write (data)

    class WSGIServer (SocketServer.ThreadingMixIn, BaseHTTPServer.HTTPServer):
        def __init__(self, func):
            BaseHTTPServer.HTTPServer.__init__(self, ("0.0.0.0", int(port)), WSGIHandler)
            self.app = func
            self.serverShuttingDown = 0

    print "Launching server: http://0.0.0.0:"+str(port)+"/"
    WSGIServer(func).serve_forever()

def makeserver(WSGIServer):
    """Updates a flup-style WSGIServer with web.py-style error support."""
    class MyServer(WSGIServer):            
        def error(self, req):
            w = req.stdout.write
            internalerror()
            w('Status: '+context.status+'\r\n')
            for (h, v) in context.headers:
                w(h+': '+v+'\r\n')
            w('\r\n'+context.output)
                
    return MyServer
    
def runfcgi(func):
    """Runs a WSGI-function with a FastCGI server."""
    from flup.server.fcgi import WSGIServer
    return makeserver(WSGIServer)(func, multiplexed=True).run()

def runscgi(func):
    """Runs a WSGI-function with an SCGI server."""
    from flup.server.scgi import WSGIServer
    MyServer = makeserver(WSGIServer)
    if len(sys.argv) > 2: # progname, scgi
        args = sys.argv[:]
        args.remove('scgi')
        hostport = args[1]
        hostport = hostport.split(':',1)
        if len(hostport) == 2: hostport = (hostport[0], int(hostport[1]))
        else: hostport = ('localhost',int(hostport[0]))
    else: hostport = ('localhost',4000)
    return MyServer(func, bindAddress=hostport).run()

## debug

def debug(*args):
    """
    Prints a prettyprinted version of `args` to stderr.
    """
    try: out = context.environ['wsgi.errors']
    except: out = sys.stderr
    for x in args:
        print >> out, pprint.pformat(x)
    return ''

def debugwrite(x):
    try: out = context.environ['wsgi.errors']
    except: out = sys.stderr
    out.write(x)
debug.write = debugwrite

class reloader:
    """
    Before every request, checks to see if any loaded modules have changed on disk
    and, if so, reloads them.
    """
    def __init__(self, func, tocheck=None): 
        self.func = func
        self.mtimes = {}
        global _compiletemplate
        b = _compiletemplate.bases
        _compiletemplate = globals()['__compiletemplate']
        _compiletemplate.bases = b
    
    def check(self):
        for mod in sys.modules.values():
            try: mtime = os.stat(mod.__file__).st_mtime
            except (AttributeError, OSError, IOError): continue
            if mod.__file__.endswith('.pyc') and os.path.exists(mod.__file__[:-1]):
                mtime = max(os.stat(mod.__file__[:-1]).st_mtime, mtime)
            if mod not in self.mtimes:
                self.mtimes[mod] = mtime
            elif self.mtimes[mod] < mtime:
                try: reload(mod)
                except ImportError: pass
        return True
    
    def __call__(self, e, o): 
        self.check()
        return self.func(e, o)

def profiler(app):
    """Outputs basic profiling information at the bottom of each response."""
    def profile_internal(e, o):
        out, result = profile(app)(e, o)
        return out + ['<pre>'+result+'</pre>'] #@@encode
    return profile_internal

## setting up the context

class _outputter:
    """Wraps `sys.stdout` so that print statements go into the response."""
    def write(self, x): 
        if hasattr(ctx, 'output'): return output(x)
        else: _oldstdout.write(x)
    def flush(self): return _oldstdout.flush()
    def close(self): return _oldstdout.close()

_context = {currentThread():Storage()}
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
  
   `fullpath`
     : The full path requested, including query arguments.
  
   ### Response Data
  
   `status` (default: "200 OK")
     : The status code to be used in the response.
  
   `headers`
     : A list of 2-tuples to be used in the response.
  
   `output`
     : A string to be used as the response.
"""

if not '_oldstdout' in globals(): 
    _oldstdout = sys.stdout
    sys.stdout = _outputter()

def _load(env):
    _context[currentThread()] = Storage()
    ctx.environ = ctx.env = env
    ctx.host = env.get('HTTP_HOST')
    ctx.home = 'http://' + env.get('HTTP_HOST', '[unknown]') + env.get('SCRIPT_NAME', '')
    ctx.ip = env.get('REMOTE_ADDR')
    ctx.method = env.get('REQUEST_METHOD')
    ctx.path = env.get('PATH_INFO')
    # http://trac.lighttpd.net/trac/ticket/406 requires:
    if env.get('SERVER_SOFTWARE', '').startswith('lighttpd/'):
        ctx.path = lstrips(env.get('REQUEST_URI').split('?')[0], env.get('SCRIPT_NAME'))

    ctx.fullpath = ctx.path
    if dict(input()): ctx.fullpath+='?'+urllib.urlencode(dict(input()))
    ctx.status = '200 OK'
    ctx.headers = []
    ctx.output = ''
    if 'db_parameters' in globals():
        connect(**db_parameters)

def _unload(): 
    # ensures db cursors and such are GCed promptly
    del _context[currentThread()]

if __name__ == "__main__":
    urls = ('/web.py', 'source')
    class source:
        def GET(self):
            header('Content-Type', 'text/python')
            print open(sys.argv[0]).read()
    run(urls)
