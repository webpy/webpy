#!/usr/bin/env python
"""web.py: makes web apps (http://webpy.org)"""
__version__ = "0.121"
__license__ = "Affero General Public License, Version 1"
__author__ = "Aaron Swartz <me@aaronsw.com>"

# long term todo:
#   - new form system
#   - new templating system
#   - unit tests?

# todo:
#   - add sqlite support
#   - provide an option to use .write()

import cgi, re, os, os.path, sys, time, urllib, urlparse, pprint, traceback, types, Cookie
from threading import currentThread
try:
    from Cheetah.Compiler import Compiler
    from Cheetah.Filters import Filter
    _hasTemplating = True
except ImportError:
    _hasTemplating = False

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

def rstrips(a, b): return _strips('r', a, b)
def lstrips(a, b): return _strips('l', a, b)
def strips(a, b): return rstrips(lstrips(a,b),b)

def autoassign():
    locals = sys._getframe(2).f_locals
    self = locals['self']
    for (k, v) in locals.iteritems():
        if k == 'self': continue
        setattr(self, k, v)

class Storage:
    def __init__(self, initial=None):
        if initial:
            for k in initial.keys(): setattr(self, k, initial[k])
    
    def __getattr__(self, k): 
        if hasattr(self.__dict__, k) or (
          k.startswith('__') and k.endswith('__')): # special keyword
            return getattr(self.__dict__, k)
        raise AttributeError, repr(k)
    
    def __repr__(self): return '<Storage '+repr(self.__dict__)+'>'

storage = Storage

def storify(f, *requireds, **defaults):
    stor = Storage()

    for k in requireds + tuple(f.keys()):
        v = f[k]
        if isinstance(k, list): v = v[-1]
        if hasattr(v, 'value'): v = v.value
        setattr(stor, k, v)

    for (k,v) in defaults.iteritems():
        result = v
        if hasattr(stor, k): result = stor[k]
        if v == () and not isinstance(result, tuple): result = (result,)
        setattr(stor, k, result)
    
    return stor

class memoize:
    def __init__(self, func): self.func = func; self.cache = {}
    def __call__(self, *a, **k):
        key = (a, tuple(k.items()))
        if key not in self.cache: self.cache[key] = self.func(*a, **k)
        return self.cache[key]

re_compile = memoize(re.compile) #@@ threadsafe?

class _re_subm_proxy:       
    def __init__(self): self.match = None
    def __call__(self, match): self.match = match; return ''

def re_subm(pat, repl, string):
    """like re.sub, but returns the replacement and the match object"""
    r = re_compile(pat)
    proxy = _re_subm_proxy()
    r.sub(proxy.__call__, string)
    return r.sub(repl, string), proxy.match

def group(seq, size): 
    """Breaks 'seq' into a generator of lists with length 'size'."""
    if not hasattr(seq, 'next'):  seq = iter(seq)
    while True: yield [seq.next() for i in xrange(size)]

def dictfind(d, elt):
    for (k,v) in d.iteritems():
        if elt is v: return k

def dictincr(d, e):
    d.setdefault(e, 0)
    d[e] += 1
    return d[e]

def dictadd(a, b):
    result = {}
    result.update(a)
    result.update(b)
    return result

sumdicts = dictadd # deprecated

def listget(l, n, v=None):
    if len(l)-1 < n: return v
    return l[n]

def upvars(n=2):
    return dictadd(
      sys._getframe(n).f_globals,
      sys._getframe(n).f_locals)

class capturestdout:
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
    def __init__(self, func): self.func = func
    def __call__(self, *args, **kw):
        import hotshot, hotshot.stats, tempfile, time
        temp = tempfile.NamedTemporaryFile()
        prof = hotshot.Profile(temp.name)

        stime = time.time()
        result = prof.runcall(app, *args)
        stime = time.time() - stime

        prof.close()
        stats = hotshot.stats.load(temp.name)
        stats.strip_dirs()
        stats.sort_stats('time', 'calls')
        x =  '\n\ntook '+ str(stime) + ' seconds\n'
        x += capturestdout(stats.print_stats)(40)
        x += capturestdout(stats.print_callers)()
        return result, x

def tryall(context):
    context = context.copy() # vars() would update
    results = {}
    for (k, v) in context.iteritems():
        if not hasattr(v, '__call__'): continue
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
    def __init__(self, d): self.__dict__['_threadeddict__d'] = d
    def __getattr__(self, a): return getattr(self.__d[currentThread()], a)
    def __getitem__(self, i): return self.__d[currentThread()][i]
    def __setattr__(self, a, v): return setattr(self.__d[currentThread()], a, v)
    def __setitem__(self, i, v): self.__d[currentThread()][i] = v

## url utils

def base(base=''): #when would you use a default base?
    url = context.path.lstrip('/')
    for i in xrange(url.count('/')): base += '../'
    if not base: base = './'
    return base

## formatting

try:
    from markdown import markdown # http://webpy.org/markdown.py
except ImportError: pass

