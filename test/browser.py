import webtest
import web

urls = (
    "/", "index",
    "/hello/(.*)", "hello",
    "/cookie", "cookie",
    "/setcookie", "setcookie",
    "/redirect", "redirect",
)
app = web.application(urls, globals())

class index:
    def GET(self):
        return "welcome"

class hello:
    def GET(self, name):
        name = name or 'world'
        return "hello, " + name + '!'

class cookie:
    def GET(self):
        return ",".join(sorted(web.cookies().keys()))

class setcookie:
    def GET(self):
        i = web.input()
        for k, v in i.items():
            web.setcookie(k, v)
        return "done"

class redirect:
    def GET(self):
        i = web.input(url='/')
        raise web.seeother(i.url)

class BrowserTest(webtest.TestCase):
    def testCookies(self):
        b = app.browser()
        b.open('http://0.0.0.0/setcookie?x=1&y=2')
        b.open('http://0.0.0.0/cookie')
        self.assertEquals(b.data, 'x,y')

    def testNotfound(self):
        b = app.browser()
        b.open('http://0.0.0.0/notfound')
        self.assertEquals(b.status, 404)

    def testRedirect(self):
        b = app.browser()

        b.open('http://0.0.0.0:8080/redirect')
        self.assertEquals(b.url, 'http://0.0.0.0:8080/')
        b.open('http://0.0.0.0:8080/redirect?url=/hello/foo')
        self.assertEquals(b.url, 'http://0.0.0.0:8080/hello/foo')

        b.open('https://0.0.0.0:8080/redirect')
        self.assertEquals(b.url, 'https://0.0.0.0:8080/')
        b.open('https://0.0.0.0:8080/redirect?url=/hello/foo')
        self.assertEquals(b.url, 'https://0.0.0.0:8080/hello/foo')

if __name__ == "__main__":
    webtest.main()
