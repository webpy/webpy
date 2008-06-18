"""
Template design:

Template string is split into tokens and the tokens are combined into nodes. 
Parse tree is a nodelist. TextNode and ExpressionNode are simple nodes and 
for-loop, if-loop etc are block nodes, which contain multiple child nodes. 

Each node can emit some python string. python string emitted by the 
root node is validated for safeeval and executed using python in the given environment.

Enough care is taken to make sure the generated code and the template has line to line match, 
so that the error messages can point to exact line number in template. (It doesn't work in some cases still.)

Grammer:

    template -> defwith sections 
    defwith -> '$def with (' arguments ')' | ''
    sections -> section*
    section -> block | assignment | line

    assignment -> '$ ' <assignment expression>
    line -> (text|expr)*
    text -> <any characters other than $>
    expr -> '$' pyexpr | '$(' pyexpr ')' | '${' pyexpr '}'
    pyexpr -> <python expression>

TODOs:
    * take care of unicode issues
    * support for \$
"""

import tokenize, compiler
import os
import glob

from utils import storage
from webapi import config
from net import websafe

DEBUG = True

def splitline(text):
    r"""Splits the given text at newline.
    
        >>> splitline('foo\nbar')
        ('foo\n', 'bar')
        >>> splitline('foo')
        ('foo', '')
        >>> splitline('')
        ('', '')
    """
    index = text.find('\n') + 1
    if index:
        return text[:index], text[index:]
    else:
        return text, ''

