"""
web.py test suite.
"""

import sys
import web
import unittest

def commit(value):
    web.transact()
    web.insert("test", seqname=False, value=value)
    web.commit()

def rollback(value):
    web.transact()
    web.insert("test", seqname=False, value=value)
    web.rollback()

def getrow(value):
    d = web.select('test', where='value=$value', vars=locals())
    a = (d and d[0].value) or None
    return a

def assert_presence(*values):
    for v in values:
        assert getrow(v) is not None

def assert_absence(*values):
    for v in values:
        assert getrow(v) is None
    
class PostgresTest(unittest.TestCase):
    parameters = dict(dbn="postgres", db="webtest", user="webpy", pw="")
    
    def setUp(self):
        web.config.db_parameters = self.parameters
        #web.config.db_printing = True
        web.load()
        web.delete("test", where="1=1")

    def tearDown(self):
        sys.stdout.flush()
        sys.stderr.flush()

    def testCommit(self):
        commit(1)
        assert_presence(1)
        
    def testRollback(self):
        rollback(1)
        assert_absence(1)
        
class MySQLTest(PostgresTest):
    parameters = dict(dbn="mysql", db="webtest", user="webpy", pw="")

if __name__ == "__main__":
    unittest.main()
    
