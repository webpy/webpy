"""Browser to test web applications.
(from web.py)
"""
import os
import webbrowser
from io import BytesIO

from .net import htmlunquote
from .py3helpers import PY2, text_type
from .utils import re_compile

try:  # Py3
    from http.client import HTTPMessage
    from urllib.request import HTTPHandler, HTTPCookieProcessor, Request, HTTPError
    from urllib.request import build_opener as urllib_build_opener
    from urllib.parse import urljoin
    from http.cookiejar import CookieJar
    from urllib.response import addinfourl
except ImportError:  # Py2
    from httplib import HTTPMessage
    from urllib import addinfourl
    from urllib2 import HTTPHandler, HTTPCookieProcessor, Request, HTTPError
    from urllib2 import build_opener as urllib_build_opener
    from cookielib import CookieJar
    from urlparse import urljoin

# Welcome to the Py2->Py3 httplib/urllib reorganization nightmare.

if PY2:
    get_selector = lambda x: x.get_selector()
    get_host = lambda x: x.get_host()
    get_data = lambda x: x.get_data()
    get_type = lambda x: x.get_type()
else:
    get_selector = lambda x: x.selector
    get_host = lambda x: x.host
    get_data = lambda x: x.data
    get_type = lambda x: x.type

DEBUG = False

__all__ = ["BrowserError", "Browser", "AppBrowser", "AppHandler"]


class BrowserError(Exception):
    pass


class Browser(object):
    def __init__(self):
        self.cookiejar = CookieJar()
        self._cookie_processor = HTTPCookieProcessor(self.cookiejar)
        self.form = None

        self.url = "http://0.0.0.0:8080/"
        self.path = "/"

        self.status = None
        self.data = None
        self._response = None
        self._forms = None

    @property
    def text(self):
        return self.data.decode("utf-8")

    def reset(self):
        """Clears all cookies and history."""
        self.cookiejar.clear()

    def build_opener(self):
        """Builds the opener using (urllib2/urllib.request).build_opener.
        Subclasses can override this function to prodive custom openers.
        """
        return urllib_build_opener()

    def do_request(self, req):
        if DEBUG:
            print("requesting", req.get_method(), req.get_full_url())

        opener = self.build_opener()
        opener.add_handler(self._cookie_processor)
        try:
            self._response = opener.open(req)
        except HTTPError as e:
            self._response = e

        self.url = self._response.geturl()
        self.path = get_selector(Request(self.url))
        self.data = self._response.read()
        self.status = self._response.code
        self._forms = None
        self.form = None

        return self.get_response()

    def open(self, url, data=None, headers={}):
        """Opens the specified url."""
        url = urljoin(self.url, url)
        req = Request(url, data, headers)

        return self.do_request(req)

    def show(self):
        """Opens the current page in real web browser."""
        f = open("page.html", "w")
        f.write(self.data)
        f.close()

        url = "file://" + os.path.abspath("page.html")
        webbrowser.open(url)

    def get_response(self):
        """Returns a copy of the current response."""
        return addinfourl(
            BytesIO(self.data), self._response.info(), self._response.geturl()
        )

    def get_soup(self):
        """Returns beautiful soup of the current document."""
        import BeautifulSoup

        return BeautifulSoup.BeautifulSoup(self.data)

    def get_text(self, e=None):
        """Returns content of e or the current document as plain text."""
        e = e or self.get_soup()
        return "".join(
            [
                htmlunquote(c)
                for c in e.recursiveChildGenerator()
                if isinstance(c, text_type)
            ]
        )

    def _get_links(self):
        soup = self.get_soup()
        return [a for a in soup.findAll(name="a")]

    def get_links(
        self, text=None, text_regex=None, url=None, url_regex=None, predicate=None
    ):
        """Returns all links in the document."""
        return self._filter_links(
            self._get_links(),
            text=text,
            text_regex=text_regex,
            url=url,
            url_regex=url_regex,
            predicate=predicate,
        )

    def follow_link(
        self,
        link=None,
        text=None,
        text_regex=None,
        url=None,
        url_regex=None,
        predicate=None,
    ):
        if link is None:
            links = self._filter_links(
                self.get_links(),
                text=text,
                text_regex=text_regex,
                url=url,
                url_regex=url_regex,
                predicate=predicate,
            )
            link = links and links[0]

        if link:
            return self.open(link["href"])
        else:
            raise BrowserError("No link found")

    def find_link(
        self, text=None, text_regex=None, url=None, url_regex=None, predicate=None
    ):
        links = self._filter_links(
            self.get_links(),
            text=text,
            text_regex=text_regex,
            url=url,
            url_regex=url_regex,
            predicate=predicate,
        )
        return links and links[0] or None

    def _filter_links(
        self,
        links,
        text=None,
        text_regex=None,
        url=None,
        url_regex=None,
        predicate=None,
    ):
        predicates = []
        if text is not None:
            predicates.append(lambda link: link.string == text)
        if text_regex is not None:
            predicates.append(
                lambda link: re_compile(text_regex).search(link.string or "")
            )
        if url is not None:
            predicates.append(lambda link: link.get("href") == url)
        if url_regex is not None:
            predicates.append(
                lambda link: re_compile(url_regex).search(link.get("href", ""))
            )
        if predicate:
            predicate.append(predicate)

        def f(link):
            for p in predicates:
                if not p(link):
                    return False
            return True

        return [link for link in links if f(link)]

    def get_forms(self):
        """Returns all forms in the current document.
        The returned form objects implement the ClientForm.HTMLForm interface.
        """
        if self._forms is None:
            import ClientForm

            self._forms = ClientForm.ParseResponse(
                self.get_response(), backwards_compat=False
            )
        return self._forms

    def select_form(self, name=None, predicate=None, index=0):
        """Selects the specified form."""
        forms = self.get_forms()

        if name is not None:
            forms = [f for f in forms if f.name == name]
        if predicate:
            forms = [f for f in forms if predicate(f)]

        if forms:
            self.form = forms[index]
            return self.form
        else:
            raise BrowserError("No form selected.")

    def submit(self, **kw):
        """submits the currently selected form."""
        if self.form is None:
            raise BrowserError("No form selected.")
        req = self.form.click(**kw)
        return self.do_request(req)

    def __getitem__(self, key):
        return self.form[key]

    def __setitem__(self, key, value):
        self.form[key] = value