class Parser:
    """Parser Base.
    """
    def __init__(self, text, name="<template>"):
        self.text = text
        self.name = name

    def parse(self):
        text = self.text
        defwith, text = self.read_defwith(text)
        suite = self.read_suite(text)
        return DefwithNode(defwith, suite)

    def read_defwith(self, text):
        if text.startswith('$def with'):
            defwith, text = splitline(text)
            defwith = defwith[1:].strip() # strip $ and spaces
            return defwith, text
        else:
            return '', text
    
    def readlines(self, text):
        pass
        
    def read_section(self, text):
        r"""Reads one section from the given text.
        
        section -> block | assignment | line
        
            >>> read_section = Parser('').read_section
            >>> read_section('foo\nbar\n')
            (<line: [t'foo\n']>, 'bar\n')
            >>> read_section('$ a = b + 1\nfoo\n')
            (<assignment: 'a = b + 1'>, 'foo\n')
            
        read_section('$for in range(10):\n    hello $i\nfoo)
        """
        if text.lstrip(' ').startswith('$'):
            index = text.index('$')
            begin_indent, text2 = text[:index], text[index+1:]
            ahead = self.python_lookahead(text2)
            if ahead in STATEMENT_NODES:
                return self.read_block_section(text2, begin_indent)
            elif ahead.strip() == '':
                # assignments starts with a space after $
                # ex: $ a = b + 2
                return self.read_assignment(text2)
        return self.readline(text)
        
    def read_suite(self, text):
        r"""Reads section by section till end of text.
        
            >>> read_suite = Parser('').read_suite
            >>> read_suite('hello $name\nfoo\n')
            [<line: [t'hello ', $name, t'\n']>, <line: [t'foo\n']>]
        """
        sections = []
        while text:
            section, text = self.read_section(text)
            sections.append(section)
        return SuiteNode(sections)
    
    def readline(self, text):
        r"""Reads one line from the text. Newline is supressed if the line ends with \.
        
            >>> readline = Parser('').readline
            >>> readline('hello $name!\nbye!')
            (<line: [t'hello ', $name, t'!\n']>, 'bye!')
            >>> readline('hello $name!\\\nbye!')
            (<line: [t'hello ', $name, t'!']>, 'bye!')
            >>> readline('$f()\n\n')
            (<line: [$f(), t'\n']>, '\n')
        """
        line, text = splitline(text)

        # supress new line if line ends with \
        if line.endswith('\\\n'):
            line = line[:-2]
                
        nodes = []
        while line:
            node, line = self.read_node(line)
            nodes.append(node)
            
        return LineNode(nodes), text

    def read_node(self, text):
        r"""Reads a node from the given text and returns the node and remaining text.

            >>> read_node = Parser('').read_node
            >>> read_node('hello $name')
            (t'hello ', '$name')
            >>> read_node('$name')
            ($name, '')
        """
        if text.startswith('$$'):
            return TextNode('$'), text[2:]
        elif text.startswith('$#'): # comment
            line, text = splitline(text)
            return TextNode('\n'), text
        elif text.startswith('$'):
            text = text[1:] # strip $
            if text.startswith(':'):
                escape = False
                text = text[1:] # strip :
            else:
                escape = True
            return self.read_expr(text, escape=escape)
        else:
            return self.read_text(text)
    
    def read_text(self, text):
        r"""Reads a text node from the given text.
        
            >>> read_text = Parser('').read_text
            >>> read_text('hello $name')
            (t'hello ', '$name')
        """
        index = text.find('$')
        if index < 0:
            return TextNode(text), ''
        else:
            return TextNode(text[:index]), text[index:]

    def read_expr(self, text, escape=True):
        """Reads a python expression from the text and returns the expression and remaining text.

        expr -> simple_expr | paren_expr
        simple_expr -> id extended_expr
        extended_expr -> attr_access | paren_expr extended_expr | ''
        attr_access -> dot id extended_expr
        paren_expr -> [ tokens ] | ( tokens ) | { tokens }
     
            >>> read_expr = Parser('').read_expr
            >>> read_expr("name")
            ($name, '')
            >>> read_expr("a.b and c")
            ($a.b, ' and c')
            >>> read_expr("a. b")
            ($a, '. b')
            >>> read_expr("name</h1>")
            ($name, '</h1>')
            >>> read_expr("(limit)ing")
            ($(limit), 'ing')
            >>> read_expr('a[1, 2][:3].f(1+2, "weird string[).", 3 + 4) done.')
            ($a[1, 2][:3].f(1+2, "weird string[).", 3 + 4), ' done.')
        """
        def simple_expr():
            identifier()
            extended_expr()
        
        def identifier():
            tokens.next()
        
        def extended_expr():
            lookahead = tokens.lookahead()
            if lookahead is None:
                return
            elif lookahead.value == '.':
                attr_access()
            elif lookahead.value in parens:
                paren_expr()
                extended_expr()
            else:
                return
        
        def attr_access():
            from token import NAME # python token constants
            dot = tokens.lookahead()
            if tokens.lookahead2().type == NAME:
                tokens.next() # consume dot
                identifier()
                extended_expr()
        
        def paren_expr():
            begin = tokens.next().value
            end = parens[begin]
            while True:
                if tokens.lookahead().value in parens:
                    paren_expr()
                else:
                    t = tokens.next()
                    if t.value == end:
                        break
            return

        parens = {
            "(": ")",
            "[": "]",
            "{": "}"
        }
        
        def get_tokens(text):
            """tokenize text using python tokenizer.
            Python tokenizer ignores spaces, but they might be important in some cases. 
            This function introduces dummy space tokens when it identifies any ignored space.
            Each token is a storage object containing type, value, begin and end.
            """
            readline = iter([text]).next
            end = None
            for t in tokenize.generate_tokens(readline):
                t = storage(type=t[0], value=t[1], begin=t[2], end=t[3])
                if end is not None and end != t.begin:
                    _, x1 = end
                    _, x2 = t.begin
                    yield storage(type=-1, value=text[x1:x2], begin=end, end=t.begin)
                end = t.end
                yield t
                
        class BetterIter:
            """Iterator like object with 2 support for 2 look aheads."""
            def __init__(self, items):
                self.iteritems = iter(items)
                self.items = []
                self.position = 0
                self.current_item = None
            
            def lookahead(self):
                if len(self.items) <= self.position:
                    self.items.append(self._next())
                return self.items[self.position]

            def _next(self):
                try:
                    return self.iteritems.next()
                except StopIteration:
                    return None
                
            def lookahead2(self):
                if len(self.items) <= self.position+1:
                    self.items.append(self._next())
                return self.items[self.position+1]
                    
            def next(self):
                self.current_item = self.lookahead()
                self.position += 1
                return self.current_item

        tokens = BetterIter(get_tokens(text))
                
        if tokens.lookahead().value in parens:
            paren_expr()
        else:
            simple_expr()
        row, col = tokens.current_item.end
        return ExpressionNode(text[:col], escape=escape), text[col:]    

    def read_assignment(self, text):
        r"""Reads assignment statement from text.
    
            >>> read_assignment = Parser('').read_assignment
            >>> read_assignment('a = b + 1\nfoo')
            (<assignment: 'a = b + 1'>, 'foo')
        """
        line, text = splitline(text)
        return AssignmentNode(line.strip()), text
    
    def python_lookahead(self, text):
        """Returns the first python token from the given text.
        
            >>> python_lookahead = Parser('').python_lookahead
            >>> python_lookahead('for i in range(10):')
            'for'
            >>> python_lookahead('else:')
            'else'
            >>> python_lookahead(' x = 1')
            ' '
        """
        readline = iter([text]).next
        tokens = tokenize.generate_tokens(readline)
        return tokens.next()[1]
        
    def read_indented_block(self, text, indent):
        r"""Read a block of text. A block is what typically follows a for or it statement.
        It can be in the same line as that of the statement or an indented block.

            >>> read_indented_block = Parser('').read_indented_block
            >>> read_indented_block('  a\n  b\nc', '  ')
            ('a\nb\n', 'c')
            >>> read_indented_block('  a\n    b\n  c\nd', '  ')
            ('a\n  b\nc\n', 'd')
        """
        block = ""
        while True:
            if text.startswith(indent):
                line, text = splitline(text)
                block += line[len(indent):]
            else:
                break
        return block, text

    def read_statement(self, text):
        r"""Reads a python statement.
        
            >>> read_statement = Parser('').read_statement
            >>> read_statement('for i in range(10): hello $name')
            ('for i in range(10):', ' hello $name')
        """
        tok = PythonTokenizer(text)
        tok.consume_till(':')
        return text[:tok.index], text[tok.index:]
        
    def read_block_section(self, text, begin_indent=''):
        r"""
            >>> read_block_section = Parser('').read_block_section
            >>> read_block_section('for i in range(10): hello $i\nfoo')
            (<block: 'for i in range(10):', [<line: [t' hello ', $i, t'\n']>]>, 'foo')
            >>> read_block_section('for i in range(10):\n        hello $i\n    foo', begin_indent='    ')
            (<block: 'for i in range(10):', [<line: [t'hello ', $i, t'\n']>]>, '    foo')
        """
        line, text = splitline(text)
        stmt, line = self.read_statement(line)
        keyword = self.python_lookahead(stmt)
        
        #@@ quick hack to support var
        if keyword == 'var':
            node, _ = self.readline(line)
            return VarNode(stmt, node), text
        
        # if there is some thing left in the line
        if line.strip():
            block = line
        else:
            block, text = self.read_indented_block(text, begin_indent + INDENT)
            
        suite = self.read_suite(block)
        return self.create_block_node(keyword, stmt, suite, begin_indent), text
        
    def create_block_node(self, keyword, stmt, suite, begin_indent):
        if keyword in STATEMENT_NODES:
            return STATEMENT_NODES[keyword](stmt, suite, begin_indent)
        else:
            raise ParseError, 'Unknown statement: %s' % repr(keyword)
        
