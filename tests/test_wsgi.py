import threading
import time
import unittest
from urllib.parse import unquote_to_bytes as unquote

import web


class WSGITest(unittest.TestCase):
    def test_layers_unicode(self):
        urls = ("/", "uni")

        class uni:
            def GET(self):
                return "\u0C05\u0C06"

        app = web.application(urls, locals())

        thread = threading.Thread(target=app.run)
        thread.start()
        time.sleep(0.5)

        b = web.browser.AppBrowser(app)
        r = b.open("/").read()
        s = r.decode("utf8")
        self.assertEqual(s, "\u0C05\u0C06")

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
        s = unquote(r.read())
        self.assertEqual(s, b"\xE2\x84\xA6")

        r = b.open("/Dictionnaire_des_ide%CC%81es_rec%CC%A7ues")
        s = unquote(r.read())
        self.assertEqual(s, b"/Dictionnaire des id\xc3\xa9es re\xc3\xa7ues")
        self.assertEqual(s, "/Dictionnaire des idées reçues")

        r = b.open("/Hélas")
        s = unquote(r.read())
        self.assertEqual(s, b"H\xe9las")

        app.stop()
        thread.join()
