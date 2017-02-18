"""
py.test test suit for Network utilities
(from web.py -> net.py)
"""

import web

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
	# TODO : try if the bytes are getting accepted
	assert web.validipaddr('0b1111.0b1111.0b1111.0b1111') == False