class PythonTokenizer:
    """Utility wrapper over python tokenizer."""
    def __init__(self, text):
        self.text = text
        readline = iter([text]).next
        self.tokens = tokenize.generate_tokens(readline)
        self.index = 0
        
    def consume_till(self, delim):        
        """Consumes tokens till colon.
        
            >>> tok = PythonTokenizer('for i in range(10): hello $i')
            >>> tok.consume_till(':')
            >>> tok.text[:tok.index]
            'for i in range(10):'
            >>> tok.text[tok.index:]
            ' hello $i'
        """      
        while True:
            t = self.next()
            if t.value == delim:
                break
    
    def next(self):
        type, t, begin, end, line = self.tokens.next()
        row, col = end
        self.index = col
        return storage(type=type, value=t, begin=begin, end=end)
        
class DefwithNode:
    def __init__(self, defwith, suite):
        if defwith:
            self.defwith = defwith.replace('with', '__template__') + ':'
        else:
            self.defwith = 'def __template__():'
        self.suite = suite

    def emit(self, indent):
        return self.defwith + self.suite.emit(indent + INDENT)

    def __repr__(self):
        return "<defwith: %s, %s>" % (self.defwith, self.nodes)

class TextNode:
    def __init__(self, value):
        self.value = value

    def emit(self, indent):
        return repr(self.value)
        
    def __repr__(self):
        return 't' + repr(self.value)
        
class ExpressionNode:
    def __init__(self, value, escape=True):
        self.value = value.strip()
        
        # convert ${...} to $(...)
        if value.startswith('{') and value.endswith('}'):
            self.value = '(' + self.value[1:-1] + ')'
            
        self.escape = escape

    def emit(self, indent):
        return 'escape_(%s, %s)' % (self.value, bool(self.escape))
        
    def __repr__(self):
        if self.escape:
            escape = ''
        else:
            escape = ':'
        return "$%s%s" % (escape, self.value)
        
