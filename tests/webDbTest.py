import web.db
import web
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
import web.application
import web.browser


def test_init_SQLLiteral_0():
    var = web.db.SQLLiteral(None)
    ret = var
    assert isinstance(ret, web.db.SQLLiteral)


def test_repr_SQLLiteral_0():
    var = web.db.SQLLiteral(None)
    ret = var.__repr__()
    assert ret is not None


def test_repr_SQLParam_0():
    var = web.db.SQLParam(None)
    ret = var.__repr__()
    assert ret is not None


def test_str_SQLParam_0():
    var = web.db.SQLParam(None)
    ret = var.__str__()
    assert ret is not None


def test_eq_SQLQuery_0():
    var = web.db.SQLQuery(None)
    ret = var.__eq__(None)
    assert ret is not None


def test_iadd_SQLQuery_0():
    var = web.db.SQLQuery(None)
    ret = var.__iadd__(None)
    assert ret is not None


def test_repr_SQLQuery_0():
    var = web.db.SQLQuery(None)
    ret = var.__repr__()
    assert ret is not None


def test_unicode_SQLQuery_0():
    var = web.db.SQLQuery(None)
    ret = var.__unicode__()
    assert ret is not None


def test_append_SQLQuery_0():
    var = web.db.SQLQuery(None)
    ret = var.append(None)
    assert ret is None


def test_eq__Node_0():
    var = web.db._Node(None, None, None)
    ret = var.__eq__(None)
    assert ret is not None


def test_repr__Node_0():
    var = web.db._Node(None, None, None)
    ret = var.__repr__()
    assert ret is not None


def test_sqlify_0():
    ret = web.db.sqlify(None)
    assert ret is not None


def test_test_parser_0():
    ret = web.db.test_parser()
    assert ret is None


def test_test_safeeval_0():
    ret = web.db.test_safeeval()
    assert ret is None


def test_match_Parser_0():
    try:
        var = web.db.Parser()
        var.match()
    except Exception as e:
        assert isinstance(e, web.db._ItplError)


def test_add_SQLParam_0():
    try:
        var = web.db.SQLParam(None)
        var.__add__(None)
    except Exception as e:
        assert isinstance(e, TypeError)


def test_radd_SQLParam_0():
    try:
        var = web.db.SQLParam(None)
        var.__radd__(None)
    except Exception as e:
        assert isinstance(e, TypeError)


def test_str__ItplError_0():
    try:
        var = web.db._ItplError(None, None)
        var.__str__()
    except Exception as e:
        assert isinstance(e, TypeError)


def test_interpolate_0():
    try:
        web.db._interpolate(None)
    except Exception as e:
        assert isinstance(e, AttributeError)


def test__sqllist_0():
    try:
        web.db._sqllist(None)
    except Exception as e:
        assert isinstance(e, TypeError)


def test_dburl2dict_0():
    try:
        web.db.dburl2dict(None)
    except Exception as e:
        assert isinstance(e, TypeError)


def test_sqllist_0():
    try:
        web.db.sqllist(None)
    except Exception as e:
        assert isinstance(e, TypeError)


def test_sqlors_0():
    try:
        web.db.sqlors(None, None)
    except Exception as e:
        assert isinstance(e, TypeError)
