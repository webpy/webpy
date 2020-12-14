import web.net
import web
import web.db
import web.py3helpers
import web.utils
import web.webapi
import web.debugerror
import web.template
import web.form
import web.http
import web.httpserver
import web.session
import web.wsgi
import web.application
import web.browser


def test_urlquote_0():
    ret = web.net.urlquote(None)
    assert ret is not None


def test_websafe_0():
    ret = web.net.websafe(None)
    assert ret is not None


def test_htmlunquote_0():
    try:
        web.net.htmlunquote(None)
    except Exception as e:
        assert isinstance(e, AttributeError)


def test_httpdate_0():
    try:
        web.net.httpdate(None)
    except Exception as e:
        assert isinstance(e, AttributeError)


def test_parsehttpdate_0():
    try:
        web.net.parsehttpdate(None)
    except Exception as e:
        assert isinstance(e, TypeError)


def test_validipaddr_0():
    try:
        web.net.validipaddr(None)
    except Exception as e:
        assert isinstance(e, AttributeError)


def test_validipport_0():
    try:
        web.net.validipport(None)
    except Exception as e:
        assert isinstance(e, TypeError)
