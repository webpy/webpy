"""
General Utilities
(part of web.py)
"""

__all__ = [
  "Storage", "storage", "storify", 
  "iters", 
  "rstrips", "lstrips", "strips", "utf8",
  "TimeoutError", "timelimit",
  "Memoize", "memoize",
  "re_compile", "re_subm",
  "group",
  "IterBetter", "iterbetter",
  "dictreverse", "dictfind", "dictfindall", "dictincr", "dictadd",
  "listget", "intget", "datestr",
  "numify", "denumify", "dateify",
  "CaptureStdout", "capturestdout", "Profile", "profile",
  "tryall",
  "ThreadedDict",
  "autoassign",
  "to36",
  "safemarkdown",
  "sendmail"
]

import re, sys, time, threading, os
try: import datetime
except ImportError: pass

class Storage(dict):
    """
    A Storage object is like a dictionary except `obj.foo` can be used
    in addition to `obj['foo']`.
    
        >>> o = storage(a=1)
        >>> o.a
        1
        >>> o['a']
        1
        >>> o.a = 2
        >>> o['a']
        2
        >>> del o.a
        >>> o.a
        Traceback (most recent call last):
            ...
        AttributeError: 'a'
    
    """
    def __getattr__(self, key): 
        try:
            return self[key]
        except KeyError, k:
            raise AttributeError, k
    
    def __setattr__(self, key, value): 
        self[key] = value
    
    def __delattr__(self, key):
        try:
            del self[key]
        except KeyError, k:
            raise AttributeError, k
    
    def __repr__(self):     
        return '<Storage ' + dict.__repr__(self) + '>'

storage = Storage

def storify(mapping, *requireds, **defaults):
    """
    Creates a `storage` object from dictionary `mapping`, raising `KeyError` if
    d doesn't have all of the keys in `requireds` and using the default 
    values for keys found in `defaults`.

    For example, `storify({'a':1, 'c':3}, b=2, c=0)` will return the equivalent of
    `storage({'a':1, 'b':2, 'c':3})`.
    
    If a `storify` value is a list (e.g. multiple values in a form submission), 
    `storify` returns the last element of the list, unless the key appears in 
    `defaults` as a list. Thus:
    
        >>> storify({'a':[1, 2]}).a
        2
        >>> storify({'a':[1, 2]}, a=[]).a
        [1, 2]
        >>> storify({'a':1}, a=[]).a
        [1]
        >>> storify({}, a=[]).a
        []
    
    Similarly, if the value has a `value` attribute, `storify will return _its_
    value, unless the key appears in `defaults` as a dictionary.
    
        >>> storify({'a':storage(value=1)}).a
        1
        >>> storify({'a':storage(value=1)}, a={}).a
        <Storage {'value': 1}>
        >>> storify({}, a={}).a
        {}
    
    """
    def getvalue(x):
        if hasattr(x, 'value'):
            return x.value
        else:
            return x
    
    stor = Storage()
    for key in requireds + tuple(mapping.keys()):
        value = mapping[key]
        if isinstance(value, list):
            if isinstance(defaults.get(key), list):
                value = [getvalue(x) for x in value]
            else:
                value = value[-1]
        if not isinstance(defaults.get(key), dict):
            value = getvalue(value)
        if isinstance(defaults.get(key), list) and not isinstance(value, list):
            value = [value]
        setattr(stor, key, value)

    for (key, value) in defaults.iteritems():
        result = value
        if hasattr(stor, key): 
            result = stor[key]
        if value == () and not isinstance(result, tuple): 
            result = (result,)
        setattr(stor, key, result)
    
    return stor

iters = [list, tuple]
import __builtin__
if hasattr(__builtin__, 'set'):
    iters.append(set)
try: 
    from sets import Set
    iters.append(Set)
except ImportError: 
    pass

class _hack(tuple): pass
iters = _hack(iters)
iters.__doc__ = """
A list of iterable items (like lists, but not strings). Includes whichever
of lists, tuples, sets, and Sets are available in this version of Python.
"""

