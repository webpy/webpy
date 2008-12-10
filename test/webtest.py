"""webtest: test utilities.
"""
import sys

# adding current directory to path to make sure local modules can be imported
sys.path.insert(0, '.')

from web.test import *
    
def setup_database(dbname, pooling=False):
    if dbname == 'sqlite':
        db = web.database(dbn=dbname, db='webpy.db', pooling=pooling)
    else:
        db = web.database(dbn=dbname, db='webpy', user='scott', pw='tiger', pooling=pooling)

    db.printing = '-v' in sys.argv
    return db
