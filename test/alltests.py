import webtest

def suite():
    modules = ["doctests", "db", "application", "session", "auth"]
    return webtest.suite(modules)

if __name__ == "__main__":
    webtest.main()