def _strips(direction, text, remove):
    if direction == 'l': 
        if text.startswith(remove): 
            return text[len(remove):]
    elif direction == 'r':
        if text.endswith(remove):   
            return text[:-len(remove)]
    else: 
        raise ValueError, "Direction needs to be r or l."
    return text

def rstrips(text, remove):
    """
    removes the string `remove` from the right of `text`

        >>> rstrips("foobar", "bar")
        'foo'
    
    """
    return _strips('r', text, remove)

def lstrips(text, remove):
    """
    removes the string `remove` from the left of `text`
    
        >>> lstrips("foobar", "foo")
        'bar'
    
    """
    return _strips('l', text, remove)

def strips(text, remove):
    """removes the string `remove` from the both sides of `text`

        >>> strips("foobarfoo", "foo")
        'bar'
    
    """
    return rstrips(lstrips(text, remove), remove)

def utf8(text):
    """Encodes text in utf-8.
        
        >> utf8(u'\u1234') # doctest doesn't seem to like utf-8
        '\xe1\x88\xb4'

        >>> utf8('hello')
        'hello'
        >>> utf8(42)
        '42'
    """
    if isinstance(text, unicode):
        return text.encode('utf-8')
    elif isinstance(text, str):
        return text
    else:
        return str(text)

class TimeoutError(Exception): pass
def timelimit(timeout):
    """
    A decorator to limit a function to `timeout` seconds, raising `TimeoutError`
    if it takes longer.
    
        >>> import time
        >>> def meaningoflife():
        ...     time.sleep(.2)
        ...     return 42
        >>> 
        >>> timelimit(.1)(meaningoflife)()
        Traceback (most recent call last):
            ...
        TimeoutError: took too long
        >>> timelimit(1)(meaningoflife)()
        42

    _Caveat:_ The function isn't stopped after `timeout` seconds but continues 
    executing in a separate thread. (There seems to be no way to kill a thread.)

    inspired by <http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/473878>
    """
    def _1(function):
        def _2(*args, **kw):
            class Dispatch(threading.Thread):
                def __init__(self):
                    threading.Thread.__init__(self)
                    self.result = None
                    self.error = None

                    self.setDaemon(True)
                    self.start()

                def run(self):
                    try:
                        self.result = function(*args, **kw)
                    except:
                        self.error = sys.exc_info()

            c = Dispatch()
            c.join(timeout)
            if c.isAlive():
                raise TimeoutError, 'took too long'
            if c.error:
                raise c.error[0], c.error[1]
            return c.result
        return _2
    return _1

class Memoize:
    """
    'Memoizes' a function, caching its return values for each input.
    
        >>> import time
        >>> def meaningoflife():
        ...     time.sleep(.2)
        ...     return 42
        >>> fastlife = memoize(meaningoflife)
        >>> meaningoflife()
        42
        >>> timelimit(.1)(meaningoflife)()
        Traceback (most recent call last):
            ...
        TimeoutError: took too long
        >>> fastlife()
        42
        >>> timelimit(.1)(fastlife)()
        42
    
    """
    def __init__(self, func): 
        self.func = func
        self.cache = {}
    def __call__(self, *args, **keywords):
        key = (args, tuple(keywords.items()))
        if key not in self.cache: 
            self.cache[key] = self.func(*args, **keywords)
        return self.cache[key]

memoize = Memoize

re_compile = memoize(re.compile) #@@ threadsafe?
re_compile.__doc__ = """
A memoized version of re.compile.
"""

class _re_subm_proxy:
    def __init__(self): 
        self.match = None
    def __call__(self, match): 
        self.match = match
        return ''

def re_subm(pat, repl, string):
    """
    Like re.sub, but returns the replacement _and_ the match object.
    
        >>> t, m = re_subm('g(oo+)fball', r'f\\1lish', 'goooooofball')
        >>> t
        'foooooolish'
        >>> m.groups()
        ('oooooo',)
    """
    compiled_pat = re_compile(pat)
    proxy = _re_subm_proxy()
    compiled_pat.sub(proxy.__call__, string)
    return compiled_pat.sub(repl, string), proxy.match