class AssignmentNode:
    def __init__(self, code):
        self.code = code
        
    def emit(self, indent, begin_indent=''):
        return indent + self.code + "\n"
        
    def __repr__(self):
        return "<assignment: %s>" % repr(self.code)
        
class LineNode:
    def __init__(self, nodes):
        self.nodes = nodes
        
    def emit(self, indent, text_indent='', name='main'):
        text = [node.emit('') for node in self.nodes]
        if text_indent:
            text = [repr(text_indent)] + text
        return indent + 'yield %s, join_(%s)\n' % (repr(name), ', '.join(text))
    
    def __repr__(self):
        return "<line: %s>" % repr(self.nodes)

INDENT = '    ' # 4 spaces
        
class BlockNode:
    def __init__(self, stmt, suite, begin_indent=''):
        self.stmt = stmt
        self.suite = suite
        self.begin_indent = begin_indent

    def emit(self, indent, text_indent=''):
        text_indent = self.begin_indent + text_indent
        out = indent + self.stmt + self.suite.emit(indent + INDENT, text_indent)
        return out
        
    def text(self):
        return '${' + self.stmt + '}' + "".join(node.text(indent) for node in self.nodes)
        
    def __repr__(self):
        return "<block: %s, %s>" % (repr(self.stmt), repr(self.nodelist))

class ForNode(BlockNode):
    def __init__(self, stmt, suite, begin_indent=''):
        self.original_stmt = stmt
        tok = PythonTokenizer(stmt)
        tok.consume_till('in')
        a = stmt[:tok.index] # for i in
        b = stmt[tok.index:-1] # rest of for stmt excluding :
        stmt = a + ' loop.setup(' + b.strip() + '):'
        BlockNode.__init__(self, stmt, suite, begin_indent)
        
    def __repr__(self):
        return "<block: %s, %s>" % (repr(self.original_stmt), repr(self.suite))
    
class IfNode(BlockNode):
    pass

class ElseNode(BlockNode):
    pass

class ElifNode(BlockNode):
    pass

class DefNode(BlockNode):
    pass

class VarNode:
    def __init__(self, stmt, node):
        _, self.name = stmt.split()
        self.node = node
        
    def emit(self, indent, text_indent):
        return self.node.emit(indent, text_indent, self.name)

class SuiteNode:
    """Suite is a list of sections."""
    def __init__(self, sections):
        self.sections = sections
        
    def emit(self, indent, text_indent=''):
        return "\n" + "".join([s.emit(indent, text_indent) for s in self.sections])
        
    def __repr__(self):
        return repr(self.sections)

STATEMENT_NODES = {
    'for': ForNode,
    'if': IfNode,
    'elif': ElifNode,
    'else': ElseNode,
    'def': DefNode,
    'var': VarNode,
}
        
TEMPLATE_BUILTIN_NAMES = [
    "dict", "enumerate", "float", "int", "bool", "list", "long", "reversed", 
    "set", "slice", "tuple", "xrange",
    "abs", "all", "any", "callable", "chr", "cmp", "divmod", "filter", "hex", 
    "id", "isinstance", "iter", "len", "max", "min", "oct", "ord", "pow", "range",
    "True", "False"
]

import __builtin__
TEMPLATE_BUILTINS = dict([(name, getattr(__builtin__, name)) for name in TEMPLATE_BUILTIN_NAMES if name in __builtin__.__dict__])

class ForLoop:
    """Wrapper for expression in for stament to support forloop.xxx helpers.
    
        >>> forloop = ForLoop()
        >>> for x in forloop.setup(['a', 'b', 'c']):
        ...     print forloop.index, forloop.parity, x
        ...
        1 odd a
        2 even b
        3 odd c
        >>> forloop.index
        Traceback (most recent call last):
            ...
        AttributeError: index
    """
    def __init__(self):
        self._ctx = None
        
    def __getattr__(self, name):
        if self._ctx is None:
            raise AttributeError, name
        else:
            return getattr(self._ctx, name)
        
    def setup(self, seq):
        self._push()
        return self._ctx.setup(seq)
        
    def _push(self):
        self._ctx = ForLoopContext(self, self._ctx)
        
    def _pop(self):
        self._ctx = self._ctx.parent
                
