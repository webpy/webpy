"""
simple, elegant templating
(part of web.py)

Template design:

Template string is split into tokens and the tokens are combined into nodes. 
Parse tree is a nodelist. TextNode and ExpressionNode are simple nodes and 
for-loop, if-loop etc are block nodes, which contain multiple child nodes. 

Each node can emit some python string. python string emitted by the 
root node is validated for safeeval and executed using python in the given environment.

Enough care is taken to make sure the generated code and the template has line to line match, 
so that the error messages can point to exact line number in template. (It doesn't work in some cases still.)

Grammar:

    template -> defwith sections 
    defwith -> '$def with (' arguments ')' | ''
    sections -> section*
    section -> block | assignment | line

    assignment -> '$ ' <assignment expression>
    line -> (text|expr)*
    text -> <any characters other than $>
    expr -> '$' pyexpr | '$(' pyexpr ')' | '${' pyexpr '}'
    pyexpr -> <python expression>

"""

__all__ = [
    "Template",
    "Render", "render", "frender",
    "ParseError", "SecurityError",
    "test"
]

import tokenize
import os
import glob
import re

from utils import storage, safeunicode, safestr, re_compile
from webapi import config
from net import websafe

def splitline(text):
    r"""
    Splits the given text at newline.
    
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
            
            if ahead == 'var':
                return self.read_var(text2)
            elif ahead in STATEMENT_NODES:
                return self.read_block_section(text2, begin_indent)
            elif ahead in KEYWORDS:
                return self.read_keyword(text2)
            elif ahead.strip() == '':
                # assignments starts with a space after $
                # ex: $ a = b + 2
                return self.read_assignment(text2)
        return self.readline(text)
        
    def read_var(self, text):
        r"""Reads a var statement.
        
            >>> read_var = Parser('').read_var
            >>> read_var('var x=10\nfoo')
            (<var: x = 10>, 'foo')
            >>> read_var('var x: hello $name\nfoo')
            (<var: x = join_('hello ', escape_(name, True))>, 'foo')
        """
        line, text = splitline(text)
        tokens = self.python_tokens(line)
        if len(tokens) < 4:
            raise SyntaxError('Invalid var statement')
            
        name = tokens[1]
        sep = tokens[2]
        value = line.split(sep, 1)[1].strip()
        
        if sep == '=':
            pass # no need to process value
        elif sep == ':': 
            #@@ Hack for backward-compatability
            if tokens[3] == '\n': # multi-line var statement
                block, text = self.read_indented_block(text, '    ')
                lines = [self.readline(x)[0] for x in block.splitlines()]
                nodes = []
                for x in lines:
                    nodes.extend(x.nodes)
                    nodes.append(TextNode('\n'))         
            else: # single-line var statement
                linenode, _ = self.readline(value)
                nodes = linenode.nodes                
            parts = [node.emit('') for node in nodes]
            value = "join_(%s)" % ", ".join(parts)
        else:
            raise SyntaxError('Invalid var statement')
        return VarNode(name, value), text
                    
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
            
    def read_keyword(self, text):
        line, text = splitline(text)
        return CodeNode(None, line.strip() + "\n"), text

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
        
    def python_tokens(self, text):
        readline = iter([text]).next
        tokens = tokenize.generate_tokens(readline)
        return [t[1] for t in tokens]
        
    def read_indented_block(self, text, indent):
        r"""Read a block of text. A block is what typically follows a for or it statement.
        It can be in the same line as that of the statement or an indented block.

            >>> read_indented_block = Parser('').read_indented_block
            >>> read_indented_block('  a\n  b\nc', '  ')
            ('a\nb\n', 'c')
            >>> read_indented_block('  a\n    b\n  c\nd', '  ')
            ('a\n  b\nc\n', 'd')
        """
        if indent == '':
            return '', text
            
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
            (<block: 'for i in range(10):', [<line: [t'hello ', $i, t'\n']>]>, 'foo')
            >>> read_block_section('for i in range(10):\n        hello $i\n    foo', begin_indent='    ')
            (<block: 'for i in range(10):', [<line: [t'hello ', $i, t'\n']>]>, '    foo')
            >>> read_block_section('for i in range(10):\n  hello $i\nfoo')
            (<block: 'for i in range(10):', [<line: [t'hello ', $i, t'\n']>]>, 'foo')
        """
        line, text = splitline(text)
        stmt, line = self.read_statement(line)
        keyword = self.python_lookahead(stmt)
        
        # if there is some thing left in the line
        if line.strip():
            block = line.lstrip()
        else:
            def find_indent(text):
                rx = re_compile('  +')
                match = rx.match(text)    
                first_indent = match and match.group(0)
                return first_indent or ""

            # find the indentation of the block by looking at the first line
            first_indent = find_indent(text)[len(begin_indent):]
            indent = begin_indent + min(first_indent, INDENT)
            
            block, text = self.read_indented_block(text, indent)
            
        return self.create_block_node(keyword, stmt, block, begin_indent), text
        
    def create_block_node(self, keyword, stmt, block, begin_indent):
        if keyword in STATEMENT_NODES:
            return STATEMENT_NODES[keyword](stmt, block, begin_indent)
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
        try:
            while True:
                t = self.next()
                if t.value == delim:
                    break
                elif t.value == '(':
                    self.consume_till(')')
                elif t.value == '[':
                    self.consume_till(']')
                elif t.value == '{':
                    self.consume_till('}')

                # if end of line is found, it is an exception.
                # Since there is no easy way to report the line number,
                # leave the error reporting to the python parser later  
                #@@ This should be fixed.
                if t.value == '\n':
                    break
        except:
            #raise ParseError, "Expected %s, found end of line." % repr(delim)

            # raising ParseError doesn't show the line number. 
            # if this error is ignored, then it will be caught when compiling the python code.
            return
    
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
        
    def emit(self, indent, text_indent='', name=''):
        text = [node.emit('') for node in self.nodes]
        if text_indent:
            text = [repr(text_indent)] + text
        return indent + 'yield %s, join_(%s)\n' % (repr(name), ', '.join(text))
    
    def __repr__(self):
        return "<line: %s>" % repr(self.nodes)

