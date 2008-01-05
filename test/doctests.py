"""Run all doctests in web.py.
"""
import webtest

def suite():
    modules = ["web.utils", "web.db", "web.net", "web.wsgi", "web.http", "web.webapi", "web.request", "web.template"]
    return webtest.doctest_suite(modules)
    
if __name__ == "__main__":
    webtest.main()
