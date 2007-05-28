#!/usr/bin/env python

# ...

from distutils.core import setup

setup(name='web.py',
      version='0.21',
      description='web.py: makes web apps',
      author='Aaron Swartz',
      author_email='me@aaronsw.com',
      url=' http://webpy.org/',
      packages=['web', 'web.wsgiserver'],
      long_description="Think about the ideal way to write a web app. Write the code to make it happen.",
      license="Public domain",
      platforms=["any"],
     )
