import web.application
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
import web.wsgi
import web.browser


def test_handle_with_processors_auto_application_0():
    try:
        var = web.application.auto_application()
        var.handle_with_processors()
    except Exception as e:
        assert isinstance(e, AttributeError)
