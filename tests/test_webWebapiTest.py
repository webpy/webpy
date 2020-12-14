import web.webapi
import web
import web.db
import web.py3helpers
import web.utils
import web.debugerror
import web.net
import web.template
import web.form
import web.http
import web.httpserver
import web.session
import web.wsgi
import web.application
import web.browser


def test_init_NotModified_0():
    var = web.webapi.NotModified()
    ret = var
    assert isinstance(ret, web.webapi.NotModified)


def test_debug_0():
    ret = web.webapi.debug(None)
    assert ret is not None


def test_init_Accepted_0():
    try:
        var = web.webapi.Accepted(r"Accepted", None)
        var
    except Exception as e:
        assert isinstance(e, AttributeError)


def test_init_BadRequest_0():
    try:
        var = web.webapi.BadRequest(None)
        var
    except Exception as e:
        assert isinstance(e, AttributeError)


def test_init_Conflict_0():
    try:
        var = web.webapi.Conflict(None)
        var
    except Exception as e:
        assert isinstance(e, AttributeError)


def test_init_Forbidden_0():
    try:
        var = web.webapi.Forbidden(None)
        var
    except Exception as e:
        assert isinstance(e, AttributeError)


def test_init_Found_0():
    try:
        var = web.webapi.Found(None, False)
        var
    except Exception as e:
        assert isinstance(e, AttributeError)


def test_init_Gone_0():
    try:
        var = web.webapi.Gone(None)
        var
    except Exception as e:
        assert isinstance(e, AttributeError)


def test_init_NotAcceptable_0():
    try:
        var = web.webapi.NotAcceptable(None)
        var
    except Exception as e:
        assert isinstance(e, AttributeError)


def test_init_PreconditionFailed_0():
    try:
        var = web.webapi.PreconditionFailed(None)
        var
    except Exception as e:
        assert isinstance(e, AttributeError)


def test_init_TempRedirect_0():
    try:
        var = web.webapi.TempRedirect(None, False)
        var
    except Exception as e:
        assert isinstance(e, AttributeError)


def test_init_Unauthorized_0():
    try:
        var = web.webapi.Unauthorized(None)
        var
    except Exception as e:
        assert isinstance(e, AttributeError)


def test_init_UnsupportedMediaType_0():
    try:
        var = web.webapi.UnsupportedMediaType(None)
        var
    except Exception as e:
        assert isinstance(e, AttributeError)


def test_init__InternalError_0():
    try:
        var = web.webapi._InternalError(None)
        var
    except Exception as e:
        assert isinstance(e, AttributeError)


def test_init__UnavailableForLegalReasons_0():
    try:
        var = web.webapi._UnavailableForLegalReasons(None)
        var
    except Exception as e:
        assert isinstance(e, AttributeError)


def test_InternalError_0():
    try:
        web.webapi.InternalError(None)
    except Exception as e:
        assert isinstance(e, AttributeError)


def test_NotFound_0():
    try:
        web.webapi.NotFound(None)
    except Exception as e:
        assert isinstance(e, AttributeError)


def test_UnavailableForLegalReasons_0():
    try:
        web.webapi.UnavailableForLegalReasons(None)
    except Exception as e:
        assert isinstance(e, AttributeError)
