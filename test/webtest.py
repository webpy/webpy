"""webtest: test utilities.
"""
import sys, os

# adding current directory to path to make sure local modules can be imported
sys.path.insert(0, '.')

from web.test import *
    
def setup_database(dbname, driver=None, pooling=False):
    if dbname == 'sqlite':
        db = web.database(dbn=dbname, db='webpy.db', pooling=pooling, driver=driver)
    elif dbname == 'postgres':
        user = os.getenv('USER')
        db = web.database(dbn=dbname, db='webpy', user=user, pw='', pooling=pooling, driver=driver)
    else:
        db = web.database(dbn=dbname, db='webpy', user='scott', pw='tiger', pooling=pooling, driver=driver)

    db.printing = '-v' in sys.argv
    return db