def group(seq, size): 
    """
    Returns an iterator over a series of lists of length size from iterable.

        >>> list(group([1,2,3,4], 2))
        [[1, 2], [3, 4]]
    """
    if not hasattr(seq, 'next'):  
        seq = iter(seq)
    while True: 
        yield [seq.next() for i in xrange(size)]

class IterBetter:
    """
    Returns an object that can be used as an iterator 
    but can also be used via __getitem__ (although it 
    cannot go backwards -- that is, you cannot request 
    `iterbetter[0]` after requesting `iterbetter[1]`).
    
        >>> import itertools
        >>> c = iterbetter(itertools.count())
        >>> c[1]
        1
        >>> c[5]
        5
        >>> c[3]
        Traceback (most recent call last):
            ...
        IndexError: already passed 3
    """
    def __init__(self, iterator): 
        self.i, self.c = iterator, 0
    def __iter__(self): 
        while 1:    
            yield self.i.next()
            self.c += 1
    def __getitem__(self, i):
        #todo: slices
        if i < self.c: 
            raise IndexError, "already passed "+str(i)
        try:
            while i > self.c: 
                self.i.next()
                self.c += 1
            # now self.c == i
            self.c += 1
            return self.i.next()
        except StopIteration: 
            raise IndexError, str(i)
iterbetter = IterBetter

def dictreverse(mapping):
    """
        >>> dictreverse({1: 2, 3: 4})
        {2: 1, 4: 3}
    """
    return dict([(value, key) for (key, value) in mapping.iteritems()])

def dictfind(dictionary, element):
    """
    Returns a key whose value in `dictionary` is `element` 
    or, if none exists, None.
    
        >>> d = {1:2, 3:4}
        >>> dictfind(d, 4)
        3
        >>> dictfind(d, 5)
    """
    for (key, value) in dictionary.iteritems():
        if element is value: 
            return key

def dictfindall(dictionary, element):
    """
    Returns the keys whose values in `dictionary` are `element`
    or, if none exists, [].
    
        >>> d = {1:4, 3:4}
        >>> dictfindall(d, 4)
        [1, 3]
        >>> dictfindall(d, 5)
        []
    """
    res = []
    for (key, value) in dictionary.iteritems():
        if element is value:
            res.append(key)
    return res

def dictincr(dictionary, element):
    """
    Increments `element` in `dictionary`, 
    setting it to one if it doesn't exist.
    
        >>> d = {1:2, 3:4}
        >>> dictincr(d, 1)
        3
        >>> d[1]
        3
        >>> dictincr(d, 5)
        1
        >>> d[5]
        1
    """
    dictionary.setdefault(element, 0)
    dictionary[element] += 1
    return dictionary[element]

def dictadd(*dicts):
    """
    Returns a dictionary consisting of the keys in the argument dictionaries.
    If they share a key, the value from the last argument is used.
    
        >>> dictadd({1: 0, 2: 0}, {2: 1, 3: 1})
        {1: 0, 2: 1, 3: 1}
    """
    result = {}
    for dct in dicts:
        result.update(dct)
    return result

def listget(lst, ind, default=None):
    """
    Returns `lst[ind]` if it exists, `default` otherwise.
    
        >>> listget(['a'], 0)
        'a'
        >>> listget(['a'], 1)
        >>> listget(['a'], 1, 'b')
        'b'
    """
    if len(lst)-1 < ind: 
        return default
    return lst[ind]

def intget(integer, default=None):
    """
    Returns `integer` as an int or `default` if it can't.
    
        >>> intget('3')
        3
        >>> intget('3a')
        >>> intget('3a', 0)
        0
    """
    try:
        return int(integer)
    except (TypeError, ValueError):
        return default

