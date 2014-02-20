import webtest

def suite():
    modules = ["doctests", "db", "application", "session", "template", "wsgi"]
    return webtest.suite(modules)
    
if __name__ == "__main__":
    webtest.main()
