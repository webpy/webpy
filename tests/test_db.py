"""DB test"""
from __future__ import print_function

import importlib
import os
import unittest

import web

try:
    unicode  # Python 2
except NameError:
    unicode = str  # Python 3


def try_import(name):
    try:
        return importlib.import_module(name)
    except ImportError:
        return None


def requires_module(name):
    module = try_import(name)

    # this doesn't seem to be working. The simple decorator below seems to be working.
    # return pytest.mark.skipif(module is None, reason="requires {} module".format(name))

    def decorator(cls):
        if module:
            return cls
        else:

            class Foo:
                pass

            print(
                "skipping all tests from {} as {} module is not found".format(
                    cls.__name__, name
                )
            )
            return Foo

    return decorator


def setup_database(dbname, driver=None, pooling=False):
    if dbname == "sqlite":
        db = web.database(dbn=dbname, db="webpy.db", pooling=pooling, driver=driver)
    elif dbname == "postgres":
        user = os.getenv("USER")
        db = web.database(
            dbn=dbname, db="webpy", user=user, pw="", pooling=pooling, driver=driver
        )
    else:
        db = web.database(
            dbn=dbname,
            db="webpy",
            user="scott",
            pw="tiger",
            pooling=pooling,
            driver=driver,
        )

    db.printing = True
    return db


class DBTest(unittest.TestCase):
    dbname = "postgres"
    driver = None

    def setUp(self):
        self.db = setup_database(self.dbname, driver=self.driver)
        self.db.query("DROP TABLE IF EXISTS person")
        self.db.query("CREATE TABLE person (name text, email text, active boolean)")

    def tearDown(self):
        self.db.query("DROP TABLE IF EXISTS person")
        self.db.query("DROP TABLE IF EXISTS mi")
        self.db.ctx.db.close()

    def _testable(self):
        try:
            setup_database(self.dbname, driver=self.driver)
            print("Running tests for %s" % self.__class__.__name__, file=web.debug)
            return True
        except ImportError as e:
            print(str(e), "(ignoring %s)" % self.__class__.__name__, file=web.debug)
            return False

    def testUnicode(self):
        # Bug#177265: unicode queries throw errors
        self.db.select("person", where="name=$name", vars={"name": u"\xf4"})

    def assertRows(self, n):
        result = self.db.select("person")
        self.assertEqual(len(list(result)), n)

    def testCommit(self):
        t = self.db.transaction()
        self.db.insert("person", False, name="user1")
        t.commit()

        t = self.db.transaction()
        self.db.insert("person", False, name="user2")
        self.db.insert("person", False, name="user3")
        t.commit()

        self.assertRows(3)

    def testRollback(self):
        t = self.db.transaction()
        self.db.insert("person", False, name="user1")
        self.db.insert("person", False, name="user2")
        self.db.insert("person", False, name="user3")
        t.rollback()
        self.assertRows(0)

    def testWrongQuery(self):
        # It should be possible to run a correct query after getting an error from a wrong query.
        try:
            self.db.select("notthere")
        except:
            pass
        self.db.select("person")

    def testNestedTransactions(self):
        t1 = self.db.transaction()
        self.db.insert("person", False, name="user1")
        self.assertRows(1)

        t2 = self.db.transaction()
        self.db.insert("person", False, name="user2")
        self.assertRows(2)
        t2.rollback()
        self.assertRows(1)
        t3 = self.db.transaction()
        self.db.insert("person", False, name="user3")
        self.assertRows(2)
        t3.commit()
        t1.commit()
        self.assertRows(2)

    def testPooling(self):
        # can't test pooling if DBUtils is not installed
        try:
            import DBUtils  # noqa
        except ImportError:
            return
        db = setup_database(self.dbname, pooling=True)
        try:
            self.assertEqual(db.ctx.db.__class__.__module__, "DBUtils.PooledDB")
            db.select("person", limit=1)
        finally:
            db.ctx.db.close()

    def test_multiple_insert(self):
        db = self.db
        db.multiple_insert("person", [dict(name="a"), dict(name="b")], seqname=False)

        assert db.select("person", where="name='a'").list()
        assert db.select("person", where="name='b'").list()

        # Create table `mi`
        if self.driver in web.db.pg_drivers:
            db.query("CREATE TABLE mi (id SERIAL PRIMARY KEY, v VARCHAR(5))")
        elif self.driver in web.db.mysql_drivers:
            self.db.query(
                "CREATE TABLE mi (id INT(10) UNSIGNED AUTO_INCREMENT, v VARCHAR(5), PRIMARY KEY (`id`))"
            )
        elif self.driver in web.db.sqlite_drivers:
            self.db.query(
                "CREATE TABLE mi (id INTEGER PRIMARY KEY NOT NULL, v VARCHAR(5))"
            )

        # Insert rows and verify returned row id.
        if (
            self.driver
            in web.db.pg_drivers + web.db.mysql_drivers + web.db.sqlite_drivers
        ):
            values = [{"v": "a"}, {"v": "b"}, {"v": "c"}]

            ids = db.multiple_insert("mi", values)
            # `psycopg2` returns `range(1, 4)` instead of `[1, 2, 3]` on Python-3.
            assert list(ids) == [1, 2, 3]

            ids = db.multiple_insert("mi", values)
            assert list(ids) == [4, 5, 6]

    def test_result_is_unicode(self):
        # TODO : not sure this test has still meaning with Py3
        self.db.insert("person", False, name="user")
        name = self.db.select("person")[0].name
        self.assertEqual(type(name), unicode)

    def test_result_is_true(self):
        self.db.insert("person", False, name="user")
        self.assertEqual(bool(self.db.select("person")), True)

    def testBoolean(self):
        def t(active):
            name = "name-%s" % active
            self.db.insert("person", False, name=name, active=active)
            a = self.db.select("person", where="name=$name", vars=locals())[0].active
            self.assertEqual(a, active)

        t(False)
        t(True)

    def test_insert_default_values(self):
        self.db.insert("person")

    def test_where(self):
        self.db.insert("person", False, name="Foo")
        d = self.db.where("person", name="Foo").list()
        assert len(d) == 1
        d = self.db.where("person").list()
        assert len(d) == 1


