import unittest
import web
import threading
import time


class WSGITest(unittest.TestCase):
    def test_layers_unicode(self):
        urls = ("/", "uni")

        class uni:
            def GET(self):
                return u"\u0C05\u0C06"

        app = web.application(urls, locals())

        thread = threading.Thread(target=app.run)
        thread.start()
        time.sleep(0.5)

        b = web.browser.Browser()
        r = b.open("/").read()
        s = r.decode("utf8")
        self.assertEqual(s, u"\u0C05\u0C06")

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

        b = web.browser.Browser()
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

        b = web.browser.Browser()
        r = b.open("/%E2%84%A6")
        self.assertEqual(r.read(), b"\xE2\x84\xA6")

        app.stop()
        thread.join()
