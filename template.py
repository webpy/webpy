"""template.py: simple, elegant templating"""
__author__ = "Aaron Swartz <me@aaronsw.com>"
__version__ = .001 # only half-written

from web import storage, group
import re
# differences from python:
#  - you can use the expression inside if, while blocks
#  - special for loop attributes, like django?
#  - you can check to see if a variable is defined (perhaps w/ get func?)
#  - for: has an optional else: 
# all these are probably good ideas for python...

# todo:
#  setting things
#  continue, break, etc.
#  nested blocks (for within if, etc.)
#  better getable, expr support
#    inline arrays, tuples, dictionaries
#  code blocks
#  tracebacks

MAX_ITERS = 100000

# http://docs.python.org/ref/identifiers.html
r_var = '[a-zA-Z_][a-zA-Z0-9_]*'

class ParseError(Exception): pass
class Parser:
    def __init__(_, text):
        _.t = text
        _.p = 0
        _._lock = [False]
    
    def lock(_):
        _._lock[-1] = True
    
    def curline(_):
        return _.t[:_.p].count('\n')+1
        
    def csome(_):
        return repr(_.t[_.p:_.p+5]+'...')

    def Error(_, x, y=None):
        if y is None: y = _.csome()
        raise ParseError, "expected %s, got %s (line %s)" % (x, y, _.curline())
    
    def q(_, f):
        def internal(*a, **kw):
            checkp = _.p
            _._lock.append(False)
            try:
                q = f(*a, **kw)
            except ParseError:
                if _._lock[-1]:
                    raise
                _.p = checkp
                _._lock.pop()
                return False
            _._lock.pop()
            return q or True
        return internal
    
    def tokr(_, t): 
        text = _.c(len(t))
        if text != t:
            _.Error(repr(t), repr(text))
        return t
    
    def rer(_, r):
        x = re.match(r, _.t[_.p:]) #@@re_compile
        if not x:
            _.Error('r'+repr(r))
        return _.tokr(x.group())
    
    def endr(_):
        if _.p != len(_.t):
            _.Error('EOF')
        
    def c(_, n=1):
        out = _.t[_.p:_.p+n]
        if out == '' and n != 0:
            _.Error('character', 'EOF')
        _.p += n
        return out

    def lookbehind(_, t):
        return _.t[_.p-len(t):_.p] == t
    
    def __getattr__(self, a):
        if a.endswith('q'):
            return self.q(getattr(self, a[:-1]+'r'))
        raise AttributeError, a