INDENT = '    ' # 4 spaces
        
class BlockNode:
    def __init__(self, stmt, block, begin_indent=''):
        self.stmt = stmt
        self.suite = Parser('').read_suite(block)
        self.begin_indent = begin_indent

    def emit(self, indent, text_indent=''):
        text_indent = self.begin_indent + text_indent
        out = indent + self.stmt + self.suite.emit(indent + INDENT, text_indent)
        return out
        
    def text(self):
        return '${' + self.stmt + '}' + "".join([node.text(indent) for node in self.nodes])
        
    def __repr__(self):
        return "<block: %s, %s>" % (repr(self.stmt), repr(self.nodelist))

class ForNode(BlockNode):
    def __init__(self, stmt, block, begin_indent=''):
        self.original_stmt = stmt
        tok = PythonTokenizer(stmt)
        tok.consume_till('in')
        a = stmt[:tok.index] # for i in
        b = stmt[tok.index:-1] # rest of for stmt excluding :
        stmt = a + ' loop.setup(' + b.strip() + '):'
        BlockNode.__init__(self, stmt, block, begin_indent)
        
    def __repr__(self):
        return "<block: %s, %s>" % (repr(self.original_stmt), repr(self.suite))

class CodeNode:
    def __init__(self, stmt, block, begin_indent=''):
        self.code = block
        
    def emit(self, indent, text_indent=''):
        import re
        rx = re.compile('^', re.M)
        return rx.sub(indent, self.code).rstrip(' ')
        
    def __repr__(self):
        return "<code: %s>" % repr(self.code)
        
class IfNode(BlockNode):
    pass

class ElseNode(BlockNode):
    pass

class ElifNode(BlockNode):
    pass

class DefNode(BlockNode):
    pass

class VarNode:
    def __init__(self, name, value):
        self.name = name
        self.value = value
        
    def emit(self, indent, text_indent):
        return indent + 'yield %s, %s\n' % (repr(self.name), self.value)
        
    def __repr__(self):
        return "<var: %s = %s>" % (self.name, self.value)

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
    'while': BlockNode,
    'if': IfNode,
    'elif': ElifNode,
    'else': ElseNode,
    'def': DefNode,
    'code': CodeNode
}

KEYWORDS = [
    "pass",
    "break",
    "continue",
    "return"
]

TEMPLATE_BUILTIN_NAMES = [
    "dict", "enumerate", "float", "int", "bool", "list", "long", "reversed", 
    "set", "slice", "tuple", "xrange",
    "abs", "all", "any", "callable", "chr", "cmp", "divmod", "filter", "hex", 
    "id", "isinstance", "iter", "len", "max", "min", "oct", "ord", "pow", "range",
    "True", "False",
    "None",
    "__import__", # some c-libraries like datetime requires __import__ to present in the namespace
]

