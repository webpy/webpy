"""
simple, elegant templating
(part of web.py)
"""

import re, glob, os, os.path
from types import FunctionType as function
from utils import storage, group
from net import websafe

# differences from python:
#  - for: has an optional else: that gets called if the loop never runs
# differences to add:
#  - you can use the expression inside if, while blocks
#  - special for loop attributes, like django?
#  - you can check to see if a variable is defined (perhaps w/ get func?)
# all these are probably good ideas for python...

# todo:
#  inline tuple
#  relax constraints on spacing
#  continue, break, etc.
#  tracebacks

global_globals = {'None':None, 'False':False, 'True': True}
MAX_ITERS = 100000

WHAT = 0
ARGS = 4
KWARGS = 6
NAME = 2
BODY = 4
CLAUSE = 2
ELIF = 6
ELSE = 8
IN = 6
NAME = 2
EXPR = 4
FILTER = 4
THING = 2
ATTR = 4
ITEM = 4
NEGATE = 4
X = 2
OP = 4
Y = 6
LINENO = -1

# http://docs.python.org/ref/identifiers.html
r_var = '[a-zA-Z_][a-zA-Z0-9_]*'

class ParseError(Exception): pass
class Parser:
    def __init__(self, text):
        self.t = text
        self.p = 0
        self._lock = [False]
    
    def lock(self):
        self._lock[-1] = True
    
    def curline(self):
        return self.t[:self.p].count('\n')+1
        
    def csome(self):
        return repr(self.t[self.p:self.p+5]+'...')

    def Error(self, x, y=None):
        if y is None: y = self.csome()
        raise ParseError, "expected %s, got %s (line %s)" % (x, y, self.curline())
    
    def q(self, f):
        def internal(*a, **kw):
            checkp = self.p
            self._lock.append(False)
            try:
                q = f(*a, **kw)
            except ParseError:
                if self._lock[-1]:
                    raise
                self.p = checkp
                self._lock.pop()
                return False
            self._lock.pop()
            return q or True
        return internal
    
    def tokr(self, t): 
        text = self.c(len(t))
        if text != t:
            self.Error(repr(t), repr(text))
        return t
    
    def ltokr(self, *l):
        for x in l:
            o = self.tokq(x)
            if o: return o
        self.Error('one of '+repr(l))
    
    def rer(self, r):
        x = re.match(r, self.t[self.p:]) #@@re_compile
        if not x:
            self.Error('r'+repr(r))
        return self.tokr(x.group())
    
    def endr(self):
        if self.p != len(self.t):
            self.Error('EOF')
        
    def c(self, n=1):
        out = self.t[self.p:self.p+n]
        if out == '' and n != 0:
            self.Error('character', 'EOF')
        self.p += n
        return out

    def lookbehind(self, t):
        return self.t[self.p-len(t):self.p] == t
    
    def __getattr__(self, a):
        if a.endswith('q'):
            return self.q(getattr(self, a[:-1]+'r'))
        raise AttributeError, a

