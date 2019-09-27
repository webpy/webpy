web.py is a web framework for Python that is as simple as it is powerful.

Visit http://webpy.org/ for more information.

[![build status](https://secure.travis-ci.org/webpy/webpy.png?branch=master)](https://travis-ci.org/webpy/webpy)
[![Codecov Test Coverage](https://codecov.io/gh/webpy/webpy/branch/master/graphs/badge.svg?style=flat)](https://codecov.io/gh/webpy/webpy)

The latest stable release `0.40` supports both Python 2.7 and Python >= 3.5.
To install it, please run:

```
# For Python 2.7
pip2 install web.py==0.40

# For Python 3
pip3 install web.py==0.40
```

You can also download it from [GitHub Releases](https://github.com/webpy/webpy/releases)
page, then install it manually:

```
unzip webpy-0.40.zip
cd webpy-0.40/
python3 setup.py install
```

Note: `0.40` is the last release which supports Python 2. Future releases
will drop support for Python 2.

### Philosophy

The web.py slogan is: “_Think about the ideal way to write a web app. Write the code to make it happen._”

This is literally how I developed web.py. I wrote a web application in Python just imagining how I wanted the API to be. It started with import web, of course, and then had a place to define URLs, simple functions for GET and POST, a thing to deal with input variables and so on. Once the code looked right to me, I did whatever it took to make it execute without changing the application code – the result was web.py.

In response to someone complaining about web.py having "yet another template language", I wrote a bit more about my philosophy:

    You don't have to use it – each part of web.py is completely separate from the others. But you’re right, it is “yet another template language”. And I’m not going to apologize for it.

    The goal of web.py is to build the ideal way to make web apps. If reinventing old things with only small differences were necessary to achieve this goal, I would defend reinventing them. The difference between the ideal way and the almost-ideal way is, as Mark Twain suggested, the difference between the lightning and the lightning bug.

    But these aren’t just small differences. Instead of exposing Python objects, web.py allows you to build HTTP responses. Instead of trying to make the database look like an object, web.py makes the database easier to use. And instead of coming up with yet another way to write HTML, the web.py template system tries to bring Python into HTML. Not many other people are really trying to do that.

    You can disagree that these ways are better and say why. But simply criticizing them for being different is a waste of time. Yes, they are different. That’s the whole point.

started by [Aaron Swartz](https://en.wikipedia.org/wiki/Aaron_Swartz) and http://waaronsw.com
