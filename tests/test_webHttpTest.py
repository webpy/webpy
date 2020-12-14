import web.http
import web
import web.db
import web.py3helpers
import web.utils
import web.webapi
import web.debugerror
import web.net
import web.template
import web.form
import web.httpserver
import web.session
import web.wsgi
import web.application
import web.browser


def test_expires_0():
    try:
        web.http.expires(None)
    except Exception as e:
        assert isinstance(e, TypeError)


def test_lastmodified_0():
    try:
        web.http.lastmodified(None)
    except Exception as e:
        assert isinstance(e, AttributeError)


def test_modified_0():
    try:
        web.http.modified(None, None)
    except Exception as e:
        assert isinstance(e, AttributeError)


def test_prefixurl_0():
    try:
        web.http.prefixurl(None)
    except Exception as e:
        assert isinstance(e, AttributeError)


def test_profiler_0():
    try:
        web.http.profiler(None)
    except Exception as e:
        assert isinstance(e, ModuleNotFoundError)
