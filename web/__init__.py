#!/usr/bin/env python
"""web.py: makes web apps (http://webpy.org)"""

from __future__ import generators

from . import (
    db,
    debugerror,
    form,
    http,
    httpserver,
    net,
    session,
    template,
    utils,
    webapi,
    wsgi,
)
from .application import *
from .db import *
from .debugerror import *
from .http import *
from .httpserver import *
from .net import *
from .utils import *
from .webapi import *
from .wsgi import *

__version__ = "0.51"
__author__ = [
    "Aaron Swartz <me@aaronsw.com>",
    "Anand Chitipothu <anandology@gmail.com>",
]
__license__ = "public domain"
__contributors__ = "see http://webpy.org/changes"
