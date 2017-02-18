"""
py.test test suit for Network utilities
(from web.py -> net.py)
"""

import web

def test_validip6addr():
	assert web.validip6addr('::') == True
	assert web.validip6addr('aaaa:bbbb:cccc:dddd::1') ==	True
	assert web.validip6addr('1:2:3:4:5:6:7:8:9:10') == False
	assert web.validip6addr('12:10') == False