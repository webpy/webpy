
import web

urls = ("/", "c")
app = web.application(urls, globals(), autoreload=True)

class c:
    def GET(self):
        return "c"

