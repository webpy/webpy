import web.debugerror
import web
import web.db
import web.py3helpers
import web.utils
import web.webapi
import web.net
import web.template
import web.form
import web.http
import web.httpserver
import web.session
import web.wsgi
import web.application
import web.browser


def test_debugerror_0():
    try:
        web.debugerror.debugerror()
    except Exception as e:
        assert isinstance(e, AttributeError)
