"""DB test"""
import webtest
import web

class DBTest(webtest.TestCase):
    dbname = 'postgres'
    
    def setUp(self):
        webtest.setup_database(self.dbname)
        web.query("CREATE TABLE person (name text, email text)")

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

    def assertRows(self, n):
        result = web.select('person')
        self.assertEquals(len(list(result)), n)

    def testCommit(self):
        web.transact()
        web.insert('person', False, name='user1')
        web.commit()

        web.transact()
        web.insert('person', False, name='user2')
        web.insert('person', False, name='user3')
        web.commit()
        self.assertRows(3)

    def testRollback(self):
        web.transact()
        web.insert('person', False, name='user1')
        web.insert('person', False, name='user2')
        web.insert('person', False, name='user3')
        web.rollback()
        self.assertRows(0)

    def testNestedTransactions(self):
        web.transact()
        web.insert('person', False, name='user1')
        self.assertRows(1)   

        web.transact()
        web.insert('person', False, name='user2')
        self.assertRows(2)
        web.rollback()
        self.assertRows(1)

        web.transact()
        web.insert('person', False, name='user3')
        web.commit()

        self.assertRows(2)
        web.commit()
        



class SqliteTest(DBTest):
    dbname = "sqlite"

    def testNestedTransactions(self):
        # nested transactions are not supported in sqlite
        pass
    
class MySQLTest(DBTest):
    dbname = "mysql"

    def setUp(self):
        web.config._hasPooling = False
        webtest.setup_database(self.dbname)
        # In mysql, transactions are supported only with INNODB engine.
        web.query("CREATE TABLE person (name text, email text) ENGINE InnoDB")

if __name__ == '__main__':
    webtest.main()