def datestr(then, now=None):
    """
    Converts a (UTC) datetime object to a nice string representation.
    
        >>> from datetime import datetime, timedelta
        >>> d = datetime(1970, 5, 1)
        >>> datestr(d, now=d)
        '0 microseconds ago'
        >>> for t, v in {
        ...   timedelta(microseconds=1): '1 microsecond ago',
        ...   timedelta(microseconds=2): '2 microseconds ago',
        ...   -timedelta(microseconds=1): '1 microsecond from now',
        ...   -timedelta(microseconds=2): '2 microseconds from now',
        ...   timedelta(microseconds=2000): '2 milliseconds ago',
        ...   timedelta(seconds=2): '2 seconds ago',
        ...   timedelta(seconds=2*60): '2 minutes ago',
        ...   timedelta(seconds=2*60*60): '2 hours ago',
        ...   timedelta(days=2): '2 days ago',
        ... }.iteritems():
        ...     assert datestr(d, now=d+t) == v
        >>> datestr(datetime(1970, 1, 1), now=d)
        'January  1'
        >>> datestr(datetime(1969, 1, 1), now=d)
        'January  1, 1969'
        >>> datestr(datetime(1970, 6, 1), now=d)
        'June  1, 1970'
    """
    def agohence(n, what, divisor=None):
        if divisor: n = n // divisor

        out = str(abs(n)) + ' ' + what       # '2 day'
        if abs(n) != 1: out += 's'           # '2 days'
        out += ' '                           # '2 days '
        if n < 0:
            out += 'from now'
        else:
            out += 'ago'
        return out                           # '2 days ago'

    oneday = 24 * 60 * 60

    if not now: now = datetime.datetime.utcnow()
    if type(now).__name__ == "DateTime":
        now = datetime.datetime.fromtimestamp(now)
    if type(then).__name__ == "DateTime":
        then = datetime.datetime.fromtimestamp(then)
    delta = now - then
    deltaseconds = int(delta.days * oneday + delta.seconds + delta.microseconds * 1e-06)
    deltadays = abs(deltaseconds) // oneday
    if deltaseconds < 0: deltadays *= -1 # fix for oddity of floor

    if deltadays:
        if abs(deltadays) < 4:
            return agohence(deltadays, 'day')

        out = then.strftime('%B %e') # e.g. 'June 13'
        if then.year != now.year or deltadays < 0:
            out += ', %s' % then.year
        return out

    if int(deltaseconds):
        if abs(deltaseconds) > (60 * 60):
            return agohence(deltaseconds, 'hour', 60 * 60)
        elif abs(deltaseconds) > 60:
            return agohence(deltaseconds, 'minute', 60)
        else:
            return agohence(deltaseconds, 'second')

    deltamicroseconds = delta.microseconds
    if delta.days: deltamicroseconds = int(delta.microseconds - 1e6) # datetime oddity
    if abs(deltamicroseconds) > 1000:
        return agohence(deltamicroseconds, 'millisecond', 1000)

    return agohence(deltamicroseconds, 'microsecond')

def numify(string):
    """
    Removes all non-digit characters from `string`.
    
        >>> numify('800-555-1212')
        '8005551212'
        >>> numify('800.555.1212')
        '8005551212'
    
    """
    return ''.join([c for c in str(string) if c.isdigit()])

def denumify(string, pattern):
    """
    Formats `string` according to `pattern`, where the letter X gets replaced
    by characters from `string`.
    
        >>> denumify("8005551212", "(XXX) XXX-XXXX")
        '(800) 555-1212'
    
    """
    out = []
    for c in pattern:
        if c == "X":
            out.append(string[0])
            string = string[1:]
        else:
            out.append(c)
    return ''.join(out)

def dateify(datestring):
    """
    Formats a numified `datestring` properly.
    """
    return denumify(datestring, "XXXX-XX-XX XX:XX:XX")

class CaptureStdout:
    """
    Captures everything `func` prints to stdout and returns it instead.
    
        >>> def idiot():
        ...     print "foo"
        >>> capturestdout(idiot)()
        'foo\\n'
    
    **WARNING:** Not threadsafe!
    """
    def __init__(self, func): 
        self.func = func
    def __call__(self, *args, **keywords):
        from cStringIO import StringIO
        # Not threadsafe!
        out = StringIO()
        oldstdout = sys.stdout
        sys.stdout = out
        try: 
            self.func(*args, **keywords)
        finally: 
            sys.stdout = oldstdout
        return out.getvalue()

