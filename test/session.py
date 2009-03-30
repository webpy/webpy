import webtest
import web
import tempfile

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
        b = self.app.browser() 
        self.assertEquals(b.open('/count').read(), '1')
        self.assertEquals(b.open('/count').read(), '2')
        self.assertEquals(b.open('/count').read(), '3')
        b.open('/reset')
        self.assertEquals(b.open('/count').read(), '1')

    def testParallelSessions(self):
        b1 = self.app.browser()
        b2 = self.app.browser()
        
        b1.open('/count')
        
        for i in range(1, 10):
            self.assertEquals(b1.open('/count').read(), str(i+1))
            self.assertEquals(b2.open('/count').read(), str(i))

    def testBadSessionId(self):
        b = self.app.browser()
        self.assertEquals(b.open('/count').read(), '1')
        self.assertEquals(b.open('/count').read(), '2')
        
        cookie = b.cookiejar._cookies['0.0.0.0']['/']['webpy_session_id']
        cookie.value = '/etc/password'
        self.assertEquals(b.open('/count').read(), '1')

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
