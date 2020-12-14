import web.session
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
import web.wsgi
import web.application
import web.browser


def test_contains_Session_0():
    var = web.session.Session(None, None, None)
    ret = var.__contains__(None)
    assert ret is not None


def test_init_SessionExpired_0():
    var = web.session.SessionExpired(None)
    ret = var
    assert isinstance(ret, web.session.SessionExpired)


def test_init_ShelfStore_0():
    var = web.session.ShelfStore(None)
    ret = var
    assert isinstance(ret, web.session.ShelfStore)


def test_getitem_DBStore_0():
    try:
        var = web.session.DBStore(None, None)
        var.__getitem__(None)
    except Exception as e:
        assert isinstance(e, AttributeError)


def test_delattr_Session_0():
    try:
        var = web.session.Session(None, None, None)
        var.__delattr__(None)
    except Exception as e:
        assert isinstance(e, TypeError)


def test_expired_Session_0():
    try:
        var = web.session.Session(None, None, None)
        var.expired()
    except Exception as e:
        assert isinstance(e, KeyError)


def test_contains_ShelfStore_0():
    try:
        var = web.session.ShelfStore(None)
        var.__contains__(None)
    except Exception as e:
        assert isinstance(e, TypeError)


def test_delitem_ShelfStore_0():
    try:
        var = web.session.ShelfStore(None)
        var.__delitem__(None)
    except Exception as e:
        assert isinstance(e, TypeError)


def test_getitem_ShelfStore_0():
    try:
        var = web.session.ShelfStore(None)
        var.__getitem__(None)
    except Exception as e:
        assert isinstance(e, TypeError)


def test_setitem_ShelfStore_0():
    try:
        var = web.session.ShelfStore(None)
        var.__setitem__(None, None)
    except Exception as e:
        assert isinstance(e, TypeError)


def test_cleanup_ShelfStore_0():
    try:
        var = web.session.ShelfStore(None)
        var.cleanup(None)
    except Exception as e:
        assert isinstance(e, TypeError)


def test_contains_Store_0():
    try:
        var = web.session.Store()
        var.__contains__(None)
    except Exception as e:
        assert isinstance(e, NotImplementedError)


def test_getitem_Store_0():
    try:
        var = web.session.Store()
        var.__getitem__(None)
    except Exception as e:
        assert isinstance(e, NotImplementedError)


def test_setitem_Store_0():
    try:
        var = web.session.Store()
        var.__setitem__(None, None)
    except Exception as e:
        assert isinstance(e, NotImplementedError)


def test_cleanup_Store_0():
    try:
        var = web.session.Store()
        var.cleanup(None)
    except Exception as e:
        assert isinstance(e, NotImplementedError)