class TemplateParser(Parser):
    def __init__(self, *a, **kw):
        Parser.__init__(self, *a, **kw)
        self.curws = ''
        self.curind = ''
        
    def o(self, *a):
        return a+('lineno', self.curline())
    
    def go(self): 
        # maybe try to do some traceback parsing/hacking
        return self.gor()
    
    def gor(self):
        header = self.defwithq()
        results = self.lines(start=True)
        self.endr()
        return header, results
    
    def ws(self):
        n = 0
        while self.tokq(" "): n += 1
        return " " * n
    
    def defwithr(self):
        self.tokr('$def with ')
        self.lock()
        self.tokr('(')
        args = []
        kw = []
        x = self.req(r_var)
        while x:
            if self.tokq('='):
                v = self.exprr()
                kw.append((x, v))
            else: 
                args.append(x)
            x = self.tokq(', ') and self.req(r_var)
        self.tokr(')\n')
        return self.o('defwith', 'null', None, 'args', args, 'kwargs', kw)
    
    def literalr(self):
        o = (
          self.req('"[^"]*"') or #@@ no support for escapes
          self.req("'[^']*'")
        )
        if o is False:
            o = self.req('\-?[0-9]+(\.[0-9]*)?')
            if o is not False:
                if '.' in o: o = float(o)
                else: o = int(o)

        if o is False: self.Error('literal')
        return self.o('literal', 'thing', o)
    
    def listr(self):
        self.tokr('[')
        self.lock()
        x = []
        if not self.tokq(']'):
            while True:
                t = self.exprr()
                x.append(t)
                if not self.tokq(', '): break
            self.tokr(']')
        return self.o('list', 'thing', x)
    
    def dictr(self):
        self.tokr('{')
        self.lock()
        x = {}
        if not self.tokq('}'):
            while True:
                k = self.exprr()
                self.tokr(': ')
                v = self.exprr()
                x[k] = v
                if not self.tokq(', '): break
            self.tokr('}')
        return self.o('dict', 'thing', x)

    def parenr(self):
        self.tokr('(')
        self.lock()
        o = self.exprr() # todo: allow list
        self.tokr(')')
        return self.o('paren', 'thing', o)
    
    def atomr(self):
        """returns var, literal, paren, dict, or list"""
        o = (
          self.varq() or 
          self.parenq() or
          self.dictq() or
          self.listq() or
          self.literalq()
        )
        if o is False: self.Error('atom')
        return o
        
    def primaryr(self):
        """returns getattr, call, or getitem"""        
        n = self.atomr()
        while 1:
            if self.tokq('.'):
                v = self.req(r_var)
                if not v:
                    self.p -= 1 # get rid of the '.'
                    break
                else:
                    n = self.o('getattr', 'thing', n, 'attr', v)
            elif self.tokq('('):
                args = []
                kw = []
                
                while 1:
                    # need to see if we're doing a keyword argument
                    checkp = self.p
                    k = self.req(r_var)
                    if k and self.tokq('='): # yup
                        v = self.exprr()
                        kw.append((k, v))
                    else:
                        self.p = checkp
                        x = self.exprq()
                        if x: # at least it's something
                            args.append(x)
                        else:
                            break
                            
                    if not self.tokq(', '): break
                self.tokr(')')
                n = self.o('call', 'thing', n, 'args', args, 'kwargs', kw)
            elif self.tokq('['):
                v = self.exprr()
                self.tokr(']')
                n = self.o('getitem', 'thing', n, 'item', v)
            else:
                break
        
        return n
    
    def exprr(self):
        negate = self.tokq('not ')
        x = self.primaryr()
        if self.tokq(' '):
            operator = self.ltokr('not in', 'in', 'is not', 'is', '==', '!=', '>=', '<=', '<', '>', 'and', 'or', '*', '+', '-', '/', '%')
            self.tokr(' ')
            y = self.exprr()
            x = self.o('test', 'x', x, 'op', operator, 'y', y)
        
        return self.o('expr', 'thing', x, 'negate', negate)

    def varr(self):
        return self.o('var', 'name', self.rer(r_var))
    
    def liner(self):
        out = []
        o = self.curws
        while 1:
            c = self.c()
            self.lock()
            if c == '\n':
                self.p -= 1
                break
            if c == '$':
                if self.lookbehind('\\$'):
                    o = o[:-1] + c
                else:
                    filter = not bool(self.tokq(':'))
                    
                    if self.tokq('{'):
                        out.append(o)
                        out.append(self.o('itpl', 'name', self.exprr(), 'filter', filter))
                        self.tokr('}')
                        o = ''
                    else:
                        g = self.primaryq()
                        if g: 
                            out.append(o)
                            out.append(self.o('itpl', 'name', g, 'filter', filter))
                            o = ''
                        else:
                            o += c
            else:
                o += c
        self.tokr('\n')
        if not self.lookbehind('\\\n'):
            o += '\n'
        else:
            o = o[:-1]
        out.append(o)
        return self.o('line', 'thing', out)
    
    def varsetr(self):
        self.tokr('$var ')
        self.lock()
        what = self.rer(r_var)
        self.tokr(':')
        body = self.lines()
        return self.o('varset', 'name', what, 'body', body)

    def ifr(self):
        self.tokr("$if ")
        self.lock()
        expr = self.exprr()
        self.tokr(":")
        ifc = self.lines()
        
        elifs = []
        while self.tokq(self.curws + self.curind + '$elif '):
            v = self.exprr()
            self.tokr(':')
            c = self.lines()
            elifs.append(self.o('elif', 'clause', v, 'body', c))
        
        if self.tokq(self.curws + self.curind + "$else:"):
            elsec = self.lines()
        else:
            elsec = None
        
        return self.o('if', 'clause', expr, 'then', ifc, 'elif', elifs, 'else', elsec)
    
    def forr(self):
        self.tokr("$for ")
        self.lock()
        v = self.setabler()
        self.tokr(" in ")
        g = self.exprr()
        self.tokr(":")
        l = self.lines()

        if self.tokq(self.curws + self.curind + '$else:'):
            elsec = self.lines()
        else:
            elsec = None
        
        return self.o('for', 'name', v, 'body', l, 'in', g, 'else', elsec)
    
    def whiler(self):
        self.tokr('$while ')
        self.lock()
        v = self.exprr()
        self.tokr(":")
        l = self.lines()
        
        if self.tokq(self.curws + self.curind + '$else:'):
            elsec = self.lines()
        else:
            elsec = None
        
        return self.o('while', 'clause', v, 'body', l, 'null', None, 'else', elsec)
    
    def assignr(self):
        self.tokr('$ ')
        assign = self.rer(r_var) # NOTE: setable
        self.tokr(' = ')
        expr = self.exprr()
        self.tokr('\n')
        
        return self.o('assign', 'name', assign, 'expr', expr)
        
    def commentr(self):
        self.tokr('$#')
        self.lock()
        while self.c() != '\n': pass
        return self.o('comment')
        
    def setabler(self):
        out = [self.varr()] #@@ not quite right
        while self.tokq(', '):
             out.append(self.varr())
        return out
    
    def lines(self, start=False):
        """
        This function gets called from two places:
          1. at the start, where it's matching the document itself
          2. after any command, where it matches one line or an indented block
        """
        o = []
        if not start: # try to match just one line
            singleline = self.tokq(' ') and self.lineq()
            if singleline:
                return [singleline]
            else:
                self.rer(' *') #@@slurp space?
                self.tokr('\n')
                oldind = self.curind
                self.curind += '    '
        while 1:
            oldws = self.curws
            t = self.tokq(oldws + self.curind)
            if not t: break
            
            self.curws += self.ws()
            x = t and (
              self.varsetq() or 
              self.ifq() or 
              self.forq() or 
              self.whileq() or 
              self.assignq() or
              self.commentq() or
              self.lineq())
            self.curws = oldws
            if not x:
                break
            elif x[WHAT] == 'comment':
                pass
            else:
                o.append(x)

        if not start: self.curind = oldind
        return o
    