capturestdout = CaptureStdout

class Profile:
    """
    Profiles `func` and returns a tuple containing its output
    and a string with human-readable profiling information.
        
        >>> import time
        >>> out, inf = profile(time.sleep)(.001)
        >>> out
        >>> inf[:10].strip()
        'took 0.0'
    """
    def __init__(self, func): 
        self.func = func
    def __call__(self, *args): ##, **kw):   kw unused
        import hotshot, hotshot.stats, tempfile ##, time already imported
        temp = tempfile.NamedTemporaryFile()
        prof = hotshot.Profile(temp.name)

        stime = time.time()
        result = prof.runcall(self.func, *args)
        stime = time.time() - stime
        prof.close()

        def print_stats():
            stats = hotshot.stats.load(temp.name)
            stats.strip_dirs()
            stats.sort_stats('time', 'calls')
            stats.print_stats(40)
            stats.print_callers()
    
        x =  '\n\ntook '+ str(stime) + ' seconds\n'
        x += capturestdout(print_stats)()

        return result, x

profile = Profile


import traceback
# hack for compatibility with Python 2.3:
if not hasattr(traceback, 'format_exc'):
    from cStringIO import StringIO
    def format_exc(limit=None):
        strbuf = StringIO()
        traceback.print_exc(limit, strbuf)
        return strbuf.getvalue()
    traceback.format_exc = format_exc

def tryall(context, prefix=None):
    """
    Tries a series of functions and prints their results. 
    `context` is a dictionary mapping names to values; 
    the value will only be tried if it's callable.
    
        >>> tryall(dict(j=lambda: True))
        j: True
        ----------------------------------------
        results:
           True: 1

    For example, you might have a file `test/stuff.py` 
    with a series of functions testing various things in it. 
    At the bottom, have a line:

        if __name__ == "__main__": tryall(globals())

    Then you can run `python test/stuff.py` and get the results of 
    all the tests.
    """
    context = context.copy() # vars() would update
    results = {}
    for (key, value) in context.iteritems():
        if not hasattr(value, '__call__'): 
            continue
        if prefix and not key.startswith(prefix): 
            continue
        print key + ':',
        try:
            r = value()
            dictincr(results, r)
            print r
        except:
            print 'ERROR'
            dictincr(results, 'ERROR')
            print '   ' + '\n   '.join(traceback.format_exc().split('\n'))
        
    print '-'*40
    print 'results:'
    for (key, value) in results.iteritems():
        print ' '*2, str(key)+':', value

class ThreadedDict:
    """
    Takes a dictionary that maps threads to objects. 
    When a thread tries to get or set an attribute or item 
    of the threadeddict, it passes it on to the object 
    for that thread in dictionary.
    """
    def __init__(self, dictionary): 
        self.__dict__['_ThreadedDict__d'] = dictionary
    
    def __getattr__(self, attr): 
        return getattr(self.__d[threading.currentThread()], attr)
    
    def __getitem__(self, item): 
        return self.__d[threading.currentThread()][item]
    
    def __setattr__(self, attr, value):
        if attr == '__doc__':
            self.__dict__[attr] = value
        else:
            return setattr(self.__d[threading.currentThread()], attr, value)
    
    def __delattr__(self, item):
        try:
            del self.__d[threading.currentThread()][item]
        except KeyError, k:
            raise AttributeError, k
    
    def __delitem__(self, item):
        del self.__d[threading.currentThread()][item]
    
    def __setitem__(self, item, value): 
        self.__d[threading.currentThread()][item] = value
    
    def __hash__(self): 
        return hash(self.__d[threading.currentThread()])

threadeddict = ThreadedDict

def autoassign(self, locals):
    """
    Automatically assigns local variables to `self`.
    
        >>> self = storage()
        >>> autoassign(self, dict(a=1, b=2))
        >>> self
        <Storage {'a': 1, 'b': 2}>
    
    Generally used in `__init__` methods, as in:

        def __init__(self, foo, bar, baz=1): autoassign(self, locals())
    """
    for (key, value) in locals.iteritems():
        if key == 'self': 
            continue
        setattr(self, key, value)