class TemplateParser(Parser):
    def o(_, *a):
        return a+('lineno', _.curline())
    
    def go(_): 
        # maybe try to do some traceback parsing/hacking
        return _.gor()
    
    def gor(_):
        header = _.defwithq()

        results = []
        while 1:
            ws = _.ws()
            x = (
              _.setq(ws) or 
              _.ifq(ws) or 
              _.forq(ws) or 
              _.whileq(ws) or 
#              _.assignq() or
              _.lineq('', 0, prefix=ws))
            if not x: break
            results.append(x)
        _.endr()
        return header, results
    
    def ws(_):
        n = 0
        while _.tokq(" "): n += 1
        return " " * n
    
    def defwithr(_):
        _.tokr('$def with ')
        _.lock()
        _.tokr('(')
        args = []
        kw = []
        x = _.varq() # NOTE: just rer
        while x:
            if _.tokq('='):
                v = _.exprr()
                kw.append((x[1], v))
            else: 
                args.append(x[1])
            x = _.tokq(', ') and _.varq() # NOTE: ditto
        _.tokr(')\n')
        return _.o('defwith', args, kw)

    def setr(_, ws):
        _.tokr('$set ')
        _.lock()
        what = _.varr() # NOTE: just rer
        _.tokr(':')
        body = _.lines(ws)
        return _.o('set', what, 'body', body)

    def ifr(_, ws):
        _.tokr("$if ")
        _.lock()
        expr = _.exprr()
        _.tokr(":")
        ifc = _.lines(ws)
        
        elifs = []
        while _.tokq(ws+'$elif '):
            v = _.exprr()
            _.tokr(':')
            c = _.lines(ws)
            elifs.append(('expr', v, 'code', c))
        
        if _.tokq(ws+"$else:"): elsec = _.lines(ws)
        else: elsec = None
        
        return _.o('if', expr, 'then', ifc, 'elif', elifs, 'else', elsec)
    
    def forr(_, ws):
        _.tokr("$for ")
        _.lock()
        v = _.varr() # NOTE: setable
        _.tokr(" in ")
        g = _.exprr()
        _.tokr(":")
        l = _.lines(ws)

        if _.tokq(ws+'$else:'): elsec = _.lines(ws)
        else: elsec = None
            
        return _.o('for', v, 'in', g, 'do', l, 'else', elsec)
    
    def whiler(_, ws):
        _.tokr('$while ')
        _.lock()
        v = _.exprr()
        _.tokr(":")
        l = _.lines(ws)
        
        if _.tokq(ws+'$else:'): elsec = _.lines(ws)
        else: elsec = None
        
        return _.o('while', v, 'do', l, 'else', elsec)
    
    def assigner(_, ws):
        _.tokr('$ ')
        _.varr() # NOTE: setable
        
    def varr(_):
        return _.o('var', _.rer(r_var))
    
    def getabler(_):
        if _.tokq('('):
            parens = True
        else:
            parens = False
        
        #var ["." var]+
        n = _.varr()
        while 1:
            if _.tokq('.'):
                v = _.varq()
                if not v:
                    _.p -= 1 # get rid of the '.'
                else:
                    n = ('getattr', n, v)
            elif _.tokq('('):
                args = []
                kw = []
                x = _.exprr()
                while x:
                    if _.tokq('='):
                        v = _.exprr()
                        kw.append((x[1], v))
                    else: 
                        args.append(x)
                    x = _.tokq(', ') and _.exprq()
                _.tokr(')')
                n = ('call', n, 'args', args, 'kw', kw)
            else:
                break
        
        if parens: _.tokr(')')
        return _.o('getable', n)
    
    def lines(_, ws, ilevel=4):
        o = []
        fl = _.lineq('', 1, ws)
        if fl: 
            o.append(fl)
            return o
        else:
            _.rer(' *')
            _.tokr('\n')
        
        while 1:
            p = _.lineq(ws, ilevel)
            if not p: break
            o.append(p)
        return o
    
    def liner(_, ws, ilevel, prefix=''):
        out = [prefix]
        o = ''
        _.tokr(ws+' '*ilevel)
        o += ws
        while 1:
            c = _.c()
            _.lock() # OK, since everything else tried first
            if c == '\n': _.p -= 1; break
            if c == '$':
                if _.lookbehind('\\$'):
                    o = o[:-1] + c
                else:
                    out.append(o)
                    if _.tokq('{'):
                        out.append(_.exprr())
                        _.tokr('}')
                    else:
                        out.append(_.getabler())
                    o = ''
            else:
                o += c
        _.tokr('\n')
        if not _.lookbehind('\\\n'):
            o += '\n'
        else:
            o = o[:-1]
        out.append(o)
        return _.o('line', out)
    
    def exprr(_):
        x = (
          _.getableq() or 
          _.req('[0-9]+') or 
          _.req('"[^"]*"') or #@@ no support for escapes
          _.req("'[^']*'"))
        if not x:
            _.Error('expression')
        return _.o('expr', x)

def itemize(item):
    return storage(dict(group(item, 2)))

class Stowage(storage):
    def __str__(self): return self.get('_str')

class WTF(AssertionError): pass

class Handle:
    def __init__(self, parsetree, **kw):
        self.parsetree = parsetree
        for (k, v) in kw.iteritems(): setattr(self, k, v)    
    
    def h(self, item):
        return getattr(self, 'h_'+item[0])(itemize(item))
            
