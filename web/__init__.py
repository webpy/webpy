#!/usr/bin/env python3
"""web.py: makes web apps (http://webpy.org)"""

from . import (  # noqa: F401
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
from .application import *  # noqa: F401,F403
from .db import *  # noqa: F401,F403
from .debugerror import *  # noqa: F401,F403
from .http import *  # noqa: F401,F403
from .httpserver import *  # noqa: F401,F403
from .net import *  # noqa: F401,F403
from .utils import *  # noqa: F401,F403
from .webapi import *  # noqa: F401,F403
from .wsgi import *  # noqa: F401,F403

__version__ = "0.62"
__author__ = [
    "Aaron Swartz <me@aaronsw.com>",
    "Anand Chitipothu <anandology@gmail.com>",
]
__license__ = "public domain"
__contributors__ = "see http://webpy.org/changes"
