"""Run all doctests in web.py.
"""
import webtest

def suite():
    modules = [
        "web.application",
        "web.db", 
        "web.http", 
        "web.net", 
        "web.session",
        "web.template",
        "web.utils", 
#        "web.webapi", 
#        "web.wsgi", 
    ]
    return webtest.doctest_suite(modules)
    
if __name__ == "__main__":
    webtest.main()
