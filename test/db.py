"""DB test"""
import webtest
import web

class DBTest(webtest.TestCase):
    dbname = 'postgres'
    
    def setUpAll(self):
        self.db = webtest.setup_database(self.dbname)
        self.db.query("CREATE TABLE person (name text, email text)")

    def tearDownAll(self):
        # there might be some error with the current connection, delete from a new connection
        self.db = webtest.setup_database(self.dbname)
        self.db.query('DROP TABLE person')
    
    def testUnicode(self):
        """Bug#177265: unicode queries throw errors"""
        self.db.select('person', where='name=$name', vars={'name': u'\xf4'})

class SqliteTest(DBTest):
    dbname = "sqlite"
    
class MySQLTest(DBTest):
    dbname = "mysql"

if __name__ == '__main__':
    webtest.main()
