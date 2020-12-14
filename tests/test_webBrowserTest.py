import web.browser
import web
import web.db
import web.py3helpers
import web.utils
import urllib
import urllib.parse
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
import urllib.request
import urllib.error
import urllib.response


def test_reset_AppBrowser_0():
    var = web.browser.AppBrowser(None)
    ret = var.reset()
    assert ret is None


def test_build_opener_Browser_0():
    var = web.browser.Browser()
    ret = var.build_opener()
    assert isinstance(ret, urllib.request.OpenerDirector)


def test_getitem_AppBrowser_0():
    try:
        var = web.browser.AppBrowser(None)
        var.__getitem__(None)
    except Exception as e:
        assert isinstance(e, TypeError)


def test_setitem_AppBrowser_0():
    try:
        var = web.browser.AppBrowser(None)
        var.__setitem__(None, None)
    except Exception as e:
        assert isinstance(e, TypeError)


def test_filter_links_AppBrowser_0():
    try:
        var = web.browser.AppBrowser(None)
        var._filter_links(None, None, None, None, None, None)
    except Exception as e:
        assert isinstance(e, TypeError)


def test_get_links_AppBrowser_0():
    try:
        var = web.browser.AppBrowser(None)
        var._get_links()
    except Exception as e:
        assert isinstance(e, ModuleNotFoundError)


def test_find_link_AppBrowser_0():
    try:
        var = web.browser.AppBrowser(None)
        var.find_link(None, None, None, None, None)
    except Exception as e:
        assert isinstance(e, ModuleNotFoundError)


def test_follow_link_AppBrowser_0():
    try:
        var = web.browser.AppBrowser(None)
        var.follow_link(None, None, None, None, None, None)
    except Exception as e:
        assert isinstance(e, ModuleNotFoundError)


def test_get_forms_AppBrowser_0():
    try:
        var = web.browser.AppBrowser(None)
        var.get_forms()
    except Exception as e:
        assert isinstance(e, ModuleNotFoundError)


def test_get_text_AppBrowser_0():
    try:
        var = web.browser.AppBrowser(None)
        var.get_text(None)
    except Exception as e:
        assert isinstance(e, ModuleNotFoundError)


def test_select_form_AppBrowser_0():
    try:
        var = web.browser.AppBrowser(None)
        var.select_form(None, None, 0)
    except Exception as e:
        assert isinstance(e, ModuleNotFoundError)


def test_show_AppBrowser_0():
    try:
        var = web.browser.AppBrowser(None)
        var.show()
    except Exception as e:
        assert isinstance(e, TypeError)
