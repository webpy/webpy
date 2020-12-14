import web.wsgi
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
import web.httpserver
import web.session
import web.application
import web.browser


def test_runfcgi_0():
    try:
        web.wsgi.runfcgi(None, None)
    except Exception as e:
        assert isinstance(e, ModuleNotFoundError)


def test_runscgi_0():
    try:
        web.wsgi.runscgi(None, None)
    except Exception as e:
        assert isinstance(e, ModuleNotFoundError)
