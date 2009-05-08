import webtest
import time

import web
import urllib

data = """
import web

urls = ("/", "%(classname)s")
app = web.application(urls, globals(), autoreload=True)

class %(classname)s:
    def GET(self):
        return "%(output)s"

"""

urls = (
    "/iter", "do_iter",
)
app = web.application(urls, globals())

class do_iter:
    def GET(self):
        yield 'hello, '
        yield web.input(name='world').name

    POST = GET

def write(filename, data):
    f = open(filename, 'w')
    f.write(data)
    f.close()

class ApplicationTest(webtest.TestCase):
    def test_reloader(self):
        write('foo.py', data % dict(classname='a', output='a'))
        import foo
        app = foo.app
        
        self.assertEquals(app.request('/').data, 'a')
        
        # test class change
        time.sleep(1)
        write('foo.py', data % dict(classname='a', output='b'))
        self.assertEquals(app.request('/').data, 'b')

        # test urls change
        time.sleep(1)
        write('foo.py', data % dict(classname='c', output='c'))
        self.assertEquals(app.request('/').data, 'c')
        
    def testUppercaseMethods(self):
        urls = ("/", "hello")
        app = web.application(urls, locals())
        class hello:
            def GET(self): return "hello"
            def internal(self): return "secret"
            
        response = app.request('/', method='internal')
        self.assertEquals(response.status, '405 Method Not Allowed')
        
    def testRedirect(self):
        urls = (
            "/a", "redirect /hello/",
            "/b/(.*)", r"redirect /hello/\1",
            "/hello/(.*)", "hello"
        )
        app = web.application(urls, locals())
        class hello:
            def GET(self, name): 
                name = name or 'world'
                return "hello " + name
            
        response = app.request('/a')
        self.assertEquals(response.status, '301 Moved Permanently')
        self.assertEquals(response.headers['Location'], 'http://0.0.0.0:8080/hello/')

        response = app.request('/a?x=2')
        self.assertEquals(response.status, '301 Moved Permanently')
        self.assertEquals(response.headers['Location'], 'http://0.0.0.0:8080/hello/?x=2')

        response = app.request('/b/foo?x=2')
        self.assertEquals(response.status, '301 Moved Permanently')
        self.assertEquals(response.headers['Location'], 'http://0.0.0.0:8080/hello/foo?x=2')
        
    def test_subdirs(self):
        urls = (
            "/(.*)", "blog"
        )
        class blog:
            def GET(self, path):
                return "blog " + path
        app_blog = web.application(urls, locals())
        
        urls = (
            "/blog", app_blog,
            "/(.*)", "index"
        )
        class index:
            def GET(self, path):
                return "hello " + path
        app = web.application(urls, locals())
        
        self.assertEquals(app.request('/blog/foo').data, 'blog foo')
        self.assertEquals(app.request('/foo').data, 'hello foo')
        
        def processor(handler):
            return web.ctx.path + ":" + handler()
        app.add_processor(processor)
        self.assertEquals(app.request('/blog/foo').data, '/blog/foo:blog foo')
    
    def test_subdomains(self):
        def create_app(name):
            urls = ("/", "index")
            class index:
                def GET(self):
                    return name
            return web.application(urls, locals())
        
        urls = (
            "a.example.com", create_app('a'),
            "b.example.com", create_app('b'),
            ".*.example.com", create_app('*')
        )
        app = web.subdomain_application(urls, locals())
        
        def test(host, expected_result):
            result = app.request('/', host=host)
            self.assertEquals(result.data, expected_result)
            
        test('a.example.com', 'a')
        test('b.example.com', 'b')
        test('c.example.com', '*')
        test('d.example.com', '*')
        
    def test_redirect(self):
        urls = (
            "/(.*)", "blog"
        )
        class blog:
            def GET(self, path):
                if path == 'foo':
                    raise web.seeother('/login', absolute=True)
                else:
                    raise web.seeother('/bar')
        app_blog = web.application(urls, locals())
        
        urls = (
            "/blog", app_blog,
            "/(.*)", "index"
        )
        class index:
            def GET(self, path):
                return "hello " + path
        app = web.application(urls, locals())
        
        response = app.request('/blog/foo')
        self.assertEquals(response.headers['Location'], 'http://0.0.0.0:8080/login')
        
        response = app.request('/blog/foo', env={'SCRIPT_NAME': '/x'})
        self.assertEquals(response.headers['Location'], 'http://0.0.0.0:8080/x/login')

        response = app.request('/blog/foo2')
        self.assertEquals(response.headers['Location'], 'http://0.0.0.0:8080/blog/bar')
        
        response = app.request('/blog/foo2', env={'SCRIPT_NAME': '/x'})
        self.assertEquals(response.headers['Location'], 'http://0.0.0.0:8080/x/blog/bar')

    def test_processors(self):
        urls = (
            "/(.*)", "blog"
        )
        class blog:
            def GET(self, path):
                return 'blog ' + path

        state = web.storage(x=0, y=0)
        def f():
            state.x += 1

        app_blog = web.application(urls, locals())
        app_blog.add_processor(web.loadhook(f))
        
        urls = (
            "/blog", app_blog,
            "/(.*)", "index"
        )
        class index:
            def GET(self, path):
                return "hello " + path
        app = web.application(urls, locals())
        def g():
            state.y += 1
        app.add_processor(web.loadhook(g))

        app.request('/blog/foo')
        assert state.x == 1 and state.y == 1, repr(state)
        app.request('/foo')
        assert state.x == 1 and state.y == 2, repr(state)
        
    def testUnicodeInput(self):
        urls = (
            "(/.*)", "foo"
        )
        class foo:
            def GET(self, path):
                i = web.input(name='')
                return repr(i.name)
                
            def POST(self, path):
                if path == '/multipart':
                    i = web.input(file={})
                    return i.file.value
                else:
                    i = web.input()
                    return repr(dict(i))
                
        app = web.application(urls, locals())
        
        def f(name):
            path = '/?' + urllib.urlencode({"name": name.encode('utf-8')})
            self.assertEquals(app.request(path).data, repr(name))
            
        f(u'\u1234')
        f(u'foo')

        response = app.request('/', method='POST', data=dict(name='foo'))
        self.assertEquals(response.data, "{'name': u'foo'}")
        
        data = '--boundary\r\nContent-Disposition: form-data; name="x"\r\nfoo\r\n--boundary\r\nContent-Disposition: form-data; name="file"; filename="a.txt"\r\nContent-Type: text/plain\r\n\r\na\r\n--boundary--\r\n'
        headers = {'Content-Type': 'multipart/form-data; boundary=boundary'}
        response = app.request('/multipart', method="POST", data=data, headers=headers)
        self.assertEquals(response.data, 'a')
        
    def testCustomNotFound(self):
        urls_a = ("/", "a")
        urls_b = ("/", "b")
        
        app_a = web.application(urls_a, locals())
        app_b = web.application(urls_b, locals())
        
        app_a.notfound = lambda: web.HTTPError("404 Not Found", {}, "not found 1")
        
        urls = (
            "/a", app_a,
            "/b", app_b
        )
        app = web.application(urls, locals())
        
        def assert_notfound(path, message):
            response = app.request(path)
            self.assertEquals(response.status.split()[0], "404")
            self.assertEquals(response.data, message)
            
        assert_notfound("/a/foo", "not found 1")
        assert_notfound("/b/foo", "not found")
        
        app.notfound = lambda: web.HTTPError("404 Not Found", {}, "not found 2")
        assert_notfound("/a/foo", "not found 1")
        assert_notfound("/b/foo", "not found 2")

    def testIter(self):
        self.assertEquals(app.request('/iter').data, 'hello, world')
        self.assertEquals(app.request('/iter?name=web').data, 'hello, web')

        self.assertEquals(app.request('/iter', method='POST').data, 'hello, world')
        self.assertEquals(app.request('/iter', method='POST', data='name=web').data, 'hello, web')

    def testUnload(self):
        x = web.storage(a=0)

        urls = (
            "/foo", "foo",
            "/bar", "bar"
        )
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

        app.request('/foo')
        self.assertEquals(x.a, 1)

        app.request('/bar')
        self.assertEquals(x.a, 2)

if __name__ == '__main__':
    webtest.main()
