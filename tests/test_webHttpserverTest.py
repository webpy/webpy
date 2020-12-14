import web.httpserver
import web
import web.db
import web.py3helpers
import web.utils
import web.webapi
import web.debugerror
import web.net
import web.template
import web.form
import web.http
import web.session
import web.wsgi
import web.application
import web.browser


def test_init_StaticApp_0():
    var = web.httpserver.StaticApp(None, None)
    ret = var
    assert isinstance(ret, web.httpserver.StaticApp)


def test_end_headers_StaticApp_0():
    var = web.httpserver.StaticApp(None, None)
    ret = var.end_headers()
    assert ret is None


def test_log_error_StaticApp_0():
    var = web.httpserver.StaticApp(None, None)
    ret = var.log_error(None, None)
    assert ret is None


def test_send_header_StaticApp_0():
    var = web.httpserver.StaticApp(None, None)
    ret = var.send_header(None, None)
    assert ret is None


def test_call_LogMiddleware_0():
    try:
        var = web.httpserver.LogMiddleware(None)
        var.__call__(None, None)
    except Exception as e:
        assert isinstance(e, TypeError)


def test_log_LogMiddleware_0():
    try:
        var = web.httpserver.LogMiddleware(None)
        var.log(None, None)
    except Exception as e:
        assert isinstance(e, AttributeError)


def test_send_error_StaticApp_0():
    try:
        var = web.httpserver.StaticApp(None, None)
        var.send_error(None, None, None)
    except Exception as e:
        assert isinstance(e, TypeError)


def test_call_StaticMiddleware_0():
    try:
        var = web.httpserver.StaticMiddleware(None, r"/static/")
        var.__call__(None, None)
    except Exception as e:
        assert isinstance(e, AttributeError)


def test_normpath_StaticMiddleware_0():
    try:
        var = web.httpserver.StaticMiddleware(None, r"/static/")
        var.normpath(None)
    except Exception as e:
        assert isinstance(e, TypeError)


def test_runbasic_0():
    try:
        web.httpserver.runbasic(None, None)
    except Exception as e:
        assert isinstance(e, ModuleNotFoundError)