import __builtin__
TEMPLATE_BUILTINS = dict([(name, getattr(__builtin__, name)) for name in TEMPLATE_BUILTIN_NAMES if name in __builtin__.__dict__])

class ForLoop:
    """
    Wrapper for expression in for stament to support loop.xxx helpers.
    
        >>> loop = ForLoop()
        >>> for x in loop.setup(['a', 'b', 'c']):
        ...     print loop.index, loop.revindex, loop.parity, x
        ...
        1 3 odd a
        2 2 even b
        3 1 odd c
        >>> loop.index
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
            
        self.index = 0
        seq = iter(seq)
        
        # Pre python-2.5 does not support yield in try-except.
        # This is a work-around to overcome that limitation.
        def next(seq):
            try:
                return seq.next()
            except:
                self._forloop._pop()
                raise
        
        while True:
            self._next(self.index + 1, n)
            yield next(seq)
            
    def _next(self, i, n):
        self.index = i
        self.index0 = i - 1
        self.first = (i == 1)
        self.last = (i == n)
        self.odd = (i % 2 == 1)
        self.even = (i % 2 == 0)
        self.parity = ['odd', 'even'][self.even]
        if n:
            self.length = n
            self.revindex0 = n - i
            self.revindex = self.revindex0 + 1
        
class BaseTemplate:
    def __init__(self, code, filename, filter, globals, builtins):
        self.filename = filename
        self.filter = filter
        self._globals = globals
        self._builtins = builtins
        if code:
            self.t = self._compile(code)
        else:
            self.t = lambda: ''
        
    def _compile(self, code):
        env = self.make_env(self._globals or {}, self._builtins)
        exec(code, env)
        return env['__template__']

    def __call__(self, *a, **kw):
        out = self.t(*a, **kw)
        return self._join_output(out)
        
    def _join_output(self, out):
        d = TemplateResult()
        data = []
        
        for name, value in out:
            if name:
                d[name] = value
            else:
                data.append(value)
                            
        d.__body__ = u"".join(data)
        return d       

    def make_env(self, globals, builtins):
        return dict(globals,
            __builtins__=builtins, 
            loop=ForLoop(),
            escape_=self._escape,
            join_=self._join
        )
    
    def _join(self, *items):
        return u"".join([safeunicode(item) for item in items])
        
    def _escape(self, value, escape=False):
        import types
        if value is None: 
            value = ''
        elif isinstance(value, types.GeneratorType):
            value = self._join_output(value)
            
        value = safeunicode(value)
        if escape and self.filter:
            value = self.filter(value)
        return value

class Template(BaseTemplate):
    CONTENT_TYPES = {
        '.html' : 'text/html; charset=utf-8',
        '.xhtml' : 'application/xhtml+xml; charset=utf-8',
        '.txt' : 'text/plain',
    }
    FILTERS = {
        '.html': websafe,
        '.xhtml': websafe,
        '.xml': websafe
    }
    globals = {}
    
    def __init__(self, text, filename='<template>', filter=None, globals=None, builtins=None):
        text = Template.normalize_text(text)
        code = self.compile_template(text, filename)
                
        _, ext = os.path.splitext(filename)
        filter = filter or self.FILTERS.get(ext, None)
        self.content_type = self.CONTENT_TYPES.get(ext, None)

        if globals is None:
            globals = self.globals
        if builtins is None:
            builtins = TEMPLATE_BUILTINS
                
        BaseTemplate.__init__(self, code=code, filename=filename, filter=filter, globals=globals, builtins=builtins)
        
    def normalize_text(text):
        """Normalizes template text by correcting \r\n, tabs and BOM chars."""
        text = text.replace('\r\n', '\n').replace('\r', '\n').expandtabs()
        if not text.endswith('\n'):
            text += '\n'

        # ignore BOM chars at the begining of template
        BOM = '\xef\xbb\xbf'
        if isinstance(text, str) and text.startswith(BOM):
            text = text[len(BOM):]
        
        # support fort \$ for backward-compatibility 
        text = text.replace(r'\$', '$$')
        return text
    normalize_text = staticmethod(normalize_text)
                
    def __call__(self, *a, **kw):
        import webapi as web
        if 'headers' in web.ctx and self.content_type:
            web.header('Content-Type', self.content_type, unique=True)
            
        return BaseTemplate.__call__(self, *a, **kw)
        
    def generate_code(text, filename):
        # parse the text
        rootnode = Parser(text, filename).parse()
                
        # generate python code from the parse tree
        code = rootnode.emit(indent="").strip()
        return safestr(code)
        
    generate_code = staticmethod(generate_code)
        
    def compile_template(self, template_string, filename):
        code = Template.generate_code(template_string, filename)
    
        def get_source_line(filename, lineno):
            try:
                lines = open(filename).read().splitlines()
                return lines[lineno]
            except:
                return None
        
        try:
            # compile the code first to report the errors, if any, with the filename
            compiled_code = compile(code, filename, 'exec')
        except SyntaxError, e:
            # display template line that caused the error along with the traceback.
            try:
                e.msg += '\n\nTemplate traceback:\n    File %s, line %s\n        %s' % \
                    (repr(e.filename), e.lineno, get_source_line(e.filename, e.lineno-1))
            except: 
                pass
            raise
        
        # make sure code is safe
        import compiler
        ast = compiler.parse(code)
        SafeVisitor().walk(ast, filename)

        return compiled_code
        
class CompiledTemplate(Template):
    def __init__(self, f, filename):
        Template.__init__(self, '', filename)
        self.t = f
        
    def compile_template(self, *a):
        return None
    
    def _compile(self, *a):
        return None
                
class Render:
    """The most preferred way of using templates.
    
        render = web.template.render('templates')
        print render.foo()
        
    Optional parameter can be `base` can be used to pass output of 
    every template through the base template.
    
        render = web.template.render('templates', base='layout')
    """
    def __init__(self, loc='templates', cache=None, base=None, **keywords):
        self._loc = loc
        self._keywords = keywords

        if cache is None:
            cache = not config.get('debug', False)
        
        if cache:
            self._cache = {}
        else:
            self._cache = None
        
        if base and not hasattr(base, '__call__'):
            # make base a function, so that it can be passed to sub-renders
            self._base = lambda page: self._template(base)(page)
        else:
            self._base = base
            
    def _lookup(self, name):
        path = os.path.join(self._loc, name)
        if os.path.isdir(path):
            return 'dir', path
        else:
            path = self._findfile(path)
            if path:
                return 'file', path
            else:
                return 'none', None
        
    def _load_template(self, name):
        kind, path = self._lookup(name)
        
        if kind == 'dir':
            return Render(path, cache=self._cache is not None, base=self._base, **self._keywords)
        elif kind == 'file':
            return Template(open(path).read(), filename=path, **self._keywords)
        else:
            raise AttributeError, "No template named " + name            

    def _findfile(self, path_prefix): 
        p = [f for f in glob.glob(path_prefix + '.*') if not f.endswith('~')] # skip backup files
        return p and p[0]
            
    def _template(self, name):
        if self._cache is not None:
            if name not in self._cache:
                self._cache[name] = self._load_template(name)
            return self._cache[name]
        else:
            return self._load_template(name)
        
    def __getattr__(self, name):
        t = self._template(name)
        if self._base and isinstance(t, Template):
            def template(*a, **kw):
                return self._base(t(*a, **kw))
            return template
        else:
            return self._template(name)

class GAE_Render(Render):
    # Render gets over-written. make a copy here.
    super = Render
    def __init__(self, loc, *a, **kw):
        GAE_Render.super.__init__(self, loc, *a, **kw)
        
        import types
        if isinstance(loc, types.ModuleType):
            self.mod = loc
        else:
            name = loc.rstrip('/').replace('/', '.')
            self.mod = __import__(name, None, None, ['x'])

        self.mod.__dict__.update(kw.get('builtins', TEMPLATE_BUILTINS))
        self.mod.__dict__.update(Template.globals)
        self.mod.__dict__.update(kw.get('globals', {}))

    def _load_template(self, name):
        t = getattr(self.mod, name)
        import types
        if isinstance(t, types.ModuleType):
            return GAE_Render(t, cache=self._cache is not None, base=self._base, **self._keywords)
        else:
            return t

render = Render
# setup render for Google App Engine.
try:
    from google import appengine
    render = Render = GAE_Render
except ImportError:
    pass
        
def frender(path, **keywords):
    """Creates a template from the given file path.
    """
    return Template(open(path).read(), filename=path, **keywords)
    
def compile_templates(root):
    """Compiles templates to python code."""
    re_start = re_compile('^', re.M)
    
    for dirpath, dirnames, filenames in os.walk(root):
        filenames = [f for f in filenames if not f.startswith('.') and not f.endswith('~') and not f.startswith('__init__.py')]

        for d in dirnames[:]:
            if d.startswith('.'):
                dirnames.remove(d) # don't visit this dir

        out = open(os.path.join(dirpath, '__init__.py'), 'w')
        out.write('from web.template import CompiledTemplate, ForLoop\n\n')
        if dirnames:
            out.write("import " + ", ".join(dirnames))

        for f in filenames:
            path = os.path.join(dirpath, f)

            if '.' in f:
                name, _ = f.split('.', 1)
            else:
                name = f
                
            text = open(path).read()
            text = Template.normalize_text(text)
            code = Template.generate_code(text, path)
            code = re_start.sub('    ', code)
                        
            _gen = '' + \
            '\ndef %s():' + \
            '\n    loop = ForLoop()' + \
            '\n    _dummy  = CompiledTemplate(lambda: None, "dummy")' + \
            '\n    join_ = _dummy._join' + \
            '\n    escape_ = _dummy._escape' + \
            '\n' + \
            '\n%s' + \
            '\n    return __template__'
            
            gen_code = _gen % (name, code)
            out.write(gen_code)
            out.write('\n\n')
            out.write('%s = CompiledTemplate(%s(), %s)\n\n' % (name, name, repr(path)))

            # create template to make sure it compiles
            t = Template(open(path).read(), path)
        out.close()
                
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

class TemplateResult(storage):
    """Dictionary like object for storing template output.
    
    A template can specify key-value pairs in the output using 
    `var` statements. Each `var` statement adds a new key to the 
    template output and the main output is stored with key 
    __body__.
    
        >>> d = TemplateResult(__body__='hello, world', x='foo')
        >>> d
        <TemplateResult: {'__body__': 'hello, world', 'x': 'foo'}>
        >>> print d
        hello, world
    """
    def __unicode__(self): 
        return safeunicode(self.get('__body__', ''))
    
    def __str__(self):
        return safestr(self.get('__body__', ''))
        
    def __repr__(self):
        return "<TemplateResult: %s>" % dict.__repr__(self)
    
def test():
    r"""Doctest for testing template module.

    Define a utility function to run template test.
    
        >>> class TestResult(TemplateResult):
        ...     def __repr__(self): return repr(unicode(self))
        ...
        >>> def t(code, **keywords):
        ...     tmpl = Template(code, **keywords)
        ...     return lambda *a, **kw: TestResult(tmpl(*a, **kw))
        ...
    
    Simple tests.
    
        >>> t('1')()
        u'1\n'
        >>> t('$def with ()\n1')()
        u'1\n'
        >>> t('$def with (a)\n$a')(1)
        u'1\n'
        >>> t('$def with (a=0)\n$a')(1)
        u'1\n'
        >>> t('$def with (a=0)\n$a')(a=1)
        u'1\n'
    
    Test complicated expressions.
        
        >>> t('$def with (x)\n$x.upper()')('hello')
        u'HELLO\n'
        >>> t('$(2 * 3 + 4 * 5)')()
        u'26\n'
        >>> t('${2 * 3 + 4 * 5}')()
        u'26\n'
        >>> t('$def with (limit)\nkeep $(limit)ing.')('go')
        u'keep going.\n'
        >>> t('$def with (a)\n$a.b[0]')(storage(b=[1]))
        u'1\n'
        
    Test html escaping.
    
        >>> t('$def with (x)\n$x', filename='a.html')('<html>')
        u'&lt;html&gt;\n'
        >>> t('$def with (x)\n$x', filename='a.txt')('<html>')
        u'<html>\n'
                
    Test if, for and while.
    
        >>> t('$if 1: 1')()
        u'1\n'
        >>> t('$if 1:\n    1')()
        u'1\n'
        >>> t('$if 1:\n    1\\')()
        u'1'
        >>> t('$if 0: 0\n$elif 1: 1')()
        u'1\n'
        >>> t('$if 0: 0\n$elif None: 0\n$else: 1')()
        u'1\n'
        >>> t('$if 0 < 1 and 1 < 2: 1')()
        u'1\n'
        >>> t('$for x in [1, 2, 3]: $x')()
        u'1\n2\n3\n'
        >>> t('$def with (d)\n$for k, v in d.iteritems(): $k')({1: 1})
        u'1\n'
        >>> t('$for x in [1, 2, 3]:\n\t$x')()
        u'    1\n    2\n    3\n'
        >>> t('$def with (a)\n$while a and a.pop():1')([1, 2, 3])
        u'1\n1\n1\n'

    The space after : must be ignored.
    
        >>> t('$if True: foo')()
        u'foo\n'
    
    Test loop.xxx.

        >>> t("$for i in range(5):$loop.index, $loop.parity")()
        u'1, odd\n2, even\n3, odd\n4, even\n5, odd\n'
        >>> t("$for i in range(2):\n    $for j in range(2):$loop.parent.parity $loop.parity")()
        u'odd odd\nodd even\neven odd\neven even\n'
        
    Test assignment.
    
        >>> t('$ a = 1\n$a')()
        u'1\n'
        >>> t('$ a = [1]\n$a[0]')()
        u'1\n'
        >>> t('$ a = {1: 1}\n$a.keys()[0]')()
        u'1\n'
        >>> t('$ a = []\n$if not a: 1')()
        u'1\n'
        >>> t('$ a = {}\n$if not a: 1')()
        u'1\n'
        >>> t('$ a = -1\n$a')()
        u'-1\n'
        >>> t('$ a = "1"\n$a')()
        u'1\n'

    Test comments.
    
        >>> t('$# 0')()
        u'\n'
        >>> t('hello$#comment1\nhello$#comment2')()
        u'hello\nhello\n'
        >>> t('$#comment0\nhello$#comment1\nhello$#comment2')()
        u'\nhello\nhello\n'
        
    Test unicode.
    
        >>> t('$def with (a)\n$a')(u'\u203d')
        u'\u203d\n'
        >>> t('$def with (a)\n$a')(u'\u203d'.encode('utf-8'))
        u'\u203d\n'
        >>> t(u'$def with (a)\n$a $:a')(u'\u203d')
        u'\u203d \u203d\n'
        >>> t(u'$def with ()\nfoo')()
        u'foo\n'
        >>> def f(x): return x
        ...
        >>> t(u'$def with (f)\n$:f("x")')(f)
        u'x\n'
        >>> t('$def with (f)\n$:f("x")')(f)
        u'x\n'
    
    Test dollar escaping.
    
        >>> t("Stop, $$money isn't evaluated.")()
        u"Stop, $money isn't evaluated.\n"
        >>> t("Stop, \$money isn't evaluated.")()
        u"Stop, $money isn't evaluated.\n"
        
    Test space sensitivity.
    
        >>> t('$def with (x)\n$x')(1)
        u'1\n'
        >>> t('$def with(x ,y)\n$x')(1, 1)
        u'1\n'
        >>> t('$(1 + 2*3 + 4)')()
        u'11\n'
        
    Make sure globals are working.
            
        >>> t('$x')()
        Traceback (most recent call last):
            ...
        NameError: global name 'x' is not defined
        >>> t('$x', globals={'x': 1})()
        u'1\n'
        
    Can't change globals.
    
        >>> t('$ x = 2\n$x', globals={'x': 1})()
        u'2\n'
        >>> t('$ x = x + 1\n$x', globals={'x': 1})()
        Traceback (most recent call last):
            ...
        UnboundLocalError: local variable 'x' referenced before assignment
    
    Make sure builtins are customizable.
    
        >>> t('$min(1, 2)')()
        u'1\n'
        >>> t('$min(1, 2)', builtins={})()
        Traceback (most recent call last):
            ...
        NameError: global name 'min' is not defined
        
    Test vars.
    
        >>> x = t('$var x: 1')()
        >>> x.x
        u'1'
        >>> x = t('$var x = 1')()
        >>> x.x
        1
        >>> x = t('$var x:  \n    foo\n    bar')()
        >>> x.x
        u'foo\nbar\n'

    Test BOM chars.

        >>> t('\xef\xbb\xbf$def with(x)\n$x')('foo')
        u'foo\n'

    Test for with weird cases.

        >>> t('$for i in range(10)[1:5]:\n    $i')()
        u'1\n2\n3\n4\n'
        >>> t("$for k, v in {'a': 1, 'b': 2}.items():\n    $k $v")()
        u'a 1\nb 2\n'
        >>> t("$for k, v in ({'a': 1, 'b': 2}.items():\n    $k $v")()
        Traceback (most recent call last):
            ...
        SyntaxError: invalid syntax

    Test datetime.

        >>> import datetime
        >>> t("$def with (date)\n$date.strftime('%m %Y')")(datetime.datetime(2009, 1, 1))
        u'01 2009\n'
    """
    pass
            
if __name__ == "__main__":
    import sys
    if '--compile' in sys.argv:
        compile_templates(sys.argv[2])
    else:
        import doctest
        doctest.testmod()
