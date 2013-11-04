.. web.py documentation master file, created by
   sphinx-quickstart on Sun Oct 27 15:35:05 2013.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to web.py's documentation!
==================================

Contents:

.. toctree::
   :maxdepth: 2

   input
   db

Hello World
===========

URL Mapping
===========

urls = (...)

regular expressions and grouping

Taking Inputs
=============

web.input()
web.input(page=0)
reading GET and POST
reading files

Working with database
=====================

web.database()

db.query
db.select
db.insert
db.multiple_insert
db.delete

working with transactions

with db.transaction():
    db.insert(..)

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

