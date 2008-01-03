"""DB test"""
import webtest
import web

class DBTest(webtest.TestCase):
    dbname = 'postgres'
    
    def setUp(self):
        web.config._hasPooling = False
        webtest.setup_database(self.dbname)
        web.query("CREATE TABLE person (name text unique, email text)")

    def tearDown(self):
        # there might be some error with the current connection, delete from a new connection
        webtest.setup_database(self.dbname)
        web.query('DROP TABLE person')
    
    def testUnicode(self):
        """Bug#177265: unicode queries throw errors"""
        web.select('person', where='name=$name', vars={'name': u'\xf4'})

    def testWrongQuery(self):
        # It should be possible to run a correct query after getting an error from a wrong query.
        try:
            web.select('wrong_table')
        except:
            pass
        web.select('person')

class SqliteTest(DBTest):
    dbname = "sqlite"
    
class MySQLTest(DBTest):
    dbname = "mysql"

if __name__ == '__main__':
    webtest.main()