class AppBrowser(Browser):
    """Browser interface to test web.py apps.

        b = AppBrowser(app)
        b.open('/')
        b.follow_link(text='Login')

        b.select_form(name='login')
        b['username'] = 'joe'
        b['password'] = 'secret'
        b.submit()

        assert b.path == '/'
        assert 'Welcome joe' in b.get_text()
    """

    def __init__(self, app):
        Browser.__init__(self)
        self.app = app

    def build_opener(self):
        return urllib_build_opener(AppHandler(self.app))


class AppHandler(HTTPHandler):
    """urllib2 handler to handle requests using web.py application."""

    handler_order = 100
    https_request = HTTPHandler.do_request_

    def __init__(self, app):
        self.app = app

    def http_open(self, req):
        result = self.app.request(
            localpart=get_selector(req),
            method=req.get_method(),
            host=get_host(req),
            data=get_data(req),
            headers=dict(req.header_items()),
            https=get_type(req) == "https",
        )
        return self._make_response(result, req.get_full_url())

    def https_open(self, req):
        return self.http_open(req)

    def _make_response(self, result, url):

        data = "\r\n".join(["%s: %s" % (k, v) for k, v in result.header_items])

        if PY2:
            headers = HTTPMessage(BytesIO(data))
        else:
            import email

            headers = email.message_from_string(data)

        response = addinfourl(BytesIO(result.data), headers, url)
        code, msg = result.status.split(None, 1)
        response.code, response.msg = int(code), msg
        return response
