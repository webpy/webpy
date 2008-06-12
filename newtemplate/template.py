import tokenize
from web import storage

DEBUG = True

def read_nodelist(text):
    r"""    
        >>> read_nodelist('hello $name\nhow are you\n')
        [<text: 'hello '>, <expr: name>, <newline>, <text: 'how are you'>, <newline>]
    """
    nodes = []
    while True:
        if not text:
            break
        node, text = read_node(text)
        nodes.append(node)
    return nodes
    
def read_node(text):
    r"""Reads a node.
    
    >>> read_node('hello $name')
    (<text: 'hello '>, '$name')
    >>> read_node('\nhello $name')
    (<newline>, 'hello $name')
    >>> read_node('$name')
    (<expr: name>, '')
    """
    if text.startswith('\n'):
        return NewLineNode(), text[1:]
    elif text.startswith('$'):
        text = text[1:] # strip $
        ahead = python_lookahead(text)
        if ahead in STATEMENT_KEYWORDS:
            return read_statement(text)
        elif ahead.strip() == '':
            # assignments starts with a space after $
            # ex: $ a = b + 2
            return read_assignment(text)
        else:
            return read_expr(text)
    else:
        return read_text(text)

STATEMENT_KEYWORDS = ['for', 'if', 'elif', 'else']
        
def read_statement(text):
    """Reads a python statement.
    A python statement always ends with token ':'.
    """
    readline = iter([text]).next
    tokens = tokenize.generate_tokens(readline)
    end = None
    for type, t, begin, end, line in tokens:
        if t == ':':
            break
    row, col = end
    stmt, text = text[:col], text[col:]
    block, text = read_block(text)
    nodelist = read_nodelist(block)
    
    #@@ hack
    if isinstance(nodelist[0], NewLineNode):
        nodelist[0].emit_code = False
    
    if stmt.startswith('for'):
        return ForNode(stmt, nodelist), text
    elif stmt.startswith('if'):
        return IfNode(stmt, nodelist), text
    elif stmt.startswith('else'):
        return ElseNode(stmt, nodelist), text
    else:
        assert False, "unknown statement: %s" % (repr(stmt))
    
def read_block(text):
    # any expression left in the same line of the statement.
    leftover = text.split('\n')[0].strip()
    
    # block is specified in the same line if there any leftover.
    if leftover != '':
        return read_till_eol(text)
    else:
        return read_indented_block(text.lstrip('\n'), '    ')
        
def read_indented_block(text, indent):
    r"""Read a block of text. A block is what typically follows a for or it statement.
    It can be in the same line as that of the statement or an indented block.

        >>> read_indented_block('  a\n  b\nc', '  ')
        ('a\nb\n', 'c')
        >>> read_indented_block('  a\n    b\n  c\nd', '  ')
        ('a\n  b\nc\n', 'd')
    """
    token = "\n"
    while True:
        line, left = read_till_eol(text)
        if line.startswith(indent):
            token += line[len(indent):]
            text = left
        else:
            break
    return token, text
        
def read_till_eol(text):
    r"""Read till end of line.

        >>> read_till_eol('a\nb')
        ('a\n', 'b')
        >>> read_till_eol('\nb')
        ('\n', 'b')
    """
    token, text = safesplit(text, '\n', 1)
    return token + '\n', text

def safesplit(text, sep, split_count=1):
    """Splits the text in to specified number of tokens using the sep.

        >>> safesplit('a.b.c', '.', 1)
        ['a', 'b.c']
        >>> safesplit('a.b.c', '.', 4)
        ['a', 'b', 'c', '', '']
    """
    tokens = text.split(sep, split_count)
    tokens += [''] * (split_count - len(tokens) + 1)
    return tokens    
    
