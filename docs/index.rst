.. web.py documentation master file, created by
   sphinx-quickstart on Sun Oct 27 15:35:05 2013.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to web.py's documentation!
==================================

Contents:

.. toctree::
   :maxdepth: 3

   urlmapping
   input
   db
   templating
   deploying
   api

Getting Started
===============

Building webapps with web.py is easy. To get started, save the following code as say, `hello.py` and run it with `python hello.py`. Now point your browser to `http://localhost:8080/` which responds you with 'Hello, world!'. Hey, you're done with your first program with with web.py - with just 8 lines of code!

::

    import web

    urls = ("/.*", "hello")
    app = web.application(urls, globals())

    class hello:
        def GET(self):
            return 'Hello, world!'

    if __name__ == "__main__":
        app.run()

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