class ForLoopContext:
    """Stackable context for ForLoop to support nested for loops.
    """
    def __init__(self, forloop, parent):
        self._forloop = forloop
        self.parent = parent
        
    def setup(self, seq):
        if hasattr(seq, '__len__'):
            n = len(seq)
        else:
            n = 0

        try:
            for i, x in enumerate(seq):
                self._next(i+1, n)
                yield x
        finally:
            self._forloop._pop()
    
    def _next(self, i, n):
        self.index = i
        self.index0 = i - 1
        self.first = (i == 1)
        self.last = (i == n)
        self.odd = (i % 2 == 1)
        self.even = (i % 2 == 0)
        self.parity = ['odd', 'even'][self.even]
        
class BaseTemplate:
    def __init__(self, code, filename, filter, globals, builtins):
        self.code = code
        self.filename = filename
        self.filter = filter
        self._globals = globals
        self._builtins = builtins
        self.t = None
        
    def _compile(self):
        env = self.make_env(self._globals or {}, self._builtins or TEMPLATE_BUILTINS)
        exec(self.code, env)
        return env['__template__']

    def __call__(self, *a, **kw):
        #@@ HACK: compile lazily on demand
        if self.t is None:
            self.t = self._compile()
        
        out = self.t(*a, **kw)
        d = Stowage()
        for name, value in out:
            d.setdefault(name, []).append(value)
            
        for k in d.keys():
            d[k] = "".join(d[k])
            
        d._str = d.main
        return d

    def make_env(self, globals, builtins):
        return dict(globals, 
            __builtins__=builtins, 
            loop=ForLoop(),
            escape_=self._escape,
            join_=self._join
        )
        
    def _join(self, *items):
        return "".join(items)
        
    def _escape(self, value, escape=False):
        import types
        if value is None: 
            value = ''
        elif isinstance(value, types.GeneratorType):
            value = "".join(value)
        else:
            value = str(value)
        if escape and self.filter:
            value = self.filter(value)
        return value

class Template(BaseTemplate):
    CONTENT_TYPES = {
        '.html' : 'text/html; charset=utf-8',
        '.txt' : 'text/plain',
    }
    FILTERS = {
        '.html': websafe,
        '.xml': websafe
    }
    globals = {}
    
    def __init__(self, text, filename='<template>', filter=None, globals=None, builtins=None):
        text = text.replace('\r\n', '\n').replace('\r', '\n').expandtabs()
        if not text.endswith('\n'):
            text += '\n'
        code = self.compile_template(text, filename)
        
        _, ext = os.path.splitext(filename)
        filter = filter and self.FILTERS.get(ext, None)
        self.content_type = self.CONTENT_TYPES.get(ext, None)
        
        globals = globals or self.globals
        
        BaseTemplate.__init__(self, code=code, filename=filename, filter=filter, globals=globals, builtins=builtins)
        
    def __calll__(self, *a, **kw):
        import webapi as web
        if 'headers' in web.ctx and self.content_type:
            web.header('Content-Type', self.content_type)
            
        return BaseTemplate.__calll__(self, *a, **kw)
        
    def compile_template(self, template_string, filename):
        # parse the template string
        rootnode = Parser(template_string, filename).parse()
        
        # generate python code from the parse tree
        code = rootnode.emit(indent="").strip()
        
        # make sure code is safe
        ast = compiler.parse(code)
        SafeVisitor().walk(ast, filename)

        # compile the python code
        return compile(code, filename, 'exec')
                
def frender(filename, filter=None, globals=None):
    text = open(filename).read()
    if filter is None:
        if filename.endswith('.html') or filename.endswith('.xml'):
            filter = websafe
    return Template(text, filename=filename, filter=filter)    
    
class render:
    filters = {'html': websafe, 'xml': websafe}
    
    def __init__(self, loc='templates/', cache=None, base=None):
        if cache is None:
            cache = not config.get('debug', False)
            
        self._loc = loc
        if cache:
            self._cache = {}
        else:
            self._cache = False

        self._base = base
        
    def _get_filter(self, filename):
        _, ext = os.path.splitext(filename)
        ext = ext[1:] #strip .
        return self.filters.get(ext, None)
        
    def _get_template(self, name, filter):
        path = os.path.join(self._loc, name)
        p = [f for f in glob.glob(path + '.*') if not f.endswith('~')] # skip backup files
        if not p and os.path.isdir(path):
            return render(path, cache=self._cache, base=self._base)
        elif not p:
            raise AttributeError, 'no template named ' + name
            
        p = p[0]
        filter = filter or self._get_filter(p)
        return Template(open(p).read(), filter=filter, filename=p)

    def _do(self, name, filter=None):
        if self._cache and name not in self._cache:
            t = self._get_template(name, filter)
            self._cache[name] = t
        else:
            t = self._get_template(name, filter)
        return t
    
    def __getattr__(self, p):
        if self._base:
            return lambda *a, **kw: self._do(self._base)(self._do(p)(*a, **kw))
        else:
            return self._do(p)

