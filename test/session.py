import webtest
import web
import tempfile

class Browser:
    """Browser simulation.
    Stores cookies across requests.
    """
    def __init__(self, app):
        self.app = app
        self.cookies = {}
        self.response = None

    def open(self, path):
        headers = {}
        if self.cookies:
            headers['cookie'] = self.cookie_header()
        self.response = self.app.request(path, headers=headers)
        if 'Set-Cookie' in self.response.headers:
            self.read_cookie(self.response.headers['Set-Cookie'])
        return self.response.data
        
    def cookie_header(self):
        return "; ".join(["%s=%s" % (k, v) for k, v in self.cookies.items()])
        
    def read_cookie(self, header):
        tokens = header.split('; ')
        d = {}
        name, value = tokens[0].split("=")
        for t in tokens[1:]:
            k, v = t.split("=")
            d[k.lower()] = v
            
        #@@ fix this
        if 'expires' in d:
            d.pop('name', None)
            return
        
        self.cookies[name] = value
            
class SessionTest(webtest.TestCase):
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
                
        self.app = app
        self.session = session
        
    def make_session(self, app):
        dir = tempfile.mkdtemp()
        store = web.session.DiskStore(tempfile.mkdtemp())
        return web.session.Session(app, store, {'count': 0})
        
    def testSession(self):
        b = Browser(self.app)
        self.assertEquals(b.open('/count'), '1')
        self.assertEquals(b.open('/count'), '2')
        self.assertEquals(b.open('/count'), '3')
        b.open('/reset')
        self.assertEquals(b.open('/count'), '1')

    def testParallelSessions(self):
        b1 = Browser(self.app)
        b2 = Browser(self.app)
        
        b1.open('/count')
        
        for i in range(1, 10):
            self.assertEquals(b1.open('/count'), str(i+1))
            self.assertEquals(b2.open('/count'), str(i))

    def testBadSessionId(self):
        b = Browser(self.app)
        self.assertEquals(b.open('/count'), '1')
        self.assertEquals(b.open('/count'), '2')

        b.cookies['webpy_session_id'] = '/etc/password'
        self.assertEquals(b.open('/count'), '1')

class DBSessionTest(SessionTest):
    """Session test with db store."""
    def make_session(self, app):
        db = webtest.setup_database("postgres")
        #db.printing = True
        db.query("" 
            + "CREATE TABLE session ("
            + "    session_id char(128) unique not null,"
            + "    atime timestamp default (current_timestamp at time zone 'utc'),"
            + "    data text)"
        )
        store = web.session.DBStore(db, 'session')
        return web.session.Session(app, store, {'count': 0})
         
    def tearDown(self):
        # there might be some error with the current connection, delete from a new connection
        self.db = webtest.setup_database("postgres")
        self.db.query('DROP TABLE session')

if __name__ == "__main__":
    webtest.main()
