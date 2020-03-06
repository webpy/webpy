import os
import shutil
import sys
import threading
import time
import unittest

import web

try:
    from urllib.parse import urlencode
except ImportError:
    from urllib import urlencode

data = """
import web

urls = ("/", "%(classname)s")
app = web.application(urls, globals(), autoreload=True)

class %(classname)s:
    def GET(self):
        return "%(output)s"

"""

urls = ("/iter", "do_iter")
app = web.application(urls, globals())


class do_iter:
    def GET(self):
        yield "hello, "
        yield web.input(name="world").name

    POST = GET


def write(filename, data):
    f = open(filename, "w")
    f.write(data)
    f.close()


class ApplicationTest(unittest.TestCase):
    def test_reloader(self):
        write("foo.py", data % dict(classname="a", output="a"))
        import foo

        app = foo.app

        self.assertEqual(app.request("/").data, b"a")

        # test class change
        time.sleep(1)
        write("foo.py", data % dict(classname="a", output="b"))
        self.assertEqual(app.request("/").data, b"b")

        # test urls change
        time.sleep(1)
        write("foo.py", data % dict(classname="c", output="c"))
        self.assertEqual(app.request("/").data, b"c")

    def test_reloader_nested(self):
        try:
            shutil.rmtree("testpackage")
        except OSError:
            pass
        os.mkdir("testpackage")
        write("testpackage/__init__.py", "")
        write("testpackage/bar.py", data % dict(classname="a", output="a"))
        import testpackage.bar

        app = testpackage.bar.app

        self.assertEqual(app.request("/").data, b"a")

        # test class change
        time.sleep(1)
        write("testpackage/bar.py", data % dict(classname="a", output="b"))
        self.assertEqual(app.request("/").data, b"b")

        # test urls change
        time.sleep(1)
        write("testpackage/bar.py", data % dict(classname="c", output="c"))
        self.assertEqual(app.request("/").data, b"c")

    def testUppercaseMethods(self):
        urls = ("/", "hello")
        app = web.application(urls, locals())

        class hello:
            def GET(self):
                return "hello"

            def internal(self):
                return "secret"

        response = app.request("/", method="internal")
        self.assertEqual(response.status, "405 Method Not Allowed")

    def testRedirect(self):
        # fmt: off
        urls = (
            "/a", "redirect /hello/",
            "/b/(.*)", r"redirect /hello/\1",
            "/hello/(.*)", "hello"
        )
        # fmt: on

        app = web.application(urls, locals())

        class hello:
            def GET(self, name):
                name = name or "world"
                return "hello " + name

        response = app.request("/a")
        self.assertEqual(response.status, "301 Moved Permanently")
        self.assertEqual(response.headers["Location"], "http://0.0.0.0:8080/hello/")

        response = app.request("/a?x=2")
        self.assertEqual(response.status, "301 Moved Permanently")
        self.assertEqual(response.headers["Location"], "http://0.0.0.0:8080/hello/?x=2")

        response = app.request("/b/foo?x=2")
        self.assertEqual(response.status, "301 Moved Permanently")
        self.assertEqual(
            response.headers["Location"], "http://0.0.0.0:8080/hello/foo?x=2"
        )

    def test_routing(self):
        urls = ("/foo", "foo")

        class foo:
            def GET(self):
                return "foo"

        app = web.application(urls, {"foo": foo})

        self.assertEqual(app.request("/foo\n").data, b"not found")
        self.assertEqual(app.request("/foo").data, b"foo")

    def test_subdirs(self):
        urls = ("/(.*)", "blog")

        class blog:
            def GET(self, path):
                return "blog " + path

        app_blog = web.application(urls, locals())

        # fmt: off
        urls = (
            "/blog", app_blog,
            "/(.*)", "index"
        )
        # fmt: on

        class index:
            def GET(self, path):
                return "hello " + path

        app = web.application(urls, locals())

        self.assertEqual(app.request("/blog/foo").data, b"blog foo")
        self.assertEqual(app.request("/foo").data, b"hello foo")

        def processor(handler):
            return web.ctx.path + ":" + handler()

        app.add_processor(processor)
        self.assertEqual(app.request("/blog/foo").data, b"/blog/foo:blog foo")

    def test_subdomains(self):
        def create_app(name):
            urls = ("/", "index")

            class index:
                def GET(self):
                    return name

            return web.application(urls, locals())

        # fmt: off
        urls = (
            "a.example.com", create_app('a'),
            "b.example.com", create_app('b'),
            ".*.example.com", create_app('*')
        )
        # fmt: on

        app = web.subdomain_application(urls, locals())

        def test(host, expected_result):
            result = app.request("/", host=host)
            self.assertEqual(result.data, expected_result)

        test("a.example.com", b"a")
        test("b.example.com", b"b")
        test("c.example.com", b"*")
        test("d.example.com", b"*")

    def test_redirect(self):
        urls = ("/(.*)", "blog")

        class blog:
            def GET(self, path):
                if path == "foo":
                    raise web.seeother("/login", absolute=True)
                else:
                    raise web.seeother("/bar")

        app_blog = web.application(urls, locals())

        # fmt: off
        urls = (
            "/blog", app_blog,
            "/(.*)", "index"
        )
        # fmt: on

        class index:
            def GET(self, path):
                return "hello " + path

        app = web.application(urls, locals())

        response = app.request("/blog/foo")
        self.assertEqual(response.headers["Location"], "http://0.0.0.0:8080/login")

        response = app.request("/blog/foo", env={"SCRIPT_NAME": "/x"})
        self.assertEqual(response.headers["Location"], "http://0.0.0.0:8080/x/login")

        response = app.request("/blog/foo2")
        self.assertEqual(response.headers["Location"], "http://0.0.0.0:8080/blog/bar")

        response = app.request("/blog/foo2", env={"SCRIPT_NAME": "/x"})
        self.assertEqual(response.headers["Location"], "http://0.0.0.0:8080/x/blog/bar")

    def test_processors(self):
        urls = ("/(.*)", "blog")

        class blog:
            def GET(self, path):
                return "blog " + path

        state = web.storage(x=0, y=0)

        def f():
            state.x += 1

        app_blog = web.application(urls, locals())
        app_blog.add_processor(web.loadhook(f))

        # fmt: off
        urls = (
            "/blog", app_blog,
            "/(.*)", "index"
        )
        # fmt: on

        class index:
            def GET(self, path):
                return "hello " + path

        app = web.application(urls, locals())

        def g():
            state.y += 1

        app.add_processor(web.loadhook(g))

        app.request("/blog/foo")
        assert state.x == 1 and state.y == 1, repr(state)
        app.request("/foo")
        assert state.x == 1 and state.y == 2, repr(state)

    def testUnicodeInput(self):
        urls = ("(/.*)", "foo")

        class foo:
            def GET(self, path):
                i = web.input(name="")
                return repr(i.name)

            def POST(self, path):
                if path == "/multipart":
                    i = web.input(file={})
                    return i.file.value
                else:
                    i = web.input()
                    return repr(dict(i)).replace("u", "")

        app = web.application(urls, locals())

        def f(name):
            path = "/?" + urlencode({"name": name.encode("utf-8")})
            self.assertEqual(app.request(path).data.decode("utf-8"), repr(name))

        f(u"\u1234")
        f(u"foo")

        response = app.request("/", method="POST", data=dict(name="foo"))

        self.assertEqual(response.data, b"{'name': 'foo'}")

        data = '--boundary\r\nContent-Disposition: form-data; name="x"\r\n\r\nfoo\r\n--boundary\r\nContent-Disposition: form-data; name="file"; filename="a.txt"\r\nContent-Type: text/plain\r\n\r\na\r\n--boundary--\r\n'
        headers = {"Content-Type": "multipart/form-data; boundary=boundary"}
        response = app.request("/multipart", method="POST", data=data, headers=headers)

        self.assertEqual(response.data, b"a")

    def testCustomNotFound(self):
        urls_a = ("/", "a")
        urls_b = ("/", "b")

        app_a = web.application(urls_a, locals())
        app_b = web.application(urls_b, locals())

        app_a.notfound = lambda: web.HTTPError("404 Not Found", {}, "not found 1")

        # fmt: off
        urls = (
            "/a", app_a,
            "/b", app_b
        )
        # fmt: on

        app = web.application(urls, locals())

        def assert_notfound(path, message):
            response = app.request(path)
            self.assertEqual(response.status.split()[0], "404")
            self.assertEqual(response.data, message)

        assert_notfound("/a/foo", b"not found 1")
        assert_notfound("/b/foo", b"not found")

        app.notfound = lambda: web.HTTPError("404 Not Found", {}, "not found 2")
        assert_notfound("/a/foo", b"not found 1")
        assert_notfound("/b/foo", b"not found 2")

    def testIter(self):
        self.assertEqual(app.request("/iter").data, b"hello, world")
        self.assertEqual(app.request("/iter?name=web").data, b"hello, web")

        self.assertEqual(app.request("/iter", method="POST").data, b"hello, world")
        self.assertEqual(
            app.request("/iter", method="POST", data="name=web").data, b"hello, web"
        )

    def testUnload(self):
        x = web.storage(a=0)

        # fmt: off
        urls = (
            "/foo", "foo",
            "/bar", "bar"
        )
        # fmt: on

        class foo:
            def GET(self):
                return "foo"

        class bar:
            def GET(self):
                raise web.notfound()

        app = web.application(urls, locals())

        def unload():
            x.a += 1

        app.add_processor(web.unloadhook(unload))

        app.request("/foo")
        self.assertEqual(x.a, 1)

        app.request("/bar")
        self.assertEqual(x.a, 2)

    def test_changequery(self):
        urls = ("/", "index")

        class index:
            def GET(self):
                return web.changequery(x=1)

        app = web.application(urls, locals())

        def f(path):
            return app.request(path).data

        self.assertEqual(f("/?x=2"), b"/?x=1")

        p = f("/?y=1&y=2&x=2")
        self.assertTrue(p == b"/?y=1&y=2&x=1" or p == b"/?x=1&y=1&y=2")

    def test_setcookie(self):
        urls = ("/", "index")

        class index:
            def GET(self):
                web.setcookie("foo", "bar")
                return "hello"

        app = web.application(urls, locals())

        def f(script_name=""):
            response = app.request("/", env={"SCRIPT_NAME": script_name})
            return response.headers["Set-Cookie"]

        self.assertEqual(f(""), "foo=bar; Path=/")
        self.assertEqual(f("/admin"), "foo=bar; Path=/admin/")

    def test_stopsimpleserver(self):
        urls = ("/", "index")

        class index:
            def GET(self):
                pass

        # reset command-line arguments
        sys.argv = ["code.py"]

        app = web.application(urls, locals())
        thread = threading.Thread(target=app.run)

        thread.start()
        time.sleep(1)
        self.assertTrue(thread.is_alive())

        app.stop()
        thread.join(timeout=1)
        self.assertFalse(thread.is_alive())
