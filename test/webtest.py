"""webtest: test utilities.
"""
import unittest
from unittest import TestCase
import sys, os

# adding current directory to path to make sure local copy of web module is used.
sys.path.insert(0, '.')

import web

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
        web.config.db_parameters = dict(dbn=dbname, db='webpy.db')
    else:
        web.config.db_parameters = dict(dbn=dbname, db='webpy', user='scott', pw='tiger')
        
    #web.config.db_printing=True
    web.load()