class ParseError(Exception):
    pass
    
class SecurityError(Exception):
    """The template seems to be trying to do something naughty."""
    pass

# Enumerate all the allowed AST nodes
ALLOWED_AST_NODES = [
    "Add", "And",
#   "AssAttr",
    "AssList", "AssName", "AssTuple",
#   "Assert",
    "Assign", "AugAssign",
#   "Backquote",
    "Bitand", "Bitor", "Bitxor", "Break",
    "CallFunc","Class", "Compare", "Const", "Continue",
    "Decorators", "Dict", "Discard", "Div",
    "Ellipsis", "EmptyNode",
#   "Exec",
    "Expression", "FloorDiv", "For",
#   "From",
    "Function", 
    "GenExpr", "GenExprFor", "GenExprIf", "GenExprInner",
    "Getattr", 
#   "Global", 
    "If", "IfExp",
#   "Import",
    "Invert", "Keyword", "Lambda", "LeftShift",
    "List", "ListComp", "ListCompFor", "ListCompIf", "Mod",
    "Module",
    "Mul", "Name", "Not", "Or", "Pass", "Power",
#   "Print", "Printnl", "Raise",
    "Return", "RightShift", "Slice", "Sliceobj",
    "Stmt", "Sub", "Subscript",
#   "TryExcept", "TryFinally",
    "Tuple", "UnaryAdd", "UnarySub",
    "While", "With", "Yield",
]

class SafeVisitor(object):
    """
    Make sure code is safe by walking through the AST.
    
    Code considered unsafe if:
        * it has restricted AST nodes
        * it is trying to access resricted attributes   
        
    Adopted from http://www.zafar.se/bkz/uploads/safe.txt (public domain, Babar K. Zafar)
    """
    def __init__(self):
        "Initialize visitor by generating callbacks for all AST node types."
        self.errors = []

    def walk(self, ast, filename):
        "Validate each node in AST and raise SecurityError if the code is not safe."
        self.filename = filename
        self.visit(ast)
        
        if self.errors:        
            raise SecurityError, '\n'.join([str(err) for err in self.errors])
        
    def visit(self, node, *args):
        "Recursively validate node and all of its children."
        def classname(obj):
            return obj.__class__.__name__
        nodename = classname(node)
        fn = getattr(self, 'visit' + nodename, None)
        
        if fn:
            fn(node, *args)
        else:
            if nodename not in ALLOWED_AST_NODES:
                self.fail(node, *args)
            
        for child in node.getChildNodes():
            self.visit(child, *args)

    def visitName(self, node, *args):
        "Disallow any attempts to access a restricted attr."
        #self.assert_attr(node.getChildren()[0], node)
        pass
        
    def visitGetattr(self, node, *args):
        "Disallow any attempts to access a restricted attribute."
        self.assert_attr(node.attrname, node)
            
    def assert_attr(self, attrname, node):
        if self.is_unallowed_attr(attrname):
            lineno = self.get_node_lineno(node)
            e = SecurityError("%s:%d - access to attribute '%s' is denied" % (self.filename, lineno, attrname))
            self.errors.append(e)

    def is_unallowed_attr(self, name):
        return name.startswith('_') \
            or name.startswith('func_') \
            or name.startswith('im_')
            
    def get_node_lineno(self, node):
        return (node.lineno) and node.lineno or 0
        
    def fail(self, node, *args):
        "Default callback for unallowed AST nodes."
        lineno = self.get_node_lineno(node)
        nodename = node.__class__.__name__
        e = SecurityError("%s:%d - execution of '%s' statements is denied" % (self.filename, lineno, nodename))
        self.errors.append(e)

class Stowage(storage):
    def __str__(self): 
        return self.get('_str')
        
    def __repr__(self):
        return "<Stowage: %s, %s>" % (self.keys(), repr(str(self)[:30]))
    
    def __getattr__(self, name):
        if name == 'rawtext':
            return storage.__getattr__(self, name)
        return self.get(name, '')
        
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
        
if __name__ == "__main__":
    import doctest
    doctest.testmod()
        