class Stowage(storage):
    def __str__(self): return self.get('_str')
    #@@ edits in place
    def __add__(self, other):
        if isinstance(other, (unicode, str)):
            self._str += other
            return self
        else:
            raise TypeError, 'cannot add'
    def __radd__(self, other):
        if isinstance(other, (unicode, str)):
            self._str = other + self._str
            return self
        else:
            raise TypeError, 'cannot add'
    
class WTF(AssertionError): pass
class SecurityError(Exception):
    """The template seems to be trying to do something naughty."""
    pass

Required = object()
class Template:
    globals = {}
    def __init__(self, text, filter=None):
        self.filter = filter
        # universal newlines:
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        if not text.endswith('\n'): text += '\n'
        header, tree = TemplateParser(text).go()
        self.tree = tree
        if header:
            self.h_defwith(header)
        else:
            self.args, self.kwargs = (), {}
    
    def __call__(self, *a, **kw):
        d = self.globals.copy()
        d.update(self._parseargs(a, kw))
        f = Fill(self.tree, d=d)
        if self.filter: f.filter = self.filter
        return f.go()
    
    def _parseargs(self, inargs, inkwargs):
        # difference from Python:
        #   no error on setting a keyword arg twice
        d = {}
        for arg in self.args:
            d[arg] = Required
        for kw, val in self.kwargs:
            d[kw] = val

        for n, val in enumerate(inargs):
            if n < len(self.args):
                d[self.args[n]] = val
            elif n < len(self.args)+len(self.kwargs):
                kw = self.kwargs[n - len(self.args)][0]
                d[kw] = val

        for kw, val in inkwargs.iteritems():
            d[kw] = val

        unset = []
        for k, v in d.iteritems():
            if v is Required:
                unset.append(k)
        if unset:
            raise TypeError, 'values for %s are required' % unset 

        return d
    
    def h_defwith(self, header):
        assert header[WHAT] == 'defwith'
        f = Fill(self.tree, d={})

        self.args = header[ARGS]
        self.kwargs = []
        for var, valexpr in header[KWARGS]:
            self.kwargs.append((var, f.h(valexpr)))