@requires_module("psycopg2")
class PostgresTest2(DBTest):
    dbname = "postgres"
    driver = "psycopg2"

    def test_limit_with_unsafe_value(self):
        db = self.db
        db.insert("person", False, name="Foo")
        assert len(db.select("person").list()) == 1

        try:
            db.select("person", limit="1; DELETE FROM person;")
        except db.db_module.Error:
            # It is alright if the db engine rejects this query
            pass

        assert len(db.select("person").list()) == 1

    def test_offset_with_unsafe_value(self):
        db = self.db
        db.insert("person", False, name="Foo")
        assert len(db.select("person").list()) == 1

        try:
            db.select("person", offset="1; DELETE FROM person;")
        except db.db_module.Error:
            # It is alright if the db engine rejects this query
            pass

        assert len(db.select("person").list()) == 1


@requires_module("psycopg")
class PostgresTest_psycopg(PostgresTest2):
    driver = "psycopg"


@requires_module("pgdb")
class PostgresTest_pgdb(PostgresTest2):
    driver = "pgdb"


@requires_module("sqlite3")
class SqliteTest(DBTest):
    dbname = "sqlite"
    driver = "sqlite3"

    def testNestedTransactions(self):
        # nested transactions does not work with sqlite
        pass

    def testPooling(self):
        # pooling is not support for sqlite
        pass


@requires_module("pysqlite2.dbapi2")
class SqliteTest_pysqlite2(SqliteTest):
    driver = "pysqlite2.dbapi2"


@requires_module("MySQLdb")
class MySQLTest_MySQLdb(DBTest):
    dbname = "mysql"
    driver = "MySQLdb"

    def setUp(self):
        self.db = setup_database(self.dbname)
        # In mysql, transactions are supported only with INNODB engine.
        self.db.query("CREATE TABLE person (name text, email text) ENGINE=INNODB")

    def testBoolean(self):
        # boolean datatype is not suppoted in MySQL (at least until v5.0)
        pass


@requires_module("pymysql")
class MySQLTest_PyMySQL(MySQLTest_MySQLdb):
    driver = "pymysql"


@requires_module("mysql.connector")
class MySQLTest_MySQLConnector(MySQLTest_MySQLdb):
    driver = "mysql.connector"


del DBTest