r_url = re_compile('(?<!\()(http://(\S+))')
def safemarkdown(text):
    if text:
        text = text.replace('<', '&lt;')
        # TODO: automatically get page title?
        text = r_url.sub(r'<\1>', text)
        text = markdown(text)
        return text

## db api

class UnknownParamstyle(Exception): pass
r_dbvar = re_compile(r'\B\$(\w+)')
def reparam(q):
    p = ctx.db_module.paramstyle
    if p == "pyformat":
        return r_dbvar.sub(r'%(\1)s', q)
    elif p == "named":
        return r_dbvar.sub(r':\1', q)
    raise UnknownParamstyle, p
    
def aparam():
    p = ctx.db_module.paramstyle
    if p == 'qmark':
        return '?'
    elif p == 'numeric':
        return ':1'
    elif p == 'format':
        return '%s'
    elif p == 'pyformat':
        return '%s'
    raise UnknownParamstyle, p

class UnknownDB(Exception): pass
def connect(dbn, **kw):
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
    else: raise UnknownDB, db
    ctx.db_name = dbn
    ctx.db_module = db
    ctx.db_transaction = False
    ctx.db = db.connect(**kw)
    ctx.dbc = ctx.db.cursor()
    return ctx.db

def transact():
    """Start a transaction."""
    # commit everything up to now, so we don't rollback it later
    ctx.db.commit()
    ctx.db_transaction = True

def commit():
    ctx.db.commit()
    ctx.db_transaction = False

def rollback():
    ctx.db.rollback()
    ctx.db_transaction = False

def query(q, v=None):
    d = ctx.dbc
    if v is None: v = upvars()

    d.execute(reparam(q), v)
    names = [x[0] for x in d.description]
    out = [Storage(dict(zip(names, x))) for x in d.fetchall()]
    
    if not ctx.db_transaction: ctx.db.commit()    
    return out

select = query

def insert(tablename, seqname=None, **values):
    d = ctx.dbc

    if values:
        d.execute("INSERT INTO %s (%s) VALUES (%s)" % (
            tablename,
            ", ".join(values.keys()),
            ', '.join([aparam() for x in values])
        ), values.values())
    else:
        d.execute("INSERT INTO %s DEFAULT VALUES" % tablename)

    if ctx.db_name == "postgres" and seqname != False: 
        if seqname is None: seqname = tablename + "_id_seq"
        d.execute("SELECT currval('%s')" % seqname)
        out = d.fetchone()[0]
    elif ctx.db_name == "mysql":
        d.execute("SELECT last_insert_id()")
        out = d.fetchone()[0]
    elif ctx.db_name == "sqlite":
        # not really the same...
        d.execute("SELECT last_insert_rowid()")
        out = d.fetchone()[0]
    else:
        out = None
    
    if not ctx.db_transaction: ctx.db.commit()
    return out

def update(tablename, where, pvars=(), **values):
    pvars = list(pvars)
    if isinstance(where, int):
        pvars.append(where)
        where = "id = "+aparam()
    else:
        where = where #@@ need to figure out positional params
    
    d = ctx.dbc
    d.execute("UPDATE %s SET %s WHERE %s" % (
        tablename,
        ', '.join([k+'='+aparam() for k in values.keys()]),
        where),
    values.values()+pvars)
    
    if not ctx.db_transaction: ctx.db.commit()        
    return d.rowcount

## request handlers

def handle(mapping, fvars=None):
    for url, ofn in group(mapping, 2):
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
            return tocall(*[urllib.unquote(x) for x in args])

    return notfound()

def autodelegate(prefix=''):
    def internal(self, arg):
        func = prefix+arg
        if hasattr(self, func): return getattr(self, func)()
        else: return notfound()
    return internal

## http defaults

def badrequest():
    context.status = '400 Bad Request'
    header('Content-Type', 'text/html')
    return output('bad request')

def notfound():
    context.status = '404 Not Found'
    header('Content-Type', 'text/html')
    return output('not found')

def nomethod(cls):
    context.status = '405 Method Not Allowed'
    header('Content-Type', 'text/html')
    header("Allow", ', '.join([x for x in ['GET', 'HEAD', 'POST', 'PUT', 'DELETE'] if hasattr(cls, x)]))
    return output('method not allowed')
    
def redirect(url):
    newloc = urlparse.urljoin(context.home + context.path, url)
    context.status = '301 Moved Permanently'
    header('Content-Type', 'text/html')
    header('Location', newloc)
    # seems to add a three-second delay for some reason:
    # output('<a href="'+ newloc + '">moved permanently</a>')

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
  <h2>Traceback <span>(innermost last)</span></h2>
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
              <a href='#' onclick="return varToggle(this, '$frame.id')"><span>&#x25b6;</span> Local vars</a><!--: $inspect.formatargvalues(*inspect.getargvalues(frame['tb'].tb_frame))-->
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
      #if not $key.startswith('_') and $key not in ['env', 'output', 'headers', 'environ', 'status']
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
    urljoin = urlparse.urljoin
    input_ = input()
    cookies_ = cookies()
    context_ = context
    prettify = pprint.pformat
    return render(DJANGO_500_PAGE, asTemplate=True, isString=True)

