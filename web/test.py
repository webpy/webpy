"""test utilities
(part of web.py)
"""
import doctest
import sys
import unittest

TestCase = unittest.TestCase
TestSuite = unittest.TestSuite


def load_modules(names):
    return [__import__(name, None, None, "x") for name in names]


def module_suite(module, classnames=None):
    """Makes a suite from a module."""
    if classnames:
        return unittest.TestLoader().loadTestsFromNames(classnames, module)
    elif hasattr(module, "suite"):
        return module.suite()
    else:
        return unittest.TestLoader().loadTestsFromModule(module)


def doctest_suite(module_names):
    """Makes a test suite from doctests."""
    suite = TestSuite()
    for mod in load_modules(module_names):
        suite.addTest(doctest.DocTestSuite(mod))
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
        main_module = __import__("__main__")
        # allow command line switches
        args = [a for a in sys.argv[1:] if not a.startswith("-")]
        suite = module_suite(main_module, args or None)

    result = runTests(suite)
    sys.exit(not result.wasSuccessful())
