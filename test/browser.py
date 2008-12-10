import webtest
import web

urls = (
    "/cookie", "cookie",
    "/setcookie", "setcookie",
)
app = web.application(urls, globals())

class cookie:
    def GET(self):
        return ",".join(sorted(web.cookies().keys()))

class setcookie:
    def GET(self):
        i = web.input()
        for k, v in i.items():
            web.setcookie(k, v)
        return "done"

class BrowserTest(webtest.TestCase):
    def testCookies(self):
        b = app.browser()
        b.open('http://0.0.0.0/setcookie?x=1&y=2')
        b.open('http://0.0.0.0/cookie')
        self.assertEquals(b.data, 'x')

    def testNotfound(self):
        b = app.browser()
        b.open('http://0.0.0.0/notfound')
        self.assertEquals(b.status, 404)

if __name__ == "__main__":
    webtest.main()