def to36(q):
    """
    Converts an integer to base 36 (a useful scheme for human-sayable IDs).
    
        >>> to36(35)
        'z'
        >>> to36(119292)
        '2k1o'
        >>> int(to36(939387374), 36)
        939387374
        >>> to36(0)
        '0'
        >>> to36(-393)
        Traceback (most recent call last):
            ... 
        ValueError: must supply a positive integer
    
    """
    if q < 0: raise ValueError, "must supply a positive integer"
    letters = "0123456789abcdefghijklmnopqrstuvwxyz"
    converted = []
    while q != 0:
        q, r = divmod(q, 36)
        converted.insert(0, letters[r])
    return "".join(converted) or '0'


r_url = re_compile('(?<!\()(http://(\S+))')
def safemarkdown(text):
    """
    Converts text to HTML following the rules of Markdown, but blocking any
    outside HTML input, so that only the things supported by Markdown
    can be used. Also converts raw URLs to links.

    (requires [markdown.py](http://webpy.org/markdown.py))
    """
    from markdown import markdown
    if text:
        text = text.replace('<', '&lt;')
        # TODO: automatically get page title?
        text = r_url.sub(r'<\1>', text)
        text = markdown(text)
        return text

def sendmail(from_address, to_address, subject, message, headers=None, **kw):
    """
    Sends the email message `message` with mail and envelope headers
    for from `from_address_` to `to_address` with `subject`. 
    Additional email headers can be specified with the dictionary 
    `headers.

    If `web.config.smtp_server` is set, it will send the message
    to that SMTP server. Otherwise it will look for 
    `/usr/lib/sendmail`, the typical location for the sendmail-style
    binary.
    """
    try:
        import webapi
    except ImportError:
        webapi = Storage(config=Storage())
    
    if headers is None: headers = {}
    
    cc = kw.get('cc', [])
    bcc = kw.get('bcc', [])
    
    def listify(x):
        if not isinstance(x, list):
            return [x]
        else:
            return x

    to_address = listify(to_address)
    cc = listify(cc)
    bcc = listify(bcc)

    recipients = to_address + cc + bcc
    
    headers = dictadd({
      'MIME-Version': '1.0',
      'Content-Type': 'text/plain; charset=UTF-8',
      'Content-Disposition': 'inline',
      'From': from_address,
      'To': ", ".join(to_address),
      'Subject': subject
    }, headers)

    if cc:
        headers['Cc'] = ", ".join(cc)
    
    import email.Utils
    from_address = email.Utils.parseaddr(from_address)[1]
    recipients = [email.Utils.parseaddr(r)[1] for r in recipients]
    message = ('\n'.join(['%s: %s' % x for x in headers.iteritems()])
      + "\n\n" +  message)
    message = utf8(message)
    
    if webapi.config.get('smtp_server'):
        server = webapi.config.get('smtp_server')
        port = webapi.config.get('smtp_port', 0)
        username = webapi.config.get('smtp_username') 
        password = webapi.config.get('smtp_password')
        debug_level = webapi.config.get('smtp_debuglevel', None)
        starttls = webapi.config.get('smtp_starttls', False)

        import smtplib
        smtpserver = smtplib.SMTP(server, port)

        if debug_level:
            smtpserver.set_debuglevel(debug_level)

        if starttls:
            smtpserver.ehlo()
            smtpserver.starttls()
            smtpserver.ehlo()

        if username and password:
            smtpserver.login(username, password)

        smtpserver.sendmail(from_address, recipients, message)
        smtpserver.quit()
    else:
        assert not from_address.startswith('-'), 'security'
        for r in recipients:
            assert not r.startswith('-'), 'security'

        i, o = os.popen2(["/usr/lib/sendmail", '-f', from_address] + recipients)
        i.write(message)
        i.close()
        o.close()
        del i, o

if __name__ == "__main__":
    import doctest
    doctest.testmod()