class Fill(Handle):
    def filter(self, text):
        if text == None: return ''
        else: return str(text)
        # later: can do stuff like WebSafe
    
    def h_expr(self, item):
        assert item[0] == 'expr'
        item = item[1]
        if isinstance(item, str) and item.isdigit():
            item = int(item)
        elif isinstance(item, str) and item[0] in ['"', "'"]:
            item = item[1:-1]
        elif item[0] == 'getable':
            item = self.h_getable(item[1])
        else:
            raise WTF, item
        return item
    
    def h_var(self, i):
        assert i[0] == 'var'
        try:
            return self.d[i[1]]
        except KeyError:
            i = itemize(i)
            raise NameError, 'could not find %s (line %s)' % (repr(i.var), i.lineno)
    
    def h_getable(self, i):
        if i[0] == 'expr':
            out = self.h_expr(i)
        elif i[0] == 'var':
            out = self.h_var(i)
        elif i[0] == 'getattr':
            what, attr = i[1:]
            assert attr[0] == 'var'
            out = getattr(self.h_getable(what), attr[1])
        elif i[0] == 'call':
            i = itemize(i)
            call = self.h_getable(i.call)
            args = [self.h_getable(x) for x in i.args]
            kw = dict([(x, self.h_getable(y)) for (x, y) in i.kw])
            out = call(*args, **kw)
        else:
            raise WTF, i
        return out
        
    def h_line(self, i):
        out = ''
        for x in i.line:
            if isinstance(x, str):
                out += x
            elif x[0] == 'getable':
                out += self.filter(self.h_getable(x[1]))
            else:
                raise WTF, x
        return out
    
    def h_lines(self, lines):
        if lines is None: return ''
        return ''.join([self.h_line(itemize(x)) for x in lines])
    
    def h_set(self, i):
        assert i.set[0] == 'var'
        self.output[i.set[1]] = self.h_lines(i.body)

    def h_if(self, i):
        expr = self.h_expr(i['if'])
        if expr: do = i['then']
        else:
            do = None
            for e in i['elif']:
                e = itemize(e)
                expr = self.h_expr(e['expr'])
                if expr:
                    do = e['code']
                    break
                
            if not do: do = i['else']
        return self.h_lines(do)
        
    def h_for(self, i):
        out = ''
        assert i['in'][0] == 'expr'
        invar = self.h_expr(i['in'])
        assert i['for'][0] == 'var'
        forvar = i['for'][1]
        if invar:
            for nv in invar:
                self.d[forvar] = nv # same (lack of) scoping as Python
                out += self.h_lines(i['do'])
        else:
            if i['else']:
                out += self.h_lines(i['else'])
        return out
    
    def h_while(self, i):
        out = ''
        expr = self.h_expr(i['while'])
        if not expr: return self.h_lines(i['else'])
        c = 0
        while expr:
            c += 1
            if c >= MAX_ITERS:
                raise RuntimeError, 'too many while-loop iterations (line %s)' % i.lineno
            out += self.h_lines(i['do'])
            expr = self.h_expr(i['while'])
        
        return out
    
    def go(self):
        self.output = Stowage()
        self.output._str = ''
        for item in self.parsetree:
            self.output._str += self.h(item) or ''
        return self.output

Required = object()
class Template:
    globals = {}
    def __init__(self, text):
        if not text.endswith('\n'): text += '\n'
        header, tree = TemplateParser(text).go()
        self.tree = tree
        if header:
            assert header[0] == 'defwith'
            self.args, kw = header[1:3]
            self.kwargs = []
            f = Fill(self.tree)
            for var, valexpr in kw:
                self.kwargs.append((var, f.h_expr(valexpr)))
        else:
            self.args, self.kwargs = (), {}
    
    def __call__(self, *a, **kw):
        d = self.globals.copy()
        d.update(self._parseargs(a, kw))
        return Fill(self.tree, d=d).go()
    
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

class Falser:
    def __nonzero__(self): return False
    def __cmp__(self, a): return False
    def __getattr__(self, a): 
        if a.startswith('__'): raise AttributeError
        else: return self
