"""
    Authentication and authorization tools
    (for web.py)
"""
import utils
import webapi

all = [
    "Auth"
]

webapi.config.auth_parameters = utils.storage({
    'table_name': 'users',
    'user_column': 'usr',
    'password_column': 'passwd',
    'role_column': 'role'
})


class Auth(object):
    def __init__(self, ses, db, lgn_pg=None):
        self.ses = ses
        self.db = db
        self.lgn_pg = lgn_pg

    pass

if __name__ == "__main__":
    import doctest
    doctest.testmod()
