import webtest

def suite():
    modules = ["doctests", "db", "form"]
    return webtest.suite(modules)
    
if __name__ == "__main__":
    webtest.main()
