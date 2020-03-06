import unittest

import web
from web.py3helpers import PY2
from web.template import SecurityError, Template

try:
    unicode  # Python 2
except NameError:
    unicode = str  # Python 3


class _TestResult:
    def __init__(self, t):
        self.t = t

    def __getattr__(self, name):
        return getattr(self.t, name)

    def __repr__(self):
        return repr(unicode(self.t))


def t(code, **keywords):
    tmpl = Template(code, **keywords)
    return lambda *a, **kw: _TestResult(tmpl(*a, **kw))


class TemplateTest(unittest.TestCase):
    """Tests for the template security feature."""

    def testPrint(self):
        if PY2:
            tpl = "$code:\n    print 'blah'"
            # print_function has been imported from __future__ so the print statement doesn't exist anymore
            self.assertRaises(SyntaxError, t, tpl)
        else:
            tpl = "$code:\n    print('blah')"
            self.assertRaises(NameError, t(tpl))

    def testRepr(self):
        if PY2:  # this feature doesn't exist in Py3 anymore
            tpl = "$code:\n    `1`"
            self.assertRaises(SecurityError, t, tpl)

    def testAttr(self):
        tpl = "$code:\n    (lambda x: x+1).func_code"
        self.assertRaises(SecurityError, t, tpl)

        tpl = "$def with (a)\n$code:\n    a.b = 3"
        self.assertRaises(SecurityError, t, tpl)

        # these two should execute themselves flawlessly
        t("$code:\n    foo = {'a': 1}.items()")()
        if not PY2:
            t("$code:\n    bar = {k:0 for k in [1,2,3]}")()


class TestRender:
    def test_template_without_ext(self, tmpdir):
        tmpdir.join("foobar").write("hello")
        render = web.template.render(str(tmpdir))
        assert str(render.foobar()).strip() == "hello"
