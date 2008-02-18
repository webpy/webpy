"""webtest: test utilities.
"""
import unittest
import sys, os

# adding current directory to path to make sure local copy of web module is used.
sys.path.insert(0, '.')

import web


class TestCase(unittest.TestCase):
    def setUpAll(self):
        pass
        
    def tearDownAll(self):
        pass
        
    def shortDescription(self):
        """overridden to not return docstrings"""
        return None
        
class TestSuite(unittest.TestSuite):
    """A TestSuite with once per TestCase setUpAll() and tearDownAll().
    Adopted from test/testlib/testing.py file in SQLAlchemy test suite. 
    """

    def __init__(self, tests=()):
        if len(tests) >0 and isinstance(tests[0], TestCase):
            self._initTest = tests[0]
        else:
            self._initTest = None
        unittest.TestSuite.__init__(self, tests)

    def do_run(self, result):
        # nice job unittest !  you switched __call__ and run() between py2.3
        # and 2.4 thereby making straight subclassing impossible !
        for test in self._tests:
            if result.shouldStop:
                break
            test(result)
        return result

    def run(self, result):
        return self(result)

    def __call__(self, result):
        try:
            if self._initTest is not None:
                self._initTest.setUpAll()
        except:
            # skip tests if global setup fails
            ex = self.__exc_info()
            for test in self._tests:
                result.addError(test, ex)
            return False
        try:
            return self.do_run(result)
        finally:
            try:
                if self._initTest is not None:
                    self._initTest.tearDownAll()
            except:
                result.addError(self._initTest, self.__exc_info())
                pass

    def __exc_info(self):
        """Return a version of sys.exc_info() with the traceback frame
           minimised; usually the top level of the traceback frame is not
           needed.
           ripped off out of unittest module since its double __
        """
        exctype, excvalue, tb = sys.exc_info()
        if sys.platform[:4] == 'java': ## tracebacks look different in Jython
            return (exctype, excvalue, tb)
        return (exctype, excvalue, tb)

# monkeypatch
unittest.TestLoader.suiteClass = TestSuite

def runTests(suite):
    runner = unittest.TextTestRunner()
    return runner.run(suite)

def main(suite=None):
    if not suite:
        main_module = __import__('__main__')
        suite = module_suite(main_module, sys.argv[1:] or None)

    result = runTests(suite)
    sys.exit(not result.wasSuccessful())

def load_modules(names):
    return [__import__(name, None, None, "x") for name in names]

def module_suite(module, classnames=None):
    """Makes a suite from a module."""
    if hasattr(module, 'suite'):
        return module.suite()
    elif classnames:
        return unittest.TestLoader().loadTestsFromNames(classnames, module)
    else:
        return unittest.TestLoader().loadTestsFromModule(module)

def doctest_suite(module_names):
    """Makes a test suite from doctests."""
    import doctest
    suite = unittest.TestSuite()
    for mod in load_modules(module_names):
        suite.addTest(doctest.DocTestSuite(mod))
    return suite
    
def suite(module_names):
    """Creates a suite from multiple modules."""
    suite = unittest.TestSuite()
    for mod in load_modules(module_names):
        suite.addTest(module_suite(mod))
    return suite
    
def setup_database(dbname):
    if dbname == 'sqlite':
        db = web.database(dbn=dbname, db='webpy.db')
    else:
        db = web.database(dbn=dbname, db='webpy', user='scott', pw='tiger')
        
    if '-v' in sys.argv:
        db.printing = True
    return db