def python_lookahead(text):
    """Returns the first python token from the given text.
    
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

def read_text(text):
    r"""Reads a text node from the given text.
    
        >>> read_text('hello\nworld')
        (<text: 'hello'>, '\nworld')
        >>> read_text('hello $name')
        (<text: 'hello '>, '$name')
    """
    for i, c in enumerate(text):
        if c in '$\n':
            return TextNode(text[:i]), text[i:]
    else:
        return TextNode(text), ''

def read_expr(text):
    """Reads a python expression from the text and returns the expression and remaining text.

    expr -> simple_expr | paren_expr
    simple_expr -> id extended_expr
    extended_expr -> attr_access | paren_expr extended_expr | ''
    attr_access -> dot id extended_expr
    paren_expr -> [ tokens ] | ( tokens ) | { tokens }
 
        >>> read_expr("a.b and c")
        ('a.b', ' and c')
        >>> read_expr("a. b")
        ('a', '. b')
        >>> read_expr("name</h1>")
        ('name', '</h1>')
        >>> read_expr("(limit)ing")
        ('(limit)', 'ing')
        >>> read_expr('a[1, 2][:3].f(1+2, "weird string[).", 3 + 4) done.')
        ('a[1, 2][:3].f(1+2, "weird string[).", 3 + 4)', ' done.')
    """
    def simple_expr():
        identifier()
        extended_expr()
    
    def identifier():
        tokens.next()
    
    def extended_expr():
        lookahead = tokens.lookahead()
        if lookahead.value == '.':
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
                self.items.append(self.iteritems.next())
            return self.items[self.position]
            
        def lookahead2(self):
            if len(self.items) <= self.position+1:
                self.items.append(self.iteritems.next())
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
    return ExpressionNode(text[:col]), text[col:]        
        
class TextNode:
    def __init__(self, value):
        self.value = value

    def emit(self, indent):
        return "write(" + repr(self.value) + ");"
        
    def text(self):
        return self.value

    def __repr__(self):
        return "<text: %s>" % repr(self.value)
        
class NewLineNode:
    def __init__(self, emit_code=True):
        self.emit_code = emit_code

    def emit(self, indent):
        if self.emit_code:
            return "write('\\n');\n" + indent 
        else:
            return "\n" + indent

    def text(self):
        return "\n"

    def __repr__(self):
        return "<newline>"

class ExpressionNode:
    def __init__(self, value):
        self.value = value

    def emit(self, indent):
        return "write(" + self.value + ");"
        
    def text(self):
        return "${" + self.value + "}"
        
    def __repr__(self):
        return "<expr: %s>" % self.value
        
class BlockNode:
    def __init__(self, stmt, nodelist):
        self.stmt = stmt
        self.nodelist = nodelist

    def emit(self, indent):
        indent = indent + "    "
        out = self.stmt
        for i, node in enumerate(self.nodelist):
            if i == len(self.nodelist)-1 and isinstance(node, NewLineNode):
                #@@ Hack to fix additional indentation caused by the last newline.
                out += node.emit(indent[4:])
            else:
                out += node.emit(indent)
        return out
        
    def text(self):
        return '${' + self.stmt + '}' + "".join(node.text(indent) for node in self.nodes)
        
    def __repr__(self):
        return "<block: %s %s>" % (self.stmt, repr(self.nodelist))

class ForNode(BlockNode):
    pass

class IfNode(BlockNode):
    pass

class ElseNode(BlockNode):
    pass
    
class NodeList:
    def __init__(self, nodes):
        self.nodes = nodes

    def emit(self, indent):
        return "".join(node.emit(indent) for node in self.nodes)

    def text(self):
        return "".join(node.text() for node in self.nodes)

    def __repr__(self):
        return "[" + ",".join(repr(node) for node in self.nodes) + "]"

def parse(text):
    nodes = read_nodelist(text)
    return NodeList(nodes)

def safe_compile(code, filename):
    import safe, compiler
    ast = compiler.parse(code)
    checker = safe.SafeEvalVisitor()
    if not checker.walk(ast):
        raise safe.SafeEvalCodeException(code, checker.errors)
    return compile(code, filename, 'exec')
                    
def compile_template(template_string, filename='unknown'):
    nodelist = parse(template_string)
    code = nodelist.emit(indent="")
    if DEBUG:
        print '# generated code'
        print code
        print '# end\n'

    return safe_compile(code, filename)

def make_env(env):
    from cStringIO import StringIO
    f = StringIO()
    class Env(dict):
        pass
        
    env = Env(env)
    env.file = f
    def write(value):
        if value is not None: 
            f.write(str(value))
    env['write'] = write    
    return env

def execute_template(code, **env):
    env = make_env(env)
    exec(code, env)
    return env.file.getvalue()

def frender(filename, **kw):
    t = compile_template(open(filename).read(), filename)
    return execute_template(t, **kw)
    
if __name__ == "__main__":
    import sys

    args = sys.argv[1:] or ["hello.html"]    
    print frender(args[0], name='web.py', n=3)
