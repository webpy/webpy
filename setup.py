#!/usr/bin/env python

import os
from setuptools import setup
from web import __version__

rootdir = os.path.abspath(os.path.dirname(__file__))

# Get the long description from the README file
with open(os.path.join(rootdir, "README.md")) as in_file:
    long_description = in_file.read()

setup(
    name="web.py",
    version=__version__,
    description="web.py: makes web apps",
    author="Aaron Swartz",
    author_email="me@aaronsw.com",
    maintainer="Anand Chitipothu",
    maintainer_email="anandology@gmail.com",
    url="http://webpy.org/",
    packages=["web", "web.contrib"],
    install_requires=["cheroot"],
    long_description=long_description,
    long_description_content_type="text/markdown",
    license="Public domain",
    platforms=["any"],
    classifiers=[
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
    ],
)
