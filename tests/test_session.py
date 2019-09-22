import unittest
import web
import tempfile
import os
import threading


class SessionTest(unittest.TestCase):
    def setUp(self):
        app = web.auto_application()
        session = self.make_session(app)

        class count(app.page):
            def GET(self):
                session.count += 1
                return str(session.count)

        class reset(app.page):
            def GET(self):
                session.kill()
                return ""

        class redirect(app.page):
            def GET(self):
                session.request_token = "123"
                raise web.redirect("/count")

        class get_session(app.page):
            path = "/session/(.*)"

            def GET(self, name):
                return session[name]

        self.app = app
        self.session = session

    def make_session(self, app):
        dir = tempfile.mkdtemp()
        store = web.session.DiskStore(dir)
        return web.session.Session(app, store, {"count": 0})

    def testSession(self):
        b = self.app.browser()
        self.assertEqual(b.open("/count").read(), b"1")
        self.assertEqual(b.open("/count").read(), b"2")
        self.assertEqual(b.open("/count").read(), b"3")
        b.open("/reset")
        self.assertEqual(b.open("/count").read(), b"1")

    def testParallelSessions(self):
        b1 = self.app.browser()
        b2 = self.app.browser()

        b1.open("/count")

        for i in range(1, 10):
            self.assertEqual(b1.open("/count").read(), str(i + 1).encode("utf8"))
            self.assertEqual(b2.open("/count").read(), str(i).encode("utf8"))

    def testBadSessionId(self):
        b = self.app.browser()
        self.assertEqual(b.open("/count").read(), b"1")
        self.assertEqual(b.open("/count").read(), b"2")

        cookie = b.cookiejar._cookies["0.0.0.0"]["/"]["webpy_session_id"]
        cookie.value = "/etc/password"
        self.assertEqual(b.open("/count").read(), b"1")

    def testSlowCookies(self):
        b = self.app.browser()
        self.assertEqual(b.open("/count").read(), b"1")
        self.assertEqual(b.open("/count").read(), b"2")

        cookie = b.cookiejar._cookies["0.0.0.0"]["/"]["webpy_session_id"]
        cookie.value = '"/etc/password"'
        self.assertEqual(b.open("/count").read(), b"1")

    def testRedirect(self):
        b = self.app.browser()
        b.open("/redirect")
        b.open("/session/request_token")
        self.assertEqual(b.data, b"123")


class DiskStoreTest(unittest.TestCase):
    def testStoreConcurrent(self):
        dir = tempfile.mkdtemp()
        store = web.session.DiskStore(dir)

        def set_val():
            store["fail"] = "value"

        for c in range(10):
            m = threading.Thread(target=set_val)
            m.start()
            try:
                value = store["fail"]
            except KeyError:
                pass
        self.assertEqual(value, "value")


class DBSessionTest(SessionTest):
    """Session test with db store."""

    def make_session(self, app):
        if os.path.exists("webpy.db"):
            os.remove("webpy.db")

        db = web.database(dbn="sqlite", db="webpy.db")
        # db.printing = True
        db.query(
            ""
            + "CREATE TABLE session ("
            + "    session_id char(128) unique not null,"
            + "    atime timestamp default (datetime('now','utc')),"
            + "    data text)"
        )
        store = web.session.DBStore(db, "session")
        return web.session.Session(app, store, {"count": 0})
