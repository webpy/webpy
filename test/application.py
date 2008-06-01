import webtest
import time

import web

data = """
import web

urls = ("/", "%(classname)s")
app = web.application(urls, globals(), autoreload=True)

class %(classname)s:
    def GET(self):
        return "%(output)s"

"""

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

if __name__ == '__main__':
    webtest.main()

