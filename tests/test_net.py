"""
py.test test suit for Network utilities
(from web -> net.py)
"""

from __future__ import unicode_literals
import web
import pytest
import datetime


def test_validip6addr():
	""" Checks if ipv6 format is valid or not"""
	assert web.validip6addr('::') == True
	assert web.validip6addr('aaaa:bbbb:cccc:dddd::1') ==	True
	assert web.validip6addr('1:2:3:4:5:6:7:8:9:10') == False
	assert web.validip6addr('12:10') == False


def test_validipaddr():
	""" Checks is ipv4 format is valid or not"""
	assert web.validipaddr('192.168.1.1') == True
	assert web.validipaddr('192.168.1.800') == False
	assert web.validipaddr('192.168.1') == False
	"""
		Tried if bytecode is getting accepted
	"""
	assert web.validipaddr('0b1111.0b1111.0b1111.0b1111') == False


def test_validipport():
	""" Checks if port number is valid or not """
	assert web.validipport('9000') == True
	assert web.validipport('foo') == False
	assert web.validipport('1000000') == False


def test_validip():
	""" Checks if ip_addr_port is valid"""
	assert web.validip('1.2.3.4') == ('1.2.3.4', 8080)
	assert web.validip('80') == ('0.0.0.0', 80)
	assert web.validip('192.168.0.1:85') == ('192.168.0.1', 85)
	assert web.validip('::') == ('::', 8080)
	assert web.validip('[::]:80') == ('::', 80)
	assert web.validip('[::1]:88') == ('::1', 88)


def test_validaddr():
	assert web.validaddr('/path/to/socket') == '/path/to/socket'
	assert web.validaddr('8000') == ('0.0.0.0', 8000)
	assert web.validaddr('127.0.0.1') == ('127.0.0.1', 8080)
	assert web.validaddr('[::1]:80') == ('::1', 80)
	assert web.validaddr('127.0.0.1:8000') == ('127.0.0.1', 8000)
	with pytest.raises(ValueError):
		web.validaddr('fff')


def test_urlquote():
	assert web.urlquote('://?f=1&j=1') == '%3A//%3Ff%3D1%26j%3D1'
	assert web.urlquote(None) == ''
	assert web.urlquote('\u203d') == '%E2%80%BD'
	# TODO : check for the u' 

def test_httpdate():
	assert web.httpdate(datetime.datetime(1970, 1, 1, 1, 1, 1)) == 'Thu, 01 Jan 1970 01:01:01 GMT'


def test_parsehttpdate():
	assert web.parsehttpdate('Thu, 01 Jan 1970 01:01:01 GMT') == datetime.datetime(1970, 1, 1, 1, 1, 1)


def test_htmlquote():
	assert web.htmlquote("<'&\">") == '&lt;&#39;&amp;&quot;&gt;'


def test_htmlunquote():
	assert web.htmlunquote('&lt;&#39;&amp;&quot;&gt;') == '<\'&">'


def test_websafe():
	assert web.websafe("<'&\">") == '&lt;&#39;&amp;&quot;&gt;'
	assert web.websafe(None) == ''
	assert (web.websafe('\u203d') == '\u203d') == True