"""test utilities
(part of web.py)
"""
import unittest, doctest
import sys, re
import web

TestCase = unittest.TestCase
TestSuite = unittest.TestSuite

def load_modules(names):
    return [__import__(name, None, None, "x") for name in names]

def module_suite(module, classnames=None):
    """Makes a suite from a module."""
    if classnames:
        return unittest.TestLoader().loadTestsFromNames(classnames, module)
    elif hasattr(module, 'suite'):
        return module.suite()
    else:
        return unittest.TestLoader().loadTestsFromModule(module)

#Little wrapper needed for dealing with the differents unicode strings representation in Py2 and Py3
#Source : Dirkjan Ochtman (https://dirkjan.ochtman.nl/writing/2014/07/06/single-source-python-23-doctests.html)
class Py23DocChecker(doctest.OutputChecker):
  def check_output(self, want, got, optionflags):
    if sys.version_info[0] > 2:
      want = re.sub("u'(.*?)'", "'\\1'", want)
      want = re.sub('u"(.*?)"', '"\\1"', want)
    return doctest.OutputChecker.check_output(self, want, got, optionflags)

def doctest_suite(module_names):
    """Makes a test suite from doctests."""
    suite = TestSuite()
    for mod in load_modules(module_names):
        suite.addTest(doctest.DocTestSuite(mod, checker=Py23DocChecker()))
    return suite
    
def suite(module_names):
    """Creates a suite from multiple modules."""
    suite = TestSuite()
    for mod in load_modules(module_names):
        suite.addTest(module_suite(mod))
    return suite

def runTests(suite):
    runner = unittest.TextTestRunner()
    return runner.run(suite)

def main(suite=None):
    if not suite:
        main_module = __import__('__main__')
        # allow command line switches
        args = [a for a in sys.argv[1:] if not a.startswith('-')]
        suite = module_suite(main_module, args or None)

    result = runTests(suite)
    sys.exit(not result.wasSuccessful())