class Handle:
    def __init__(self, parsetree, **kw):
        self._funccache = {}
        self.parsetree = parsetree
        for (k, v) in kw.iteritems(): setattr(self, k, v)    
    
    def h(self, item):
        return getattr(self, 'h_' + item[WHAT])(item)
        
class Fill(Handle):
    builtins = global_globals
    def filter(self, text):
        if text is None: return ''
        else: return str(text)
        # later: can do stuff like WebSafe
    
    def h_literal(self, i):
        item = i[THING]
        if isinstance(item, str) and item[0] in ['"', "'"]:
            item = item[1:-1]
        elif isinstance(item, (float, int)):
            pass
        return item
    
    def h_list(self, i):
        x = i[THING]
        out = []
        for item in x:
            out.append(self.h(item))
        return out
    
    def h_dict(self, i):
        x = i[THING]
        out = {}
        for k, v in x.iteritems():
            out[self.h(k)] = self.h(v)
        return out
    
    def h_paren(self, i):
        item = i[THING]
        if isinstance(item, list):
            raise NotImplementedError, 'tuples'
        return self.h(item)
    
    def h_getattr(self, i):
        thing, attr = i[THING], i[ATTR]
        thing = self.h(thing)
        if attr.startswith('_') or attr.startswith('func_') or attr.startswith('im_'):
            raise SecurityError, 'tried to get ' + attr
        try:
            if thing in self.builtins:
                raise SecurityError, 'tried to getattr on ' + repr(thing)
        except TypeError:
            pass # raised when testing an unhashable object
        try:
            return getattr(thing, attr)
        except AttributeError:
            if isinstance(thing, list) and attr == 'join':
                return lambda s: s.join(thing)
            else:
                raise
    
    def h_call(self, i):
        call = self.h(i[THING])
        args = [self.h(x) for x in i[ARGS]]
        kw = dict([(x, self.h(y)) for (x, y) in i[KWARGS]])
        return call(*args, **kw)
    
    def h_getitem(self, i):
        thing, item = i[THING], i[ITEM]
        thing = self.h(thing)
        item = self.h(item)
        return thing[item]
    
    def h_expr(self, i):
        item = self.h(i[THING])
        if i[NEGATE]:
            item = not item
        return item
    
    def h_test(self, item):
        ox, op, oy = item[X], item[OP], item[Y]
        # for short-circuiting to work, we can't eval these here
        e = self.h
        if op == 'is':
            return e(ox) is e(oy)
        elif op == 'is not':
            return e(ox) is not e(oy)
        elif op == 'in':
            return e(ox) in e(oy)
        elif op == 'not in':
            return e(ox) not in e(oy)
        elif op == '==':
            return e(ox) == e(oy)
        elif op == '!=':
            return e(ox) != e(oy)
        elif op == '>':
            return e(ox) > e(oy)
        elif op == '<':
            return e(ox) < e(oy)
        elif op == '<=':
            return e(ox) <= e(oy)
        elif op == '>=':
            return e(ox) >= e(oy)
        elif op == 'and':
            return e(ox) and e(oy)
        elif op == 'or':
            return e(ox) or e(oy)
        elif op == '+':
            return e(ox) + e(oy)
        elif op == '-':
            return e(ox) - e(oy)
        elif op == '*':
            return e(ox) * e(oy)
        elif op == '/':
            return e(ox) / e(oy)
        elif op == '%':
            return e(ox) % e(oy)
        else:
            raise WTF, 'op ' + op
    
    def h_var(self, i):
        v = i[NAME]
        if v in self.d:
            return self.d[v]
        elif v in self.builtins:
            return self.builtins[v]
        elif v == 'self':
            return self.output
        else:
            raise NameError, 'could not find %s (line %s)' % (repr(i[NAME]), i[LINENO])
        
    def h_line(self, i):
        out = []
        for x in i[THING]:
            if isinstance(x, str):
                out.append(x)
            elif x[WHAT] == 'itpl':
                o = self.h(x[NAME])
                if x[FILTER]:
                    o = self.filter(o)
                else:
                    if isinstance(o, Stowage):
                        o = o._str
                out.append(o)
            else:
                raise WTF, x
        return ''.join(out)
    
    def h_varset(self, i):
        self.output[i[NAME]] = ''.join(self.h_lines(i[BODY]))
        return ''

    def h_if(self, i):
        expr = self.h(i[CLAUSE])
        if expr:
            do = i[BODY]
        else:
            for e in i[ELIF]:
                expr = self.h(e[CLAUSE])
                if expr:
                    do = e[BODY]
                    break
            else:
                do = i[ELSE]
        return ''.join(self.h_lines(do))
        
    def h_for(self, i):
        out = []
        assert i[IN][WHAT] == 'expr'
        invar = self.h(i[IN])
        forvar = i[NAME]
        if invar:
            for nv in invar:
                if len(forvar) == 1:
                    fv = forvar[0]
                    assert fv[WHAT] == 'var'
                    self.d[fv[NAME]] = nv # same (lack of) scoping as Python
                else:
                    for x, y in zip(forvar, nv):
                        assert x[WHAT] == 'var'
                        self.d[x[NAME]] = y
                
                out.extend(self.h_lines(i[BODY]))
        else:
            if i[ELSE]:
                out.extend(self.h_lines(i[ELSE]))
        return ''.join(out)
    
    def h_while(self, i):
        out = []
        expr = self.h(i[CLAUSE])
        if not expr:
            return ''.join(self.h_lines(i[ELSE]))
        c = 0
        while expr:
            c += 1
            if c >= MAX_ITERS:
                raise RuntimeError, 'too many while-loop iterations (line %s)' % i[LINENO]
            out.extend(self.h_lines(i[BODY]))
            expr = self.h(i[CLAUSE])
        return ''.join(out)

    def h_assign(self, i):
        self.d[i[NAME]] = self.h(i[EXPR])
        return ''

    def h_comment(self, i): pass
    
    def h_lines(self, lines):
        if lines is None: return []
        return map(self.h, lines)
    
    def go(self):
        self.output = Stowage()
        self.output._str = ''.join(map(self.h, self.parsetree))
        if self.output.keys() == ['_str']:
            self.output = self.output['_str']
        return self.output

