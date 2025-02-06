import unittest

import web
from web.template import ExpressionNode, Parser, SecurityError, Template


class TestItem:
    __test__ = False  # silence collection warning from test framework

    def __init__(self):
        self.id = 12345


class _TestResult:
    def __init__(self, t):
        self.t = t

    def __getattr__(self, name):
        return getattr(self.t, name)

    def __repr__(self):
        return repr(str(self.t))


def t(code, **keywords):
    tmpl = Template(code, **keywords)
    return lambda *a, **kw: _TestResult(tmpl(*a, **kw))


class TemplateTest(unittest.TestCase):
    """Tests for the template security feature."""

    def testPrint(self):
        tpl = "$code:\n    print('blah')"
        self.assertRaises(NameError, t(tpl))

    def testAttr(self):
        tpl = "$code:\n    (lambda x: x+1).func_code"
        self.assertRaises(SecurityError, t, tpl)

        tpl = "$def with (a)\n$code:\n    a.b = 3"
        self.assertRaises(SecurityError, t, tpl)

        # these two should execute themselves flawlessly
        t("$code:\n    foo = {'a': 1}.items()")()
        t("$code:\n    bar = {k:0 for k in [1,2,3]}")()

    def test_overridden(self):
        tpl = "$print('blah')"
        f = t(tpl, globals={"print": lambda x: x})
        assert repr(f()) == "'blah\\n'"

    def test_quotes(self):
        template = 'a="$foo" <p>'
        f = t(template, globals={"foo": "bar"})
        assert repr(f()) == "'a=\"bar\" <p>\\n'"

    def test_accessor(self):
        template = 'a="$foo.id"<p>'
        f = t(template, globals={"foo": TestItem()})
        assert repr(f()) == "'a=\"12345\"<p>\\n'"

    def test_href(self):
        template = '<a href="/del/$item.id">Delete</a>'
        f = t(template, globals={"item": TestItem()})
        assert repr(f()) == "'<a href=\"/del/12345\">Delete</a>\\n'"

    def testImportMustFail(self):
        tpl = "${__import__('os').getpwd()}"
        self.assertRaises(SecurityError, t, tpl)

    def test_SecutityError_name(self):
        tpl = "$__special_name"
        self.assertRaises(SecurityError, Template, tpl)

        tpl = "${__special_name}"
        self.assertRaises(SecurityError, Template, tpl)

        tpl = "$var foo = __special_name"
        self.assertRaises(SecurityError, Template, tpl)

    def test_SecutityError_attr(self):
        tpl = "$foo._private"
        self.assertRaises(SecurityError, Template, tpl)

        tpl = "$foo()._private"
        self.assertRaises(SecurityError, Template, tpl)

    def test_SecutityError_not_allowed_nodes(self):
        tpl = "$code: import os"
        self.assertRaises(SecurityError, Template, tpl)

        tpl = "$code: raise Exception('x')"
        self.assertRaises(SecurityError, Template, tpl)


class TestParser(unittest.TestCase):
    """
    Test the Parser.

    Tests functions from the Parser class as if the following template were loaded:

    test_template = '''$def with (back, docs)
    $var title: Index
    <p><a href="$back">&larr; Back to Index</a></p>
    <ul>
    $for path, title in docs:
        <li><a href="$path">$title</a></li>
    </ul>
    '''
    """

    def test_read_expr(self) -> None:
        """
        Test Parser.read_expr() with the `text` values it would get from
        `Parser.read_node(), if processing `test_template`.
        """
        got = Parser().read_expr('back">&larr; Back to Index</a></p>\n')
        expression_node = got[0]
        assert isinstance(expression_node, ExpressionNode)
        assert repr(expression_node) == "$back"
        assert got[1] == '">&larr; Back to Index</a></p>\n'

        got = Parser().read_expr('path">$title</a></li>\n')
        expression_node = got[0]
        assert isinstance(expression_node, ExpressionNode)
        assert repr(expression_node) == "$path"
        assert got[1] == '">$title</a></li>\n'

        got = Parser().read_expr("title</a></li>\n")
        expression_node = got[0]
        assert isinstance(expression_node, ExpressionNode)
        assert repr(expression_node) == "$title"
        assert got[1] == "</a></li>\n"


class TestRender:
    def test_template_without_ext(self, tmpdir):
        tmpdir.join("foobar").write("hello")
        render = web.template.render(str(tmpdir))
        assert str(render.foobar()).strip() == "hello"
