"""template.py: simple, elegant templating"""
__author__ = "Aaron Swartz <me@aaronsw.com>"
__version__ = .0001

from web import storage, group
import re
# differences from python:
#  - you can use the expression inside if, while blocks
#  - special for loop attributes, like django?
#  - you can check to see if a variable is defined (perhaps w/ get func?)
#  - for: has an optional else: 
# all these are probably good ideas for python...

# todo:
#  indentation rules too strict
#  nested blocks (for within if, etc.)
#  better getable, expr support
#  setting things
#  continue, break, etc.
#  function calls
#  code blocks
#  debugger/tracebacks

MAX_ITERS = 100000

# http://docs.python.org/ref/identifiers.html
r_var = '[a-zA-Z_][a-zA-Z0-9_]*|\([a-zA-Z_][a-zA-Z0-9_]*\)'

class Nope(Exception): pass
class Parser:
    def __init__(_, text):
        _.t = text
        _.p = 0
    
    def q(_, f):
        def internal(*args):
            checkp = _.p
            try: q = f(*args)
            except Nope: 
                _.p = checkp
                return False
            return q or True
        return internal
    
    def tokr(_, t): 
        if _.c(len(t)) != t: raise Nope
        return t
    
    def rer(_, r):
        x = re.match(r, _.t[_.p:]) #@@re_compile
        if not x: raise Nope
        return _.tokr(x.group())
    
    def endr(_):
        if _.p != len(_.t): raise Nope
        
    def c(_, n=1):
        out = _.t[_.p:_.p+n]
        if out == '' and n != 0: raise Nope
        _.p += n
        return out

#    def lookbehind(_, t):
#        return _.t[_.p-len(t):_.p] == t
    
    def __getattr__(self, a):
        if a.endswith('q'):
            return self.q(getattr(self, a[:-1]+'r'))
        raise AttributeError
    

class Template(Parser):
    def go(_): 
        # maybe try to do some traceback parsing
        return _.gor()
    
    def gor(_):
        results = []
        while 1:
            ws = _.ws()
            x = _.ifq(ws) or _.forq(ws) or _.whileq(ws) or _.lineq(ws, 0)
            if not x: break
            results.append(x)
        _.endr()
        return results
    
    def ws(_):
        n = 0
        while _.tokq(" "): n += 1
        return " " * n

    def ifr(_, ws):
        _.tokr("$if ")
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
                
        return ('if', expr, 'then', ifc, 'elif', elifs, 'else', elsec)
    
    def forr(_, ws):
        _.tokr("$for ")
        v = _.varr()
        _.tokr(" in ")
        g = _.getabler()
        _.tokr(":")
        l = _.lines(ws)

        if _.tokq(ws+'$else:'): elsec = _.lines(ws)
        else: elsec = None
            
        return ('for', v, 'in', g, 'do', l, 'else', elsec)
    
    def whiler(_, ws):
        _.tokr('$while ')
        v = _.exprr()
        _.tokr(":")
        l = _.lines(ws)
        
        if _.tokq(ws+'$else:'): elsec = _.lines(ws)
        else: elsec = None
        
        return ('while', v, 'do', l, 'else', elsec)
        
    def varr(_):
        n = _.rer(r_var)
        if n.startswith('(') and n.endswith(')'): n = n[1:-1]
        return n
    
    def getabler(_):
        #var ["." var]+
        return _.varr()
    
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
        o = ''
        _.tokr(ws+' '*ilevel)
        o += ws
        while 1:
            c = _.c()
            if c == '\n': _.p -= 1; break
            o += c
        _.tokr('\n')
        o+='\n'
        return ('line', prefix+o)
    
    def exprr(_):
        # something involving getables
        x = _.getableq() or _.req('[0-9]+')
        if not x: raise Nope
        return ('expr', x)

def itemize(item):
    return storage(dict(group(item, 2)))

class Handle:
    def __init__(self, parsetree, **kw):
        self.parsetree = parsetree
        for (k, v) in kw.iteritems(): setattr(self, k, v)    
    
    def go(self):
        out = ''
        for item in self.parsetree:
            out += getattr(self, 'h_'+item[0])(itemize(item))
        return out
            
class Fill(Handle):
    def filter(self, text):
        if text == None: return ''
        else: return str(text)
    
    def h_expr(self, item):
        i = item[1]
        if i.isdigit(): return int(i)
        else: return self.d[i]
        
    r_v = re.compile(r'(?<!\\)\$('+r_var+')') #@@ use varr
    def h_line(self, i):
        def internal(m):
            n = m.groups()[0]
            if n.startswith('(') and n.endswith(')'): n = n[1:-1]
            return self.filter(self.d[n])
        i = self.r_v.sub(internal, i.line)
        return i
    
    def h_lines(self, lines):
        if lines is None: return ''
        return ''.join([self.h_line(itemize(x)) for x in lines])

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
        av = self.d[i['in']]
        if av:
            oldd = self.d.copy()
            for nv in av:
                self.d[i['for']] = nv
                out += self.h_lines(i['do'])
            self.d = oldd
        else:
            if i['else']: out += self.h_lines(i['else'])
        return out
    
    def h_while(self, i):
        out = ''
        expr = self.h_expr(i['while'])
        if not expr: return self.h_lines(i['else'])
        c = 0
        while expr:
            c += 1
            if c >= MAX_ITERS: raise RuntimeError, 'too many while loop iterations -- infinite loop?'
            out += self.h_lines(i['do'])
            expr = self.h_expr(i['while'])
        
        return out

def process(text, d):
    if not text.endswith('\n'): text += '\n'
    tree = Template(text).go()
    import pprint
    print pprint.pformat(tree)
    print
    print Fill(tree, d=d).go()

class Falser:
    def __nonzero__(self): return False
    def __cmp__(self, a): return False
    def __getattr__(self, a): 
        if a.startswith('__'): raise AttributeError
        else: return self