class render:
    def __init__(self, loc='templates/', cache=True):
        self.loc = loc
        if cache:
            self.cache = {}
        else:
            self.cache = False
    
    def _do(self, name, filter=None):
        if self.cache is False or name not in self.cache:
            p = glob.glob(self.loc + name + '.*')
            if not p and os.path.isdir(self.loc + name):
                return render(self.loc + name + '/', cache=self.cache)
            elif not p:
                raise AttributeError, 'no template named ' + name
            p = p[0]
            c = Template(open(p).read())
            if self.cache is not False: self.cache[name] = (p, c)
        
        if self.cache is not False: p, c = self.cache[name]

        if p.endswith('.html'):
            import webapi as web
            if 'headers' in web.ctx:
                web.header('Content-Type', 'text/html; charset=utf-8', unique=True)
            if not filter: c.filter = websafe
        elif p.endswith('.xml'):
            if not filter: c.filter = websafe
        
        return c

    def __getattr__(self, p):
        return self._do(p)

def frender(fn, *a, **kw):
    return Template(open(fn).read(), *a, **kw)

def test():
    import sys
    verbose = '-v' in sys.argv
    def assertEqual(a, b):
        if a == b:
            if verbose:
                sys.stderr.write('.')
                sys.stderr.flush()
        else:
            assert a == b, "\nexpected: %s\ngot: %s" % (repr(b), repr(a))
    
    from utils import storage, group
    t = Template

    tests = [
        lambda: t('1')(),                                                   '1\n',
        lambda: t('$def with ()\n1')(),                                     '1\n',
        lambda: t('$def with (a)\n$a')(1),                                  '1\n',
        lambda: t('$def with (a=0)\n$a')(1),                                '1\n',
        lambda: t('$def with (a=0)\n$a')(a=1),                              '1\n',
        lambda: t('$if 1: 1')(),                                            '1\n',
        lambda: t('$if 1:\n    1')(),                                       '1\n',
        lambda: t('$if 0: 0\n$elif 1: 1')(),                                '1\n',
        lambda: t('$if 0: 0\n$elif None: 0\n$else: 1')(),                   '1\n',
        lambda: t('$if (0 < 1) and (1 < 2): 1')(),                          '1\n',
        lambda: t('$for x in [1, 2, 3]: $x')(),                             '1\n2\n3\n',
        lambda: t('$for x in []: 0\n$else: 1')(),                           '1\n',
        lambda: t('$def with (a)\n$while a and a.pop(): 1')([1, 2, 3]),     '1\n1\n1\n',
        lambda: t('$while 0: 0\n$else: 1')(),                               '1\n',
        lambda: t('$ a = 1\n$a')(),                                         '1\n',
        lambda: t('$# 0')(),                                                '',
        lambda: t('$def with (d)\n$for k, v in d.iteritems(): $k')({1: 1}), '1\n',
        lambda: t('$def with (a)\n$(a)')(1),                                '1\n',
        lambda: t('$def with (a)\n$a')(1),                                  '1\n',
        lambda: t('$def with (a)\n$a.b')(storage(b=1)),                     '1\n',
        lambda: t('$def with (a)\n$a[0]')([1]),                             '1\n',
        lambda: t('${0 or 1}')(),                                           '1\n',
        lambda: t('$ a = [1]\n$a[0]')(),                                    '1\n',
        lambda: t('$ a = {1: 1}\n$a.keys()[0]')(),                          '1\n',
        lambda: t('$ a = []\n$if not a: 1')(),                              '1\n',
        lambda: t('$ a = {}\n$if not a: 1')(),                              '1\n',
        lambda: t('$ a = -1\n$a')(),                                        '-1\n',
        lambda: t('$ a = "1"\n$a')(),                                       '1\n',
        lambda: t('$if 1 is 1: 1')(),                                       '1\n',
        lambda: t('$if not 0: 1')(),                                        '1\n',
        lambda: t('$if 1:\n    $if 1: 1')(),                                '1\n',
        lambda: t('$ a = 1\n$a')(),                                         '1\n',
        lambda: t('$ a = 1.\n$a')(),                                        '1.0\n',
        lambda: t('$({1: 1}.keys()[0])')(),                                 '1\n',
    ]

    for func, value in group(tests, 2):
        assertEqual(func(), value)

    j = Template("$var foo: bar")()
    assertEqual(str(j), '')
    assertEqual(j.foo, 'bar\n')
    if verbose: sys.stderr.write('\n')
    

if __name__ == "__main__":
    test()
