import threading
import time
import unittest
from urllib.parse import unquote_to_bytes

import web


class WSGITest(unittest.TestCase):
    def test_layers_unicode(self):
        urls = ("/", "uni")

        class uni:
            def GET(self):
                return "\u0c05\u0c06"

        app = web.application(urls, locals())

        thread = threading.Thread(target=app.run)
        thread.start()
        time.sleep(0.5)

        b = web.browser.AppBrowser(app)
        r = b.open("/").read()
        s = r.decode("utf8")
        self.assertEqual(s, "\u0c05\u0c06")

        app.stop()
        thread.join()

    def test_layers_bytes(self):
        urls = ("/", "bytes")

        class bytes:
            def GET(self):
                return b"abcdef"

        app = web.application(urls, locals())

        thread = threading.Thread(target=app.run)
        thread.start()
        time.sleep(0.5)

        b = web.browser.AppBrowser(app)
        r = b.open("/")
        self.assertEqual(r.read(), b"abcdef")

        app.stop()
        thread.join()

    def test_unicode_url(self):
        urls = ("/([^/]+)", "url_passthrough")

        class url_passthrough:
            def GET(self, arg):
                return arg

        app = web.application(urls, locals())

        thread = threading.Thread(target=app.run)
        thread.start()
        time.sleep(0.5)

        b = web.browser.AppBrowser(app)
        r = b.open("/%E2%84%A6")
        s = unquote_to_bytes(r.read())
        self.assertEqual(s, b"\xe2\x84\xa6")

        app.stop()
        thread.join()
