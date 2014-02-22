import tempfile
import web
import webtest


class AuthTest(webtest.TestCase):
    dbname = 'sqlite'
    driver = 'sqlite3'
    crypt = None

    usr = 'scott'
    passwd = 'tiger'
    crypted = None
    role = 'admin'

    def setUp(self):
        web.config.auth.crypt = self.crypt
        self.app = web.auto_application()
        try:
            self.remove_database()
        except:
            pass
        self.db = self.make_database()

    def tearDown(self):
        self.remove_database()

    def make_session(self, app):
        dir = tempfile.mkdtemp()
        store = web.session.DiskStore(dir)
        return web.session.Session(app, store)

    def make_database(self):
        db = webtest.setup_database(self.dbname, driver=self.driver)
        db.query("CREATE TABLE users (usr text, passwd text, role text)")
        db.insert('users', usr=self.usr, passwd=self.crypted, role=self.role)
        return db

    def remove_database(self):
        self.db = webtest.setup_database(self.dbname, driver=self.driver)
        self.db.query("DROP TABLE users")

    def testLogin(self):
        ses = self.make_session(self.app)
        auth = web.auth.Auth(ses, self.db)
        auth.login(self.usr, self.passwd)
        assert ses.usr == self.usr

    def testLoginNotExists(self):
        ses = self.make_session(self.app)
        auth = web.auth.Auth(ses, self.db)
        ok = True
        try:
            auth.login('noman', 'weakpass')
        except web.auth.UserNotFound:
            ok = False
        assert not ok
        assert (not 'usr' is ses) or (ses.usr is None)

    def testLoginWrongPasswd(self):
        ses = self.make_session(self.app)
        auth = web.auth.Auth(ses, self.db)
        ok = True
        try:
            auth.login(self.usr, 'weakpass')
        except web.auth.WrongPassword:
            ok = False
        assert not ok
        assert (not 'usr' is ses) or (ses.usr is None)

    def testLogout(self):
        ses = self.make_session(self.app)
        auth = web.auth.Auth(ses, self.db)
        auth.login(self.usr, self.passwd)
        auth.logout()
        assert not ses.usr

    def testRole(self):
        #TODO: decorator test
        pass

    def testRoleNotLogged(self):
        #TODO: decorator test
        pass

    def testRoleWrongRole(self):
        #TODO: decorator test
        pass

    def testRoleWrongRoleLoginPage(self):
        #TODO: decorator test
        pass

    def testHasRole(self):
        ses = self.make_session(self.app)
        auth = web.auth.Auth(ses, self.db)
        auth.login(self.usr, self.passwd)
        assert auth.hasrole(self.role)
        assert auth.hasrole(self.role, 'user')
        assert not auth.hasrole('user')

    def testGetRole(self):
        ses = self.make_session(self.app)
        auth = web.auth.Auth(ses, self.db)
        auth.login(self.usr, self.passwd)
        assert auth.getrole() == self.role

    def testGetRow(self):
        ses = self.make_session(self.app)
        auth = web.auth.Auth(ses, self.db)
        row = auth._getrow(self.usr)
        assert self.usr == row.usr


class BcryptAuthTest(AuthTest):
    crypt = 'bcrypt'
    crypted = '$2a$10$OCbE/4Z8knNjNU3Q8PghvuvlGeJmz1Q.zsnYx2QINvj6EUeWLew1a'


class SHA256SaltAuthTest(AuthTest):
    crypt = 'sha256salt'
    crypted = ('201dbd36ae93683b17e692977ab5d0dca355f60f77d45b4dbf20d884bec25'
               '23c$74a2ee9f833bd548c72f7651457bc3dad69dffb11bcfbaa235d009e0c'
               'cb79dc73')

del AuthTest


class CryptTest(webtest.TestCase):
    alg = None
    passwd = 'tiger'
    crypted = None

    def testEncrypt(self):
        pass

    def testCompare(self):
        pass


class BcryptCryptTest(CryptTest):
    alg = 'bcrypt'
    crypted = '$2a$10$tMS/VsupzEbw1qcHAhRzoeRaqO08seOY9YhxMtZOWwuHaF9.btfNy'

    def testEncrypt(self):
        crypt = web.auth.Crypt()
        crypted = crypt[self.alg].encrypt(self.passwd)
        assert len(crypted) == 60

    def testCompare(self):
        crypt = web.auth.Crypt()
        match = crypt[self.alg].compare(self.passwd, self.crypted)
        assert match


class SHA256SaltCryptTest(CryptTest):
    alg = 'sha256salt'
    crypted = ('ab8bfb997a7783d7fd269ef0bd6167c1ace676156d0586e45ad43e5330628'
               '692$976b7778d6afa81f5b2952af11d3e36c2c4591d9674ef0d3fd9a8491e'
               'd211f4a')
    salt = '976b7778d6afa81f5b2952af11d3e36c2c4591d9674ef0d3fd9a8491ed211f4a'

    def testEncrypt(self):
        crypt = web.auth.Crypt()
        crypted = crypt[self.alg].encrypt(self.passwd)
        assert len(crypted) == 129
        assert crypted.find('$')

    def testEncryptSalt(self):
        crypt = web.auth.Crypt()
        crypted = crypt[self.alg].encrypt(self.passwd, self.salt)
        assert crypted == self.crypted

    def testCompare(self):
        crypt = web.auth.Crypt()
        match = crypt[self.alg].compare(self.passwd, self.crypted)
        assert match


class UnknownAlgCryptTest(CryptTest):
    alg = 'idontexist'

    def testEncrypt(self):
        crypt = web.auth.Crypt()
        raised = False
        try:
            crypt[self.alg].encrypt(self.passwd)
        except web.auth.UnknownCryptAlgorithm:
            raised = True
        assert raised

del CryptTest


if __name__ == "__main__":
    webtest.main()
