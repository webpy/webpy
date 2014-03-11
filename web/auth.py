"""
    Authentication and authorization tools
    (for web.py)
"""
import hashlib
import os
import utils
import webapi as web

try:
    import bcrypt
except ImportError:
    pass

__all__ = [
    "Auth", "Crypt",
    "UnknownCryptAlgorithm", "UserNotFound", "WrongPassword", "LogoutError"
]

web.config.auth = utils.storage({
    # database settings
    'table_name': 'users',
    'user_column': 'usr',
    'password_column': 'passwd',
    'role_column': 'role',
    # hashing/crypting (bcrypt|sha256salt)
    'crypt': 'sha256salt',
    'bcrypt_loops': 10,
    'sha_salt_len': 32
})


class UnknownCryptAlgorithm(Exception):
    """raised for unsupported password crypt algorithms"""
    pass


class UserNotFound(Exception):
    """raised when the user is not found in the database"""
    pass


class WrongPassword(Exception):
    """raised if inserted password do not match password in database"""
    pass


class LogoutError(Exception):
    """raised when logout failed"""
    pass


class Auth(object):
    __slots__ = [
        '_ses', '_db', '_lgn_pg', '_config', '_crypt'
    ]

    def __init__(self, ses, db, lgn_pg=None):
        self._ses = ses
        self._db = db
        self._lgn_pg = lgn_pg

        self._config = utils.storage(web.config.auth)
        self._db.user = None
        self._crypt = Crypt()

    def login(self, usr, passwd):
        row = self._getrow(usr)
        if not row:
            raise UserNotFound

        alg = self._config.crypt
        if self._crypt[alg].compare(passwd, row.passwd):
            self._ses.usr = usr
        else:
            raise WrongPassword

    def logout(self):
        self._ses.usr = None
        done = False if self._ses.usr else True
        if not done:
            raise LogoutError

    def role(self, *rargs):
        def real_role(function):
            def wrapper(*args, **kwargs):
                hasrole = self.hasrole(*rargs)
                if hasrole:
                    return function(*args, **kwargs)
                else:
                    if self._lgn_pg:
                        return web.seeother(self._lgn_pg)
                    else:
                        raise web.forbidden()
            return wrapper
        return real_role

    def hasrole(self, *rargs):
        roles = []
        for r in rargs:
            roles.append(r)
        role = self.getrole()
        hasrole = role in roles
        return hasrole

    def getrole(self):
        try:
            user = self._ses.usr
            row = self._getrow(user)
            return row.role
        except AttributeError:
            return None

    def _getrow(self, usr):
        row = self._db.select(self._config.table_name, where="usr=$usr",
                              limit=1, vars={'usr': usr})
        try:
            return row[0]
        except IndexError:
            return None


class Crypt:
    _config = utils.storage(web.config.auth)
    _algs = ['bcrypt', 'sha256salt']

    def __getitem__(self, key):
        if key == 'bcrypt':
            return self.Bcrypt
        elif key == 'sha256salt':
            return self.SHA256Salt
        else:
            raise UnknownCryptAlgorithm

    def encrypt(self, *args, **kwargs):
        return self[self._config.crypt].encrypt(*args, **kwargs)

    def compare(self, *args, **kwargs):
        return self[self._config.crypt].compare(*args, **kwargs)

    class Bcrypt:
        @staticmethod
        def encrypt(passwd):
            salt = bcrypt.gensalt(Crypt._config.bcrypt_loops)
            crypted = bcrypt.hashpw(passwd, salt)
            return crypted

        @staticmethod
        def compare(plain, crypted):
            plain_crypted = bcrypt.hashpw(plain, crypted)
            match = plain_crypted == crypted
            return match

    class SHA256Salt:
        @staticmethod
        def encrypt(passwd, salt=None):
            if not salt:
                salt_len = Crypt._config.sha_salt_len
                salt = os.urandom(salt_len).encode('hex')
            crypted = hashlib.sha256(passwd + salt).hexdigest() + '$' + salt
            return crypted

        @staticmethod
        def compare(plain, crypted):
            salt = crypted.split('$', 1)[1]
            plain_crypted = Crypt.SHA256Salt.encrypt(plain, salt)
            match = plain_crypted == crypted
            return match


if __name__ == "__main__":
    import doctest
    doctest.testmod()
