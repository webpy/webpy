"""
HTTP Utilities
(from web.py)
"""

__all__ = [
    "expires",
    "lastmodified",
    "prefixurl",
    "modified",
    "changequery",
    "url",
    "profiler",
]

import datetime
from urllib.parse import urlencode as urllib_urlencode

from . import net, utils
from . import webapi as web
from .py3helpers import iteritems


def prefixurl(base=""):
    """
    Sorry, this function is really difficult to explain.
    Maybe some other time.
    """
    url = web.ctx.path.lstrip("/")
    for i in range(url.count("/")):
        base += "../"
    if not base:
        base = "./"
    return base


def expires(delta):
    """
    Outputs an `Expires` header for `delta` from now.
    `delta` is a `timedelta` object or a number of seconds.
    """
    if isinstance(delta, int):
        delta = datetime.timedelta(seconds=delta)
    date_obj = datetime.datetime.utcnow() + delta
    web.header("Expires", net.httpdate(date_obj))


def lastmodified(date_obj):
    """Outputs a `Last-Modified` header for `datetime`."""
    web.header("Last-Modified", net.httpdate(date_obj))


def modified(date: datetime.datetime=None, etag=None, is_weak=False):
    """
    Checks to see if the page has been modified since the version in the
    requester's cache.

    When you publish pages, you can include `Last-Modified` and `ETag`
    with the date the page was last modified and an opaque token for
    the particular version, respectively. When readers reload the page,
    the browser sends along the modification date and etag value for
    the version it has in its cache. If the page hasn't changed,
    the server can just return `304 Not Modified` and not have to
    send the whole page again.

    This function takes the last-modified date `date` and the ETag `etag`
    and checks the headers to see if they match. If they do, it returns
    `True`, or otherwise it raises NotModified error. It also sets
    `Last-Modified` and `ETag` output headers.
    """
    # We have two etags/etc at play here, so lets be explicit!
    page_last_modified = date
    page_etag = etag
    page_etag_weak = is_weak

    request_modified_since = net.parsehttpdate(web.ctx.env.get("HTTP_IF_MODIFIED_SINCE", "").split(";")[0])
    request_etags = {
        # Mapping of etag to "is weak validator" flag.
        x.strip(' ').lstrip('W/').strip('"'): x.strip(' ').startswith('W/')
        for x in web.ctx.env.get("HTTP_IF_NONE_MATCH", "").split(",")
    }

    validate = False
    if page_etag and "*" in request_etags or page_etag in request_etags:
        is_request_etag_weak = request_etags.get(etag, request_etags.get("*"))
        validate = is_request_etag_weak or not page_etag_weak
    if page_last_modified and request_modified_since:
        # we subtract a second because
        # HTTP dates don't have sub-second precision
        if page_last_modified - datetime.timedelta(seconds=1) <= request_last_modified:
            validate = True

    if page_last_modified:
        lastmodified(date)
    if page_etag:
        web.header("ETag", f'{"W/" if page_etag_weak else ""}"{page_etag}"')
    if validate:
        raise web.notmodified()
    else:
        return True


def urlencode(query, doseq=0):
    """
    Same as urllib.urlencode, but supports unicode strings.

        >>> urlencode({'text':'foo bar'})
        'text=foo+bar'
        >>> urlencode({'x': [1, 2]}, doseq=True)
        'x=1&x=2'
    """

    def convert(value, doseq=False):
        if doseq and isinstance(value, list):
            return [convert(v) for v in value]
        else:
            return utils.safestr(value)

    query = {k: convert(v, doseq) for k, v in query.items()}
    return urllib_urlencode(query, doseq=doseq)


def changequery(query=None, **kw):
    """
    Imagine you're at `/foo?a=1&b=2`. Then `changequery(a=3)` will return
    `/foo?a=3&b=2` -- the same URL but with the arguments you requested
    changed.
    """
    if query is None:
        query = web.rawinput(method="get")
    for k, v in iteritems(kw):
        if v is None:
            query.pop(k, None)
        else:
            query[k] = v
    out = web.ctx.path
    if query:
        out += "?" + urlencode(query, doseq=True)
    return out


def url(path=None, doseq=False, **kw):
    """
    Makes url by concatenating web.ctx.homepath and path and the
    query string created using the arguments.
    """
    if path is None:
        path = web.ctx.path
    if path.startswith("/"):
        out = web.ctx.homepath + path
    else:
        out = path

    if kw:
        out += "?" + urlencode(kw, doseq=doseq)

    return out


def profiler(app):
    """Outputs basic profiling information at the bottom of each response."""
    from utils import profile

    def profile_internal(e, o):
        out, result = profile(app)(e, o)
        return list(out) + ["<pre>" + net.websafe(result) + "</pre>"]

    return profile_internal


if __name__ == "__main__":
    import doctest

    doctest.testmod()
