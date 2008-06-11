"""
Template design:

Template string is split into tokens and the tokens are combined into nodes. 
Parse tree is a nodelist. TextNode and ExpressionNode are simple nodes and 
for-loop, if-loop etc are block nodes, which contain multiple child nodes. 

Each node can emit some python string. python string emitted by the 
root node is validated for safeeval and executed using python in the given environment.

Enough care is taken to make sure the generated code and the template has line to line match, 
so that the error messages can point to exact line number in template. (It doesn't work in some cases still.)

TODOs:
    * The current implementation expects python expressions and statements in ${...}. This constraint should be removed.
    * Remove `$end`s
    * support for `$def with` and ability to call it like function
    * support for $:
    * take care of unicode issues
"""
import web
import re

class TextNode:
    def __init__(self, value):
        self.value = value

    def emit(self, indent):
        n = self.value.count("\n")
        return indent + "write(" + repr(self.value) + ");" + "\n" * n
    
    def text(self):
        return self.value
        
    def __repr__(self):
        return "<text: %s>" % repr(self.value)

class ExpressionNode:
    def __init__(self, value):
        self.value = value

    def emit(self, indent):
        return indent + "write(" + self.value + ");"
        
    def text(self):
        return "${" + self.value + "}"
        
    def __repr__(self):
        return "<expr: %s>" % self.value

class NodeList:
    def __init__(self, nodes):
        self.nodes = nodes

    def emit(self, indent):
        return "".join(node.emit(indent) for node in self.nodes)
        
    def text(self):
        return "".join(node.text() for node in self.nodes)

    def __repr__(self):
        return "[" + ",".join(repr(node) for node in self.nodes) + "]"

class BlockNode:
    def __init__(self, stmt, nodelist):
        self.stmt = stmt
        self.nodelist = nodelist

    def emit(self, indent):
        out = indent + self.stmt + "\n"
        indent = indent + "    "
        for node in self.nodelist:
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

class DefNode(BlockNode):
    pass

class PydefNode(BlockNode):
    def emit(self, indent):
        return indent + self.stmt.replace('pydef', 'def') + NodeList(self.nodelist).text()

class BeginNode(BlockNode):
    pass

blocks = {
    "begin": BeginNode,
    "for": ForNode,
    "if": IfNode,
    "def": DefNode,
    "pydef": PydefNode,
}

re_tokenize = re.compile('(\${[^{}]*})')

def tokenize(text):
    """Tokenizes the given text.

        >>> tokenize("hello ${name}!")
        ['hello ', '${name}', '!']
    """
    return re_tokenize.split(text)

def parse(tokens):
    """Parses the given tokens into nodelist.

        >>> parse(tokenize("hello ${name}!"))
        [<text: 'hello '>, <expr: name>, <text: '!'>]
    """
    def consume(tokens):
        """Consumes a node from and adds that to nodelist."""
        try:
            t = tokens.next()
        except StopIteration:
            return None
            
        if not t.startswith('$'):
            return TextNode(t)
        else:
            t = t[2:-1] # strip ${ and }
            for keyword, cls in blocks.items():
                if t.startswith(keyword):
                    nodes = consume_nodelist(tokens)
                    return cls(t, nodes)
            else:
                if t == 'end':
                    return None
                else:
                    return ExpressionNode(t)

    def consume_nodelist(tokens):
        """consumes blocks till it reaches end token."""
        nodes = []
        while True:
            node = consume(tokens)
            if node is None:
                break
            nodes.append(node)
        return nodes

    return NodeList(consume_nodelist(iter(tokens)))

def safe_compile(code, filename):
    import safe, compiler
    ast = compiler.parse(code)
    checker = safe.SafeEvalVisitor()
    if not checker.walk(ast):
        raise safe.SafeEvalCodeException(code, checker.errors)
    return compile(code, filename, 'exec')
                    
def compile_template(template_string, filename='unknown'):
    tokens = tokenize(template_string)
    nodelist = parse(tokens)
    code = nodelist.emit(indent="")
    return safe_compile(code, filename)

def make_env(env):
    from cStringIO import StringIO
    f = StringIO()
    env['_f'] = f
    def write(value):
        if value is not None: 
            f.write(str(value))
    env['write'] = write
    return env

def execute_template(code, **env):
    env = make_env(env)
    exec(code, env)
    return env['_f'].getvalue()

def frender(filename, **kw):
    t = compile_template(open(filename).read(), filename)
    return execute_template(t, **kw)
    
if __name__ == "__main__":
    #import doctest, sys
    #doctest.testmod()
    print frender('hello.html', name='web.py')
 
