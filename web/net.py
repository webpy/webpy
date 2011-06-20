"""
Network Utilities
(from web.py)
"""

__all__ = [
  "validipaddr", "validipport", "validip", "validaddr", 
  "urlquote",
  "httpdate", "parsehttpdate", 
  "htmlquote", "htmlunquote", "websafe",
]

import urllib, time
try: import datetime
except ImportError: pass

def validipaddr(address):
    """
    Returns True if `address` is a valid IPv4 address.
    
        >>> validipaddr('192.168.1.1')
        True
        >>> validipaddr('192.168.1.800')
        False
        >>> validipaddr('192.168.1')
        False
    """
    try:
        octets = address.split('.')
        if len(octets) != 4:
            return False
        for x in octets:
            if not (0 <= int(x) <= 255):
                return False
    except ValueError:
        return False
    return True

def validipport(port):
    """
    Returns True if `port` is a valid IPv4 port.
    
        >>> validipport('9000')
        True
        >>> validipport('foo')
        False
        >>> validipport('1000000')
        False
    """
    try:
        if not (0 <= int(port) <= 65535):
            return False
    except ValueError:
        return False
    return True

def validip(ip, defaultaddr="0.0.0.0", defaultport=8080):
    """Returns `(ip_address, port)` from string `ip_addr_port`"""
    addr = defaultaddr
    port = defaultport
    
    ip = ip.split(":", 1)
    if len(ip) == 1:
        if not ip[0]:
            pass
        elif validipaddr(ip[0]):
            addr = ip[0]
        elif validipport(ip[0]):
            port = int(ip[0])
        else:
            raise ValueError, ':'.join(ip) + ' is not a valid IP address/port'
    elif len(ip) == 2:
        addr, port = ip
        if not validipaddr(addr) and validipport(port):
            raise ValueError, ':'.join(ip) + ' is not a valid IP address/port'
        port = int(port)
    else:
        raise ValueError, ':'.join(ip) + ' is not a valid IP address/port'
    return (addr, port)

def validaddr(string_):
    """
    Returns either (ip_address, port) or "/path/to/socket" from string_
    
        >>> validaddr('/path/to/socket')
        '/path/to/socket'
        >>> validaddr('8000')
        ('0.0.0.0', 8000)
        >>> validaddr('127.0.0.1')
        ('127.0.0.1', 8080)
        >>> validaddr('127.0.0.1:8000')
        ('127.0.0.1', 8000)
        >>> validaddr('fff')
        Traceback (most recent call last):
            ...
        ValueError: fff is not a valid IP address/port
    """
    if '/' in string_:
        return string_
    else:
        return validip(string_)

def urlquote(val):
    """
    Quotes a string for use in a URL.
    
        >>> urlquote('://?f=1&j=1')
        '%3A//%3Ff%3D1%26j%3D1'
        >>> urlquote(None)
        ''
        >>> urlquote(u'\u203d')
        '%E2%80%BD'
    """
    if val is None: return ''
    if not isinstance(val, unicode): val = str(val)
    else: val = val.encode('utf-8')
    return urllib.quote(val)

def httpdate(date_obj):
    """
    Formats a datetime object for use in HTTP headers.
    
        >>> import datetime
        >>> httpdate(datetime.datetime(1970, 1, 1, 1, 1, 1))
        'Thu, 01 Jan 1970 01:01:01 GMT'
    """
    return date_obj.strftime("%a, %d %b %Y %H:%M:%S GMT")

def parsehttpdate(string_):
    """
    Parses an HTTP date into a datetime object.

        >>> parsehttpdate('Thu, 01 Jan 1970 01:01:01 GMT')
        datetime.datetime(1970, 1, 1, 1, 1, 1)
    """
    try:
        t = time.strptime(string_, "%a, %d %b %Y %H:%M:%S %Z")
    except ValueError:
        return None
    return datetime.datetime(*t[:6])

def htmlquote(text):
    r"""
    Encodes `text` for raw use in HTML.
    
        >>> htmlquote(u"<'&\">")
        u'&lt;&#39;&amp;&quot;&gt;'
    """
    text = text.replace(u"&", u"&amp;") # Must be done first!
    text = text.replace(u"<", u"&lt;")
    text = text.replace(u">", u"&gt;")
    text = text.replace(u"'", u"&#39;")
    text = text.replace(u'"', u"&quot;")
    return text

def htmlunquote(text):
    r"""
    Decodes `text` that's HTML quoted.

        >>> htmlunquote(u'&lt;&#39;&amp;&quot;&gt;')
        u'<\'&">'
    """
    text = text.replace(u"&quot;", u'"')
    text = text.replace(u"&#39;", u"'")
    text = text.replace(u"&gt;", u">")
    text = text.replace(u"&lt;", u"<")
    text = text.replace(u"&amp;", u"&") # Must be done last!
    return text
    
def websafe(val=u''):
    r"""Converts `val` so that it is safe for use in Unicode HTML.

        >>> websafe("<'&\">")
        u'&lt;&#39;&amp;&quot;&gt;'
        >>> websafe()
        u''
        >>> websafe(u'\u203d')
        u'\u203d'
        >>> websafe('\xe2\x80\xbd')
        u'\u203d'
    """
    if isinstance(val, str):
        val = val.decode('utf-8')
    if not isinstance(val, unicode):
        raise ValueError("Cravenly refusing to autoconvert to unicode")
        
    return htmlquote(val)

if __name__ == "__main__":
    import doctest
    doctest.testmod()
