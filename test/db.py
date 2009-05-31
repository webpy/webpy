"""DB test"""
import webtest
import web

class DBTest(webtest.TestCase):
    dbname = 'postgres'
    driver = None
    
    def setUp(self):
        self.db = webtest.setup_database(self.dbname, driver=self.driver)
        self.db.query("CREATE TABLE person (name text, email text, active boolean)")

    def tearDown(self):
        # there might be some error with the current connection, delete from a new connection
        self.db = webtest.setup_database(self.dbname, driver=self.driver)
        self.db.query('DROP TABLE person')
        
    def _testable(self):
        try:
            webtest.setup_database(self.dbname, driver=self.driver)
            return True
        except ImportError, e:
            print >> web.debug, str(e), "(ignoring %s)" % self.__class__.__name__
            return False
    
    def testUnicode(self):
        # Bug#177265: unicode queries throw errors
        self.db.select('person', where='name=$name', vars={'name': u'\xf4'})
    
    def assertRows(self, n):
        result = self.db.select('person')
        self.assertEquals(len(list(result)), n)
        
    def testCommit(self):
        t = self.db.transaction()
        self.db.insert('person', False, name='user1')
        t.commit()

        t = self.db.transaction()
        self.db.insert('person', False, name='user2')
        self.db.insert('person', False, name='user3')
        t.commit()
    
        self.assertRows(3)
        
    def testRollback(self):
        t = self.db.transaction()
        self.db.insert('person', False, name='user1')
        self.db.insert('person', False, name='user2')
        self.db.insert('person', False, name='user3')
        t.rollback()        
        self.assertRows(0)
        
    def testWrongQuery(self):
        # It should be possible to run a correct query after getting an error from a wrong query.
        try:
            self.db.select('notthere')
        except:
            pass
        self.db.select('person')
        
    def testNestedTransactions(self):
        t1 = self.db.transaction()
        self.db.insert('person', False, name='user1')
        self.assertRows(1)        
        
        t2 = self.db.transaction()
        self.db.insert('person', False, name='user2')
        self.assertRows(2)  
        t2.rollback()
        self.assertRows(1)  
        t3 = self.db.transaction()
        self.db.insert('person', False, name='user3')
        self.assertRows(2)  
        t3.commit()
        t1.commit()
        self.assertRows(2)
        
    def testPooling(self):
        # can't test pooling if DBUtils is not installed
        try:
            import DBUtils
        except ImportError:
            return
        db = webtest.setup_database(self.dbname, pooling=True)
        self.assertEquals(db.ctx.db.__class__.__module__, 'DBUtils.PooledDB')
        db.select('person', limit=1)

    def test_multiple_insert(self):
        db = webtest.setup_database(self.dbname)
        db.multiple_insert('person', [dict(name='a'), dict(name='b')], seqname=False)

        assert db.select("person", where="name='a'")
        assert db.select("person", where="name='b'")

    def test_result_is_unicode(self):
        db = webtest.setup_database(self.dbname)
        self.db.insert('person', False, name='user')
        name = db.select('person')[0].name
        self.assertEquals(type(name), unicode)

    def testBoolean(self):
        def t(active):
            name ='name-%s' % active
            self.db.insert('person', False, name=name, active=active)
            a = self.db.select('person', where='name=$name', vars=locals())[0].active
            self.assertEquals(a, active)
        t(False)
        t(True)

class PostgresTest(DBTest):
    dbname = "postgres"
    driver = "psycopg2"

class PostgresTest_psycopg(PostgresTest):
    driver = "psycopg"

class PostgresTest_pgdb(PostgresTest):
    driver = "pgdb"

class SqliteTest(DBTest):
    dbname = "sqlite"
    driver = "sqlite3"
    
    def testNestedTransactions(self):
        #nested transactions does not work with sqlite
        pass

class SqliteTest_pysqlite2(SqliteTest):
    driver = "pysqlite2.dbapi2"

class MySQLTest(DBTest):
    dbname = "mysql"
    
    def setUp(self):
        self.db = webtest.setup_database(self.dbname)
        # In mysql, transactions are supported only with INNODB engine.
        self.db.query("CREATE TABLE person (name text, email text) ENGINE=INNODB")

    def testBoolean(self):
        # boolean datatype is not suppoted in MySQL (at least until v5.0)
        pass

del DBTest

def is_test(cls):
    import inspect
    return inspect.isclass(cls) and webtest.TestCase in inspect.getmro(cls)

# ignore db tests when the required db adapter is not found.
for t in globals().values():
    if is_test(t) and not t('_testable')._testable():
        del globals()[t.__name__]
del t

try:
    import DBUtils
except ImportError, e:
    print >> web.debug, str(e) + "(ignoring testPooling)"

if __name__ == '__main__':
    webtest.main()
