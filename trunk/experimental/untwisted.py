import random

from twisted.internet import reactor, defer
from twisted.web import http

import simplejson

import web

class Request(http.Request):
    def process(self):
        self.content.seek(0, 0)
        env = {
          'REMOTE_ADDR': self.client.host,
          'REQUEST_METHOD': self.method,
          'PATH_INFO': self.path,
          'CONTENT_LENGTH': web.intget(self.getHeader('content-length'), 0),
          'wsgi.input': self.content
        }
        if '?' in self.uri:
            env['QUERY_STRING'] = self.uri.split('?', 1)[1]

        for k, v in self.received_headers.iteritems():
            env['HTTP_' + k.upper()] = v
        
        if self.path.startswith('/static/'):
            f = web.lstrips(self.path, '/static/')
            assert '/' not in f
            #@@@ big security hole
            self.write(file('static/' + f).read())
            return self.finish()

        web.webapi._load(env)
        web.ctx.trequest = self
        result = self.actualfunc()
        self.setResponseCode(int(web.ctx.status.split()[0]))
        for (h, v) in web.ctx.headers:
            self.setHeader(h, v)
        self.write(web.ctx.output)
        if not web.ctx.get('persist'):
            self.finish()

class Server(http.HTTPFactory):
    def __init__(self, func):
        self.func = func

    def buildProtocol(self, addr):
        """Generate a channel attached to this site.
        """
        channel = http.HTTPFactory.buildProtocol(self, addr)
        class MyRequest(Request):
            actualfunc = staticmethod(self.func)
        channel.requestFactory = MyRequest
        channel.site = self
        return channel

def runtwisted(func):
    reactor.listenTCP(8086, Server(func))
    reactor.run()

def newrun(inp, fvars):
    print "Running on http://0.0.0.0:8086/"
    runtwisted(web.webpyfunc(inp, fvars, False))

def iframe(url):
    return """
    <iframe height="0" width="0" style="display: none" src="%s"/></iframe>
    """ % url #("http://%s.ajaxpush.lh.theinfo.org:8086%s" % (random.random(), url))

class Feed:
    def __init__(self):
        self.sessions = []
    
    def subscribe(self):
        request = web.ctx.trequest
        self.sessions.append(request)
        request.connectionLost = lambda reason: self.sessions.remove(request)
        web.ctx.persist = True
    
    def publish(self, text):
        for x in self.sessions:
            x.write(text)

class JSFeed(Feed):
    def __init__(self, callback="callback"):
        Feed.__init__(self)
        self.callback = callback
        
    def publish(self, obj):
        web.debug("publishing")
        Feed.publish(self, 
          '<script type="text/javascript">window.parent.%s(%s)</script>' % (self.callback, simplejson.dumps(obj) + 
          " " * 2048))

if __name__ == "__main__":
    mfeed = JSFeed()

    urls = (
      '/', 'view',
      '/js', 'js',
      '/send', 'send'
    )

    class view:
        def GET(self):
            print """
<script type="text/javascript">
function callback(item) {
  document.getElementById('content').innerHTML += "<p>" + item + "</p>";
}
</script>

<h2>Today's News</h2>

<div id="content"></div>

<h2>Contribute</h2>
<form method="post" action="/send">
  <textarea name="text"></textarea>
  <input type="submit" value="send" />
</form>
<iframe id="foo" height="0" width="0" style="display: none" src="/js"/></iframe>
            """
        
    class js:
        def GET(self):
            mfeed.subscribe()
    
    class send:
        def POST(self):
            mfeed.publish('<p>%s</p>' % web.input().text + (" " * 2048))
            web.seeother('/')
    
    newrun(urls, globals())