def internalerror():
    context.status = "500 Internal Server Error"
    context.headers = [('Context-Type', 'text/html')]
    context.output = "internal server error"

def debugerror():
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
    context.headers = [('Context-Type', 'text/html')]
    context.output = out


## rendering

r_include = re_compile(r'^\s*#include \"(.*?)\"$', re.M)
def __compiletemplate(template, base=None, isString=False):
    if isString: text = template
    else: text = open('templates/'+template).read()
    # implement #include at compile-time
    def do_include(match):
        text = open('templates/'+match.groups()[0]).read()
        return text
    while r_include.findall(text): text = r_include.sub(do_include, text)

    execspace = _compiletemplate.bases.copy()
    c = Compiler(source=text)
    c.addImportedVarNames(execspace.keys())
    exec str(c) in execspace
    if base: _compiletemplate.bases[base] = execspace['GenTemplate']

    return execspace['GenTemplate']

_compiletemplate = memoize(__compiletemplate)
_compiletemplate.bases = {}

def htmlquote(s):
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
    if not hasattr(context, '_inputfs'): context._inputfs = cgi.FieldStorage(fp = context.environ['wsgi.input'],environ=context.environ, keep_blank_values=1)
    return storify(context._inputfs, *requireds, **defaults)

## cookies

def setcookie(name, value, expires=""):
    if expires < 0: expires = -1000000000 
    kargs = {'expires': expires, 'path':'/'}
    # @@ should we limit cookies to a different path?
    c = Cookie.SimpleCookie()
    c[name] = value
    for key, val in kargs.iteritems(): c[name][key] = val
    header('Set-Cookie', c.items()[0][1].OutputString())

def cookies(*requireds, **defaults):
    c = Cookie.SimpleCookie()
    c.load(context.environ.get('HTTP_COOKIE', ''))
    return storify(c, *requireds, **defaults)

## WSGI Sugar

def header(h, v): context.headers.append((h, v))
def output(t): context.output += str(t)

def write(t):
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
    def wsgifunc(e, r):
        _load(e)
        func()
        status, headers, output = ctx.status, ctx.headers, ctx.output
        _unload()
        r(status, headers)
        if isinstance(output, str): output = [output]
        return output
    
    for x in middleware: wsgifunc = x(wsgifunc)
    
    return wsgifunc

def run(inp, *middleware):
    autoreload = reloader in middleware
    fvars = upvars()
    return runwsgi(wsgifunc(webpyfunc(inp, fvars, autoreload), *middleware))

def runwsgi(func):
    #@@ improve detection
    if (os.environ.has_key('PHP_FCGI_CHILDREN') #lighttpd fastcgi
      or os.environ.has_key('SERVER_SOFTWARE')): #cgi
        import flup.server.fcgi
        return runfcgi(func)

    # command line:
    return runsimple(func, listget(sys.argv, 1, 8080))
    
def runsimple(func, port=8080):
    # Copyright (c) 2004 Colin Stewart (http://www.owlfish.com/)
    # Modified somewhat for simplicity
    # Used under the modified BSD license:
    # http://www.xfree86.org/3.3.6/COPYRIGHT2.html#5

    import SimpleHTTPServer, SocketServer, BaseHTTPServer, urlparse
    import sys, logging, socket, errno
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
    

def runfcgi(func):
    from flup.server.fcgi import WSGIServer
    class MyServer(WSGIServer):            
        def error(self, req):
            w = req.stdout.write
            internalerror()
            w('Status: '+context.status+'\r\n')
            for (h, v) in context.headers:
                w(h+': '+v+'\r\n')
            w('\r\n'+context.output)
                
    return MyServer(func, multiplexed=True).run()

## debug

def debug(*args):
    for x in args:
        print >> context.environ['wsgi.errors'], pprint.pformat(x)
    return ''

# has to be a lambda so the context is evaluated at runtime
debug.write = lambda x: context.environ['wsgi.errors'].write(x)

class reloader:
    def __init__(self, func, tocheck=None): 
        self.func = func
        self.mtimes = {}
        global _compiletemplate
        _compiletemplate = globals()['__compiletemplate']
        _compiletemplate.bases = {}
    
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
    def profile_internal(e, o):
        out, result = profile(app)(e, o)
        return out + ['<pre>'+result+'</pre>'] #@@encode
    return profile_internal

## setting up the context

class _outputter:
    def write(self, x): 
        if hasattr(ctx, 'output'): output(x)
        else: _oldstdout.write(x)

_context = {currentThread():Storage()}
ctx = context = threadeddict(_context)

if not '_oldstdout' in globals(): 
    _oldstdout = sys.stdout
    sys.stdout = _outputter()

def _load(env):
    _context[currentThread()] = Storage()
    ctx.environ = ctx.env = env
    ctx.home = 'http://'+env.get('HTTP_HOST') + env.get('SCRIPT_NAME', '')
    ctx.ip = env.get('HTTP_X_FORWARDED_FOR') or env.get('REMOTE_ADDR')
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
            print open(__file__).read()
    run(urls)
