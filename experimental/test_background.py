#!/usr/bin/env python
# -*- coding: utf-8 -*-
import web
from web.background import background, backgrounder
from datetime import datetime; now = datetime.now
from time import sleep

urls = (
    '/', 'index',
    )

class index:
    @backgrounder
    def GET(self):
        print "Started at %s" % now()
        print "hit f5 to refresh!"
        longrunning()


@background
def longrunning():
    for i in range(10):
        sleep(1)
        print "%s: %s" % (i, now())

if __name__ == '__main__':
    app = web.application(urls, globals())
    app.run()
