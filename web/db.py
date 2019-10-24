"""
Database API
(part of web.py)
"""
from __future__ import print_function

import datetime
import os
import re
import time

from .py3helpers import PY2, iteritems, numeric_types, string_types, text_type
from .utils import iters, safestr, safeunicode, storage, threadeddict

try:
    from urllib import parse as urlparse
    from urllib.parse import unquote
except ImportError:
    import urlparse
    from urllib import unquote

try:
    import ast
except ImportError:
    ast = None

try:
    # db module can work independent of web.py
    from .webapi import debug, config
except ImportError:
    import sys

    debug = sys.stderr
    config = storage()

__all__ = [
    "UnknownParamstyle",
    "UnknownDB",
    "TransactionError",
    "sqllist",
    "sqlors",
    "reparam",
    "sqlquote",
    "SQLQuery",
    "SQLParam",
    "sqlparam",
    "SQLLiteral",
    "sqlliteral",
    "database",
    "DB",
]

TOKEN = "[ \\f\\t]*(\\\\\\r?\\n[ \\f\\t]*)*(#[^\\r\\n]*)?(((\\d+[jJ]|((\\d+\\.\\d*|\\.\\d+)([eE][-+]?\\d+)?|\\d+[eE][-+]?\\d+)[jJ])|((\\d+\\.\\d*|\\.\\d+)([eE][-+]?\\d+)?|\\d+[eE][-+]?\\d+)|(0[xX][\\da-fA-F]+[lL]?|0[bB][01]+[lL]?|(0[oO][0-7]+)|(0[0-7]*)[lL]?|[1-9]\\d*[lL]?))|((\\*\\*=?|>>=?|<<=?|<>|!=|//=?|[+\\-*/%&|^=<>]=?|~)|[][(){}]|(\\r?\\n|[:;.,`@]))|([uUbB]?[rR]?'[^\\n'\\\\]*(?:\\\\.[^\\n'\\\\]*)*'|[uUbB]?[rR]?\"[^\\n\"\\\\]*(?:\\\\.[^\\n\"\\\\]*)*\")|[a-zA-Z_]\\w*)"

tokenprog = re.compile(TOKEN)

# Supported db drivers.
pg_drivers = ["psycopg2", "psycopg", "pgdb"]
mysql_drivers = ["MySQLdb", "pymysql", "mysql.connector"]
sqlite_drivers = ["sqlite3", "pysqlite2.dbapi2", "sqlite"]


class UnknownDB(Exception):
    """raised for unsupported dbms"""

    pass


class _ItplError(ValueError):
    def __init__(self, text, pos):
        ValueError.__init__(self)
        self.text = text
        self.pos = pos

    def __str__(self):
        return "unfinished expression in %s at char %d" % (repr(self.text), self.pos)


class TransactionError(Exception):
    pass


class UnknownParamstyle(Exception):
    """
    raised for unsupported db paramstyles

    (currently supported: qmark, numeric, format, pyformat)
    """

    pass


class SQLParam(object):
    """
    Parameter in SQLQuery.

        >>> q = SQLQuery(["SELECT * FROM test WHERE name=", SQLParam("joe")])
        >>> q
        <sql: "SELECT * FROM test WHERE name='joe'">
        >>> q.query()
        'SELECT * FROM test WHERE name=%s'
        >>> q.values()
        ['joe']
    """

    __slots__ = ["value"]

    def __init__(self, value):
        self.value = value

    def get_marker(self, paramstyle="pyformat"):
        if paramstyle == "qmark":
            return "?"
        elif paramstyle == "numeric":
            return ":1"
        elif paramstyle is None or paramstyle in ["format", "pyformat"]:
            return "%s"
        raise UnknownParamstyle(paramstyle)

    def sqlquery(self):
        return SQLQuery([self])

    def __add__(self, other):
        return self.sqlquery() + other

    def __radd__(self, other):
        return other + self.sqlquery()

    def __str__(self):
        return str(self.value)

    def __eq__(self, other):
        return isinstance(other, SQLParam) and other.value == self.value

    def __repr__(self):
        return "<param: %s>" % repr(self.value)


sqlparam = SQLParam


class SQLQuery(object):
    """
    You can pass this sort of thing as a clause in any db function.
    Otherwise, you can pass a dictionary to the keyword argument `vars`
    and the function will call reparam for you.

    Internally, consists of `items`, which is a list of strings and
    SQLParams, which get concatenated to produce the actual query.
    """

    __slots__ = ["items"]

    # tested in sqlquote's docstring
    def __init__(self, items=None):
        r"""Creates a new SQLQuery.

            >>> SQLQuery("x")
            <sql: 'x'>
            >>> q = SQLQuery(['SELECT * FROM ', 'test', ' WHERE x=', SQLParam(1)])
            >>> q
            <sql: 'SELECT * FROM test WHERE x=1'>
            >>> q.query(), q.values()
            ('SELECT * FROM test WHERE x=%s', [1])
            >>> SQLQuery(SQLParam(1))
            <sql: '1'>
        """
        if items is None:
            self.items = []
        elif isinstance(items, list):
            self.items = items
        elif isinstance(items, SQLParam):
            self.items = [items]
        elif isinstance(items, SQLQuery):
            self.items = list(items.items)
        else:
            self.items = [items]

        # Take care of SQLLiterals
        for i, item in enumerate(self.items):
            if isinstance(item, SQLParam) and isinstance(item.value, SQLLiteral):
                self.items[i] = item.value.v

    def append(self, value):
        self.items.append(value)

    def __add__(self, other):
        if isinstance(other, string_types):
            items = [other]
        elif isinstance(other, SQLQuery):
            items = other.items
        else:
            return NotImplemented
        return SQLQuery(self.items + items)

    def __radd__(self, other):
        if isinstance(other, string_types):
            items = [other]
        elif isinstance(other, SQLQuery):
            items = other.items
        else:
            return NotImplemented
        return SQLQuery(items + self.items)

    def __iadd__(self, other):
        if isinstance(other, (string_types, SQLParam)):
            self.items.append(other)
        elif isinstance(other, SQLQuery):
            self.items.extend(other.items)
        else:
            return NotImplemented
        return self

    def __len__(self):
        return len(self.query())

    def __eq__(self, other):
        return isinstance(other, SQLQuery) and other.items == self.items

    def query(self, paramstyle=None):
        """
        Returns the query part of the sql query.
            >>> q = SQLQuery(["SELECT * FROM test WHERE name=", SQLParam('joe')])
            >>> q.query()
            'SELECT * FROM test WHERE name=%s'
            >>> q.query(paramstyle='qmark')
            'SELECT * FROM test WHERE name=?'
        """
        s = []
        for x in self.items:
            if isinstance(x, SQLParam):
                x = x.get_marker(paramstyle)
                s.append(safestr(x))
            else:
                x = safestr(x)
                # automatically escape % characters in the query
                # For backward compatability, ignore escaping when the query
                # looks already escaped
                if paramstyle in ["format", "pyformat"]:
                    if "%" in x and "%%" not in x:
                        x = x.replace("%", "%%")
                s.append(x)
        return "".join(s)

    def values(self):
        """
        Returns the values of the parameters used in the sql query.
            >>> q = SQLQuery(["SELECT * FROM test WHERE name=", SQLParam('joe')])
            >>> q.values()
            ['joe']
        """
        return [i.value for i in self.items if isinstance(i, SQLParam)]

    def join(items, sep=" ", prefix=None, suffix=None, target=None):
        """
        Joins multiple queries.

        >>> SQLQuery.join(['a', 'b'], ', ')
        <sql: 'a, b'>

        Optinally, prefix and suffix arguments can be provided.

        >>> SQLQuery.join(['a', 'b'], ', ', prefix='(', suffix=')')
        <sql: '(a, b)'>

        If target argument is provided, the items are appended to target
        instead of creating a new SQLQuery.
        """
        if target is None:
            target = SQLQuery()

        target_items = target.items

        if prefix:
            target_items.append(prefix)

        for i, item in enumerate(items):
            if i != 0 and sep != "":
                target_items.append(sep)
            if isinstance(item, SQLQuery):
                target_items.extend(item.items)
            elif item == "":  # joins with empty strings
                continue
            else:
                target_items.append(item)

        if suffix:
            target_items.append(suffix)
        return target

    join = staticmethod(join)

    def _str(self):
        try:
            return self.query() % tuple([sqlify(x) for x in self.values()])
        except (ValueError, TypeError):
            return self.query()

    def __str__(self):
        return safestr(self._str())

    def __unicode__(self):
        return safeunicode(self._str())

    def __repr__(self):
        return "<sql: %s>" % repr(str(self))


class SQLLiteral:
    """
    Protects a string from `sqlquote`.

        >>> sqlquote('NOW()')
        <sql: "'NOW()'">
        >>> sqlquote(SQLLiteral('NOW()'))
        <sql: 'NOW()'>
    """

    def __init__(self, v):
        self.v = v

    def __repr__(self):
        return "<literal: %r>" % self.v


sqlliteral = SQLLiteral


def _sqllist(values):
    """
        >>> _sqllist([1, 2, 3])
        <sql: '(1, 2, 3)'>
        >>> _sqllist(set([5, 1, 3, 2]))
        <sql: '(1, 2, 3, 5)'>
        >>> _sqllist((5, 1, 3, 2, 2, 5))
        <sql: '(1, 2, 3, 5)'>
    """
    items = []
    items.append("(")

    if isinstance(values, set):
        values = list(values)
    elif isinstance(values, tuple):
        values = list(set(values))

    for i, v in enumerate(values):
        if i != 0:
            items.append(", ")
        items.append(sqlparam(v))
    items.append(")")
    return SQLQuery(items)


def reparam(string_, dictionary):
    """
    Takes a string and a dictionary and interpolates the string
    using values from the dictionary. Returns an `SQLQuery` for the result.

        >>> reparam("s = $s", dict(s=True))
        <sql: "s = 't'">
        >>> reparam("s IN $s", dict(s=[1, 2]))
        <sql: 's IN (1, 2)'>
    """
    return SafeEval().safeeval(string_, dictionary)

    dictionary = dictionary.copy()  # eval mucks with it
    # disable builtins to avoid risk for remote code exection.
    dictionary["__builtins__"] = object()
    result = []
    for live, chunk in _interpolate(string_):
        if live:
            v = eval(chunk, dictionary)
            result.append(sqlquote(v))
        else:
            result.append(chunk)
    return SQLQuery.join(result, "")


def sqlify(obj):
    """
    converts `obj` to its proper SQL version

        >>> sqlify(None)
        'NULL'
        >>> sqlify(True)
        "'t'"
        >>> sqlify(3)
        '3'
    """
    # because `1 == True and hash(1) == hash(True)`
    # we have to do this the hard way...

    if obj is None:
        return "NULL"
    elif obj is True:
        return "'t'"
    elif obj is False:
        return "'f'"
    elif isinstance(obj, numeric_types):
        return str(obj)
    elif isinstance(obj, datetime.datetime):
        return repr(obj.isoformat())
    else:
        if PY2 and isinstance(obj, text_type):  # Strings are always UTF8 in Py3
            obj = obj.encode("utf8")

        return repr(obj)


def sqllist(lst):
    """
    Converts the arguments for use in something like a WHERE clause.

        >>> sqllist(['a', 'b'])
        'a, b'
        >>> sqllist('a')
        'a'
    """
    if isinstance(lst, string_types):
        return lst
    else:
        return ", ".join(lst)


def sqlors(left, lst):
    """
    `left is a SQL clause like `tablename.arg = `
    and `lst` is a list of values. Returns a reparam-style
    pair featuring the SQL that ORs together the clause
    for each item in the lst.

        >>> sqlors('foo = ', [])
        <sql: '1=2'>
        >>> sqlors('foo = ', [1])
        <sql: 'foo = 1'>
        >>> sqlors('foo = ', 1)
        <sql: 'foo = 1'>
        >>> sqlors('foo = ', [1,2,3])
        <sql: '(foo = 1 OR foo = 2 OR foo = 3 OR 1=2)'>
    """
    if isinstance(lst, iters):
        lst = list(lst)
        ln = len(lst)
        if ln == 0:
            return SQLQuery("1=2")
        if ln == 1:
            lst = lst[0]

    if isinstance(lst, iters):
        return SQLQuery(
            ["("] + sum([[left, sqlparam(x), " OR "] for x in lst], []) + ["1=2)"]
        )
    else:
        return left + sqlparam(lst)


def sqlwhere(data, grouping=" AND "):
    """
    Converts a two-tuple (key, value) iterable `data` to an SQL WHERE clause
    `SQLQuery`.

        >>> sqlwhere((('cust_id', 2), ('order_id',3)))
        <sql: 'cust_id = 2 AND order_id = 3'>
        >>> sqlwhere((('order_id', 3), ('cust_id', 2)), grouping=', ')
        <sql: 'order_id = 3, cust_id = 2'>
        >>> sqlwhere((('a', 'a'), ('b', 'b'))).query()
        'a = %s AND b = %s'
    """

    return SQLQuery.join([k + " = " + sqlparam(v) for k, v in data], grouping)


def sqlquote(a):
    """
    Ensures `a` is quoted properly for use in a SQL query.

        >>> 'WHERE x = ' + sqlquote(True) + ' AND y = ' + sqlquote(3)
        <sql: "WHERE x = 't' AND y = 3">
        >>> 'WHERE x = ' + sqlquote(True) + ' AND y IN ' + sqlquote([2, 3])
        <sql: "WHERE x = 't' AND y IN (2, 3)">
        >>> 'WHERE x = ' + sqlquote(True) + ' AND y IN ' + sqlquote(set([3, 2, 3, 4]))
        <sql: "WHERE x = 't' AND y IN (2, 3, 4)">
        >>> 'WHERE x = ' + sqlquote(True) + ' AND y IN ' + sqlquote((3, 2, 3, 4))
        <sql: "WHERE x = 't' AND y IN (2, 3, 4)">
    """
    if isinstance(a, (list, tuple, set)):
        return _sqllist(a)
    else:
        return sqlparam(a).sqlquery()


class BaseResultSet:
    """Base implementation of Result Set, the result of a db query.
    """

    def __init__(self, cursor):
        self.cursor = cursor
        self.names = [x[0] for x in cursor.description]
        self._index = 0

    def list(self):
        rows = [self._prepare_row(d) for d in self.cursor.fetchall()]
        self._index += len(rows)
        return rows

    def _prepare_row(self, row):
        return storage(dict(zip(self.names, row)))

    def __iter__(self):
        return self

    def __next__(self):
        row = self.cursor.fetchone()
        if row is None:
            raise StopIteration()
        self._index += 1
        return self._prepare_row(row)

    next = __next__  # for python 2.7 support

    def first(self, default=None):
        """Returns the first row of this ResultSet or None when there are no
        elements.

        If the optional argument default is specified, that is returned instead
        of None when there are no elements.
        """
        try:
            return next(iter(self))
        except StopIteration:
            return default

    def __getitem__(self, i):
        # todo: slices
        if i < self._index:
            raise IndexError("already passed " + str(i))
        try:
            while i > self._index:
                next(self)
                self._index += 1
            # now self._index == i
            self._index += 1
            return next(self)
        except StopIteration:
            raise IndexError(str(i))


class ResultSet(BaseResultSet):
    """The result of a database query.
    """

    def __len__(self):
        return int(self.cursor.rowcount)


class SqliteResultSet(BaseResultSet):
    """Result Set for sqlite.

    Same functionaly as ResultSet except len is not supported.
    """

    def __init__(self, cursor):
        BaseResultSet.__init__(self, cursor)
        self._head = None

    def __next__(self):
        if self._head is not None:
            self._index += 1
            return self._head
        else:
            return super().__next__()

    def __bool__(self):
        # The ResultSet class class doesn't need to support __bool__ explicity
        # because it has __len__. Since SqliteResultSet doesn't support len,
        # we need to peep into the result to find if the result is empty of not.
        if self._head is None:
            try:
                self._head = next(self)
                self._index -= 1  # reset the index
            except StopIteration:
                return False
        return True


class Transaction:
    """Database transaction."""

    def __init__(self, ctx):
        self.ctx = ctx
        self.transaction_count = transaction_count = len(ctx.transactions)

        class transaction_engine:
            """Transaction Engine used in top level transactions."""

            def do_transact(self):
                ctx.commit(unload=False)

            def do_commit(self):
                ctx.commit()

            def do_rollback(self):
                ctx.rollback()

        class subtransaction_engine:
            """Transaction Engine used in sub transactions."""

            def query(self, q):
                db_cursor = ctx.db.cursor()
                ctx.db_execute(db_cursor, SQLQuery(q % transaction_count))

            def do_transact(self):
                self.query("SAVEPOINT webpy_sp_%s")

            def do_commit(self):
                self.query("RELEASE SAVEPOINT webpy_sp_%s")

            def do_rollback(self):
                self.query("ROLLBACK TO SAVEPOINT webpy_sp_%s")

        class dummy_engine:
            """Transaction Engine used instead of subtransaction_engine
            when sub transactions are not supported."""

            do_transact = do_commit = do_rollback = lambda self: None

        if self.transaction_count:
            # nested transactions are not supported in some databases
            if self.ctx.get("ignore_nested_transactions"):
                self.engine = dummy_engine()
            else:
                self.engine = subtransaction_engine()
        else:
            self.engine = transaction_engine()

        self.engine.do_transact()
        self.ctx.transactions.append(self)

    def __enter__(self):
        return self

    def __exit__(self, exctype, excvalue, traceback):
        if exctype is not None:
            self.rollback()
        else:
            self.commit()

    def commit(self):
        if len(self.ctx.transactions) > self.transaction_count:
            self.engine.do_commit()
            self.ctx.transactions = self.ctx.transactions[: self.transaction_count]

    def rollback(self):
        if len(self.ctx.transactions) > self.transaction_count:
            self.engine.do_rollback()
            self.ctx.transactions = self.ctx.transactions[: self.transaction_count]


class DB:
    """Database"""

    def __init__(self, db_module, keywords):
        """Creates a database.
        """
        # some DB implementaions take optional paramater `driver` to use a
        # specific driver modue but it should not be passed to `connect`.
        keywords.pop("driver", None)

        self.db_module = db_module
        self.keywords = keywords

        self._ctx = threadeddict()
        # flag to enable/disable printing queries
        self.printing = config.get("debug_sql", config.get("debug", False))
        self.supports_multiple_insert = False

        try:
            import DBUtils  # noqa, flake8 F401

            # enable pooling if DBUtils module is available.
            self.has_pooling = True
        except ImportError:
            self.has_pooling = False

        # Pooling can be disabled by passing pooling=False in the keywords.
        self.has_pooling = self.keywords.pop("pooling", True) and self.has_pooling

    def _getctx(self):
        if not self._ctx.get("db"):
            self._load_context(self._ctx)
        return self._ctx

    ctx = property(_getctx)

    def _load_context(self, ctx):
        ctx.dbq_count = 0
        ctx.transactions = []  # stack of transactions

        if self.has_pooling:
            ctx.db = self._connect_with_pooling(self.keywords)
        else:
            ctx.db = self._connect(self.keywords)
        ctx.db_execute = self._db_execute

        if not hasattr(ctx.db, "commit"):
            ctx.db.commit = lambda: None

        if not hasattr(ctx.db, "rollback"):
            ctx.db.rollback = lambda: None

        def commit(unload=True):
            # do db commit and release the connection if pooling is enabled.
            ctx.db.commit()
            if unload and self.has_pooling:
                self._unload_context(self._ctx)

        def rollback():
            # do db rollback and release the connection if pooling is enabled.
            ctx.db.rollback()
            if self.has_pooling:
                self._unload_context(self._ctx)

        ctx.commit = commit
        ctx.rollback = rollback

    def _unload_context(self, ctx):
        del ctx.db

    def _connect(self, keywords):
        return self.db_module.connect(**keywords)

    def _connect_with_pooling(self, keywords):
        def get_pooled_db():
            from DBUtils import PooledDB

            # In DBUtils 0.9.3, `dbapi` argument is renamed as `creator`
            # see Bug#122112

            if PooledDB.__version__.split(".") < "0.9.3".split("."):
                return PooledDB.PooledDB(dbapi=self.db_module, **keywords)
            else:
                return PooledDB.PooledDB(creator=self.db_module, **keywords)

        if getattr(self, "_pooleddb", None) is None:
            self._pooleddb = get_pooled_db()

        return self._pooleddb.connection()

    def _db_cursor(self):
        return self.ctx.db.cursor()

    def _param_marker(self):
        """Returns parameter marker based on paramstyle attribute if this database."""
        style = getattr(self, "paramstyle", "pyformat")

        if style == "qmark":
            return "?"
        elif style == "numeric":
            return ":1"
        elif style in ["format", "pyformat"]:
            return "%s"
        raise UnknownParamstyle(style)

    def _db_execute(self, cur, sql_query):
        """executes an sql query"""
        self.ctx.dbq_count += 1

        try:
            a = time.time()
            query, params = self._process_query(sql_query)
            out = cur.execute(query, params)
            b = time.time()
        except:
            if self.printing:
                print("ERR:", str(sql_query), file=debug)
            if self.ctx.transactions:
                self.ctx.transactions[-1].rollback()
            else:
                self.ctx.rollback()
            raise

        if self.printing:
            print(
                "%s (%s): %s" % (round(b - a, 2), self.ctx.dbq_count, str(sql_query)),
                file=debug,
            )
        return out

    def _process_query(self, sql_query):
        """Takes the SQLQuery object and returns query string and parameters.
        """
        paramstyle = getattr(self, "paramstyle", "pyformat")
        query = sql_query.query(paramstyle)
        params = sql_query.values()
        return query, params

    def _where(self, where, vars):
        if isinstance(where, numeric_types):
            where = "id = " + sqlparam(where)
        # @@@ for backward-compatibility
        elif isinstance(where, (list, tuple)) and len(where) == 2:
            where = SQLQuery(where[0], where[1])
        elif isinstance(where, dict):
            where = self._where_dict(where)
        elif isinstance(where, SQLQuery):
            pass
        else:
            where = reparam(where, vars)
        return where

    def _where_dict(self, where):
        where_clauses = []

        for k, v in sorted(iteritems(where), key=lambda t: t[0]):
            where_clauses.append(k + " = " + sqlquote(v))
        if where_clauses:
            return SQLQuery.join(where_clauses, " AND ")
        else:
            return None

    def query(self, sql_query, vars=None, processed=False, _test=False):
        """
        Execute SQL query `sql_query` using dictionary `vars` to interpolate it.
        If `processed=True`, `vars` is a `reparam`-style list to use
        instead of interpolating.

            >>> db = DB(None, {})
            >>> db.query("SELECT * FROM foo", _test=True)
            <sql: 'SELECT * FROM foo'>
            >>> db.query("SELECT * FROM foo WHERE x = $x", vars=dict(x='f'), _test=True)
            <sql: "SELECT * FROM foo WHERE x = 'f'">
            >>> db.query("SELECT * FROM foo WHERE x = " + sqlquote('f'), _test=True)
            <sql: "SELECT * FROM foo WHERE x = 'f'">
        """
        if vars is None:
            vars = {}

        if not processed and not isinstance(sql_query, SQLQuery):
            sql_query = reparam(sql_query, vars)

        if _test:
            return sql_query

        db_cursor = self._db_cursor()
        self._db_execute(db_cursor, sql_query)

        if db_cursor.description:
            return self.create_result_set(db_cursor)
        else:
            out = db_cursor.rowcount

        if not self.ctx.transactions:
            self.ctx.commit()
        return out

    def create_result_set(self, cursor):
        return ResultSet(cursor)

    def select(
        self,
        tables,
        vars=None,
        what="*",
        where=None,
        order=None,
        group=None,
        limit=None,
        offset=None,
        _test=False,
    ):
        """
        Selects `what` from `tables` with clauses `where`, `order`,
        `group`, `limit`, and `offset`. Uses vars to interpolate.
        Otherwise, each clause can be a SQLQuery.

            >>> db = DB(None, {})
            >>> db.select('foo', _test=True)
            <sql: 'SELECT * FROM foo'>
            >>> db.select(['foo', 'bar'], where="foo.bar_id = bar.id", limit=5, _test=True)
            <sql: 'SELECT * FROM foo, bar WHERE foo.bar_id = bar.id LIMIT 5'>
            >>> db.select('foo', where={'id': 5}, _test=True)
            <sql: 'SELECT * FROM foo WHERE id = 5'>
        """
        if vars is None:
            vars = {}

        sql_clauses = self.sql_clauses(what, tables, where, group, order, limit, offset)
        clauses = [
            self.gen_clause(sql, val, vars)
            for sql, val in sql_clauses
            if val is not None
        ]
        qout = SQLQuery.join(clauses)

        if _test:
            return qout

        return self.query(qout, processed=True)

    def where(
        self,
        table,
        what="*",
        order=None,
        group=None,
        limit=None,
        offset=None,
        _test=False,
        **kwargs
    ):
        """
        Selects from `table` where keys are equal to values in `kwargs`.

            >>> db = DB(None, {})
            >>> db.where('foo', bar_id=3, _test=True)
            <sql: 'SELECT * FROM foo WHERE bar_id = 3'>
            >>> db.where('foo', source=2, crust='dewey', _test=True)
            <sql: "SELECT * FROM foo WHERE crust = 'dewey' AND source = 2">
            >>> db.where('foo', _test=True)
            <sql: 'SELECT * FROM foo'>
        """
        where = self._where_dict(kwargs)
        return self.select(
            table,
            what=what,
            order=order,
            group=group,
            limit=limit,
            offset=offset,
            _test=_test,
            where=where,
        )

    def sql_clauses(self, what, tables, where, group, order, limit, offset):
        return (
            ("SELECT", what),
            ("FROM", sqllist(tables)),
            ("WHERE", where),
            ("GROUP BY", group),
            ("ORDER BY", order),
            # The limit and offset could be the values provided by
            # the end-user and are potentially unsafe.
            # Using them as parameters to avoid any risk.
            ("LIMIT", limit and SQLParam(limit).sqlquery()),
            ("OFFSET", offset and SQLParam(offset).sqlquery()),
        )

    def gen_clause(self, sql, val, vars):
        if isinstance(val, numeric_types):
            if sql == "WHERE":
                nout = "id = " + sqlquote(val)
            else:
                nout = SQLQuery(val)
        # @@@
        elif isinstance(val, (list, tuple)) and len(val) == 2:
            nout = SQLQuery(val[0], val[1])  # backwards-compatibility
        elif sql == "WHERE" and isinstance(val, dict):
            nout = self._where_dict(val)
        elif isinstance(val, SQLQuery):
            nout = val
        else:
            nout = reparam(val, vars)

        def xjoin(a, b):
            if a and b:
                return a + " " + b
            else:
                return a or b

        return xjoin(sql, nout)

    def insert(self, tablename, seqname=None, _test=False, **values):
        """
        Inserts `values` into `tablename`. Returns current sequence ID.
        Set `seqname` to the ID if it's not the default, or to `False`
        if there isn't one.

            >>> db = DB(None, {})
            >>> q = db.insert('foo', name='bob', age=2, created=SQLLiteral('NOW()'), _test=True)
            >>> q
            <sql: "INSERT INTO foo (age, created, name) VALUES (2, NOW(), 'bob')">
            >>> q.query()
            'INSERT INTO foo (age, created, name) VALUES (%s, NOW(), %s)'
            >>> q.values()
            [2, 'bob']
        """

        def q(x):
            return "(" + x + ")"

        if values:
            # needed for Py3 compatibility with the above doctests
            sorted_values = sorted(values.items(), key=lambda t: t[0])

            _keys = SQLQuery.join(map(lambda t: t[0], sorted_values), ", ")
            _values = SQLQuery.join(
                [sqlparam(v) for v in map(lambda t: t[1], sorted_values)], ", "
            )
            sql_query = (
                "INSERT INTO %s " % tablename + q(_keys) + " VALUES " + q(_values)
            )
        else:
            sql_query = SQLQuery(self._get_insert_default_values_query(tablename))

        if _test:
            return sql_query

        db_cursor = self._db_cursor()
        if seqname is not False:
            sql_query = self._process_insert_query(sql_query, tablename, seqname)

        if isinstance(sql_query, tuple):
            # for some databases, a separate query has to be made to find
            # the id of the inserted row.
            q1, q2 = sql_query
            self._db_execute(db_cursor, q1)
            self._db_execute(db_cursor, q2)
        else:
            self._db_execute(db_cursor, sql_query)

        try:
            out = db_cursor.fetchone()[0]
        except Exception:
            out = None

        if not self.ctx.transactions:
            self.ctx.commit()

        return out

    def _get_insert_default_values_query(self, table):
        return "INSERT INTO %s DEFAULT VALUES" % table

    def multiple_insert(self, tablename, values, seqname=None, _test=False):
        """
        Inserts multiple rows into `tablename`. The `values` must be a list of
        dictionaries, one for each row to be inserted, each with the same set
        of keys. Returns the list of ids of the inserted rows.
        Set `seqname` to the ID if it's not the default, or to `False`
        if there isn't one.

            >>> db = DB(None, {})
            >>> db.supports_multiple_insert = True
            >>> values = [{"name": "foo", "email": "foo@example.com"}, {"name": "bar", "email": "bar@example.com"}]
            >>> db.multiple_insert('person', values=values, _test=True)
            <sql: "INSERT INTO person (email, name) VALUES ('foo@example.com', 'foo'), ('bar@example.com', 'bar')">
        """
        if not values:
            return []

        if not self.supports_multiple_insert:
            out = [
                self.insert(tablename, seqname=seqname, _test=_test, **v)
                for v in values
            ]
            if seqname is False:
                return None
            else:
                return out

        keys = values[0].keys()
        # @@ make sure all keys are valid

        for v in values:
            if v.keys() != keys:
                raise ValueError("Not all rows have the same keys")

        # enforce query order for the above doctest compatibility with Py3
        keys = sorted(keys)

        sql_query = SQLQuery(
            "INSERT INTO %s (%s) VALUES " % (tablename, ", ".join(keys))
        )

        for i, row in enumerate(values):
            if i != 0:
                sql_query.append(", ")
            SQLQuery.join(
                [SQLParam(row[k]) for k in keys],
                sep=", ",
                target=sql_query,
                prefix="(",
                suffix=")",
            )

        if _test:
            return sql_query

        db_cursor = self._db_cursor()
        if seqname is not False:
            sql_query = self._process_insert_query(sql_query, tablename, seqname)

        if isinstance(sql_query, tuple):
            # for some databases, a separate query has to be made to find
            # the id of the inserted row.
            q1, q2 = sql_query
            self._db_execute(db_cursor, q1)
            self._db_execute(db_cursor, q2)
        else:
            self._db_execute(db_cursor, sql_query)

        try:
            out = db_cursor.fetchone()[0]

            # MySQL gives the first id of multiple inserted rows.
            # PostgreSQL and SQLite give the last id.
            if self.db_module.__name__ in mysql_drivers:
                out = range(out, out + len(values))
            else:
                out = range(out - len(values) + 1, out + 1)
        except Exception:
            out = None

        if not self.ctx.transactions:
            self.ctx.commit()
        return out

    def update(self, tables, where, vars=None, _test=False, **values):
        """
        Update `tables` with clause `where` (interpolated using `vars`)
        and setting `values`.

            >>> db = DB(None, {})
            >>> name = 'Joseph'
            >>> q = db.update('foo', where='name = $name', name='bob', age=2,
            ...     created=SQLLiteral('NOW()'), vars=locals(), _test=True)
            >>> q
            <sql: "UPDATE foo SET age = 2, created = NOW(), name = 'bob' WHERE name = 'Joseph'">
            >>> q.query()
            'UPDATE foo SET age = %s, created = NOW(), name = %s WHERE name = %s'
            >>> q.values()
            [2, 'bob', 'Joseph']
        """
        if vars is None:
            vars = {}

        where = self._where(where, vars)
        values = sorted(values.items(), key=lambda t: t[0])

        query = (
            "UPDATE "
            + sqllist(tables)
            + " SET "
            + sqlwhere(values, ", ")
            + " WHERE "
            + where
        )

        if _test:
            return query

        db_cursor = self._db_cursor()
        self._db_execute(db_cursor, query)
        if not self.ctx.transactions:
            self.ctx.commit()
        return db_cursor.rowcount

    def delete(self, table, where, using=None, vars=None, _test=False):
        """
        Deletes from `table` with clauses `where` and `using`.

            >>> db = DB(None, {})
            >>> name = 'Joe'
            >>> db.delete('foo', where='name = $name', vars=locals(), _test=True)
            <sql: "DELETE FROM foo WHERE name = 'Joe'">
        """
        if vars is None:
            vars = {}

        where = self._where(where, vars)

        q = "DELETE FROM " + table
        if using:
            q += " USING " + sqllist(using)

        if where:
            q += " WHERE " + where

        if _test:
            return q

        db_cursor = self._db_cursor()
        self._db_execute(db_cursor, q)
        if not self.ctx.transactions:
            self.ctx.commit()
        return db_cursor.rowcount

    def _process_insert_query(self, query, tablename, seqname):
        return query

    def transaction(self):
        """Start a transaction."""
        return Transaction(self.ctx)


class PostgresDB(DB):
    """Postgres driver."""

    def __init__(self, **keywords):
        if "pw" in keywords:
            keywords["password"] = keywords.pop("pw")

        db_module = import_driver(pg_drivers, preferred=keywords.pop("driver", None))
        if db_module.__name__ == "psycopg2":
            import psycopg2.extensions

            psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)
        if db_module.__name__ == "pgdb" and "port" in keywords:
            keywords["host"] += ":" + str(keywords.pop("port"))

        # if db is not provided `postgres` driver will take it from PGDATABASE
        # environment variable.
        if "db" in keywords:
            keywords["database"] = keywords.pop("db")

        self.dbname = "postgres"
        self.paramstyle = db_module.paramstyle
        DB.__init__(self, db_module, keywords)
        self.supports_multiple_insert = True
        self._sequences = None

    def _process_insert_query(self, query, tablename, seqname):
        if seqname is None:
            # when seqname is not provided guess the seqname and make sure it exists
            seqname = tablename + "_id_seq"
            if seqname not in self._get_all_sequences():
                seqname = None

        if seqname:
            query += "; SELECT currval('%s')" % seqname

        return query

    def _get_all_sequences(self):
        """Query postgres to find names of all sequences used in this database."""
        if self._sequences is None:
            q = "SELECT c.relname FROM pg_class c WHERE c.relkind = 'S'"
            self._sequences = set([c.relname for c in self.query(q)])
        return self._sequences

    def _connect(self, keywords):
        conn = DB._connect(self, keywords)
        try:
            conn.set_client_encoding("UTF8")
        except AttributeError:
            # fallback for pgdb driver
            conn.cursor().execute("set client_encoding to 'UTF-8'")
        return conn

    def _connect_with_pooling(self, keywords):
        conn = DB._connect_with_pooling(self, keywords)
        try:
            conn._con._con.set_client_encoding("UTF8")
        except AttributeError:
            # fallback for pgdb driver
            conn.cursor().execute("set client_encoding to 'UTF-8'")
        return conn


class MySQLDB(DB):
    def __init__(self, **keywords):

        db = import_driver(mysql_drivers, preferred=keywords.pop("driver", None))

        if db.__name__ == "MySQLdb":
            if "pw" in keywords:
                keywords["passwd"] = keywords["pw"]
                del keywords["pw"]
        if db.__name__ == "pymysql":
            if "pw" in keywords:
                keywords["password"] = keywords["pw"]
                del keywords["pw"]
        if db.__name__ == "mysql.connector":
            if "pw" in keywords:
                keywords["password"] = keywords["pw"]
                del keywords["pw"]

        if "charset" not in keywords:
            keywords["charset"] = "utf8"
        elif keywords["charset"] is None:
            del keywords["charset"]

        self.paramstyle = db.paramstyle = "pyformat"  # it's both, like psycopg
        self.dbname = "mysql"
        DB.__init__(self, db, keywords)
        self.supports_multiple_insert = True

    def _process_insert_query(self, query, tablename, seqname):
        return query, SQLQuery("SELECT last_insert_id();")

    def _get_insert_default_values_query(self, table):
        return "INSERT INTO %s () VALUES()" % table


def import_driver(drivers, preferred=None):
    """Import the first available driver or preferred driver.
    """
    if preferred:
        drivers = [preferred]

    for d in drivers:
        try:
            return __import__(d, None, None, ["x"])
        except ImportError:
            pass
    raise ImportError("Unable to import " + " or ".join(drivers))


class SqliteDB(DB):
    def __init__(self, **keywords):
        db = import_driver(sqlite_drivers, preferred=keywords.pop("driver", None))

        if db.__name__ in ["sqlite3", "pysqlite2.dbapi2"]:
            db.paramstyle = "qmark"

        # sqlite driver doesn't create datatime objects for timestamp columns
        # unless `detect_types` option is passed.
        # It seems to be supported in `sqlite3` and `pysqlite2` drivers, not
        # surte about `sqlite`.
        keywords.setdefault("detect_types", db.PARSE_DECLTYPES)

        self.dbname = "sqlite"
        self.paramstyle = db.paramstyle
        keywords["database"] = keywords.pop("db")

        # sqlite don't allows connections to be shared by threads
        keywords["pooling"] = False

        DB.__init__(self, db, keywords)

    def _process_insert_query(self, query, tablename, seqname):
        return query, SQLQuery("SELECT last_insert_rowid();")

    def create_result_set(self, cursor):
        return SqliteResultSet(cursor)


class FirebirdDB(DB):
    """Firebird Database.
    """

    def __init__(self, **keywords):
        try:
            import kinterbasdb as db
        except Exception:
            db = None
            pass
        if "pw" in keywords:
            keywords["password"] = keywords.pop("pw")
        keywords["database"] = keywords.pop("db")

        self.paramstyle = db.paramstyle

        DB.__init__(self, db, keywords)

    def delete(self, table, where=None, using=None, vars=None, _test=False):
        # firebird doesn't support using clause
        using = None
        return DB.delete(self, table, where, using, vars, _test)

    def sql_clauses(self, what, tables, where, group, order, limit, offset):
        return (
            ("SELECT", ""),
            ("FIRST", limit),
            ("SKIP", offset),
            ("", what),
            ("FROM", sqllist(tables)),
            ("WHERE", where),
            ("GROUP BY", group),
            ("ORDER BY", order),
        )


class MSSQLDB(DB):
    def __init__(self, **keywords):
        import pymssql as db

        if "pw" in keywords:
            keywords["password"] = keywords.pop("pw")
        keywords["database"] = keywords.pop("db")
        self.dbname = "mssql"
        DB.__init__(self, db, keywords)

    def _process_query(self, sql_query):
        """Takes the SQLQuery object and returns query string and parameters.
        """
        # MSSQLDB expects params to be a tuple.
        # Overwriting the default implementation to convert params to tuple.
        paramstyle = getattr(self, "paramstyle", "pyformat")
        query = sql_query.query(paramstyle)
        params = sql_query.values()
        return query, tuple(params)

    def sql_clauses(self, what, tables, where, group, order, limit, offset):
        return (
            ("SELECT", what),
            ("TOP", limit),
            ("FROM", sqllist(tables)),
            ("WHERE", where),
            ("GROUP BY", group),
            ("ORDER BY", order),
            ("OFFSET", offset),
        )

    def _test(self):
        """Test LIMIT.

            Fake presence of pymssql module for running tests.
            >>> import sys
            >>> sys.modules['pymssql'] = sys.modules['sys']

            MSSQL has TOP clause instead of LIMIT clause.
            >>> db = MSSQLDB(db='test', user='joe', pw='secret')
            >>> db.select('foo', limit=4, _test=True)
            <sql: 'SELECT * TOP 4 FROM foo'>
        """
        pass


class OracleDB(DB):
    def __init__(self, **keywords):
        import cx_Oracle as db

        if "pw" in keywords:
            keywords["password"] = keywords.pop("pw")

        # @@ TODO: use db.makedsn if host, port is specified
        keywords["dsn"] = keywords.pop("db")
        self.dbname = "oracle"
        db.paramstyle = "numeric"
        self.paramstyle = db.paramstyle

        # oracle doesn't support pooling
        keywords.pop("pooling", None)
        DB.__init__(self, db, keywords)

    def _process_insert_query(self, query, tablename, seqname):
        if seqname is None:
            # It is not possible to get seq name from table name in Oracle
            return query
        else:
            return query + "; SELECT %s.currval FROM dual" % seqname


def dburl2dict(url):
    """
    Takes a URL to a database and parses it into an equivalent dictionary.

        >>> dburl2dict('postgres:///mygreatdb') == {'pw': None, 'dbn': 'postgres', 'db': 'mygreatdb', 'host': None, 'user': None, 'port': None}
        True
        >>> dburl2dict('postgres://james:day@serverfarm.example.net:5432/mygreatdb') == {'pw': 'day', 'dbn': 'postgres', 'db': 'mygreatdb', 'host': 'serverfarm.example.net', 'user': 'james', 'port': 5432}
        True
        >>> dburl2dict('postgres://james:day@serverfarm.example.net/mygreatdb') == {'pw': 'day', 'dbn': 'postgres', 'db': 'mygreatdb', 'host': 'serverfarm.example.net', 'user': 'james', 'port': None}
        True
        >>> dburl2dict('postgres://james:d%40y@serverfarm.example.net/mygreatdb') == {'pw': 'd@y', 'dbn': 'postgres', 'db': 'mygreatdb', 'host': 'serverfarm.example.net', 'user': 'james', 'port': None}
        True
        >>> dburl2dict('mysql://james:d%40y@serverfarm.example.net/mygreatdb') == {'pw': 'd@y', 'dbn': 'mysql', 'db': 'mygreatdb', 'host': 'serverfarm.example.net', 'user': 'james', 'port': None}
        True
        >>> dburl2dict('sqlite:///mygreatdb.db')
        {'db': 'mygreatdb.db', 'dbn': 'sqlite'}
        >>> dburl2dict('sqlite:////absolute/path/mygreatdb.db')
        {'db': '/absolute/path/mygreatdb.db', 'dbn': 'sqlite'}
    """
    parts = urlparse.urlparse(unquote(url))

    if parts.scheme == "sqlite":
        return {"dbn": parts.scheme, "db": parts.path[1:]}
    else:
        return {
            "dbn": parts.scheme,
            "user": parts.username,
            "pw": parts.password,
            "db": parts.path[1:],
            "host": parts.hostname,
            "port": parts.port,
        }


_databases = {}


def database(dburl=None, **params):
    """Creates appropriate database using params.

    Pooling will be enabled if DBUtils module is available.
    Pooling can be disabled by passing pooling=False in params.
    """
    if not dburl and not params:
        dburl = os.environ["DATABASE_URL"]

    if dburl:
        params = dburl2dict(dburl)

    dbn = params.pop("dbn")
    if dbn in _databases:
        return _databases[dbn](**params)
    else:
        raise UnknownDB(dbn)


def register_database(name, clazz):
    """
    Register a database.

        >>> class LegacyDB(DB):
        ...     def __init__(self, **params):
        ...        pass
        ...
        >>> register_database('legacy', LegacyDB)
        >>> db = database(dbn='legacy', db='test', user='joe', passwd='secret')
    """
    _databases[name] = clazz


register_database("mysql", MySQLDB)
register_database("postgres", PostgresDB)
register_database("sqlite", SqliteDB)
register_database("firebird", FirebirdDB)
register_database("mssql", MSSQLDB)
register_database("oracle", OracleDB)


def _interpolate(format):
    """
    Takes a format string and returns a list of 2-tuples of the form
    (boolean, string) where boolean says whether string should be evaled
    or not.

    from <http://lfw.org/python/Itpl.py> (public domain, Ka-Ping Yee)
    """

    def matchorfail(text, pos):
        match = tokenprog.match(text, pos)
        if match is None:
            raise _ItplError(text, pos)
        return match, match.end()

    namechars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_"
    chunks = []
    pos = 0

    while 1:
        dollar = format.find("$", pos)
        if dollar < 0:
            break
        nextchar = format[dollar + 1]

        if nextchar == "{":
            chunks.append((0, format[pos:dollar]))
            pos, level = dollar + 2, 1
            while level:
                match, pos = matchorfail(format, pos)
                tstart, tend = match.regs[3]
                token = format[tstart:tend]
                if token == "{":
                    level = level + 1
                elif token == "}":
                    level = level - 1
            chunks.append((1, format[dollar + 2 : pos - 1]))

        elif nextchar in namechars:
            chunks.append((0, format[pos:dollar]))
            match, pos = matchorfail(format, dollar + 1)
            while pos < len(format):
                if (
                    format[pos] == "."
                    and pos + 1 < len(format)
                    and format[pos + 1] in namechars
                ):
                    match, pos = matchorfail(format, pos + 1)
                elif format[pos] in "([":
                    pos, level = pos + 1, 1
                    while level:
                        match, pos = matchorfail(format, pos)
                        tstart, tend = match.regs[3]
                        token = format[tstart:tend]
                        if token[0] in "([":
                            level = level + 1
                        elif token[0] in ")]":
                            level = level - 1
                else:
                    break
            chunks.append((1, format[dollar + 1 : pos]))
        else:
            chunks.append((0, format[pos : dollar + 1]))
            pos = dollar + 1 + (nextchar == "$")

    if pos < len(format):
        chunks.append((0, format[pos:]))
    return chunks


class _Node(object):
    def __init__(self, type, first, second=None):
        self.type = type
        self.first = first
        self.second = second

    def __eq__(self, other):
        return (
            isinstance(other, _Node)
            and self.type == other.type
            and self.first == other.first
            and self.second == other.second
        )

    def __repr__(self):
        return "Node(%r, %r, %r)" % (self.type, self.first, self.second)


class Parser:
    """Parser to parse string templates like "Hello $name".

    Loosely based on <http://lfw.org/python/Itpl.py> (public domain, Ka-Ping Yee)
    """

    namechars = "abcdefghijklmnopqrstuvwxyz" "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_"

    def __init__(self):
        self.reset()

    def reset(self):
        self.pos = 0
        self.level = 0
        self.text = ""

    def parse(self, text):
        """Parses the given text and returns a parse tree.
        """
        self.reset()
        self.text = text
        return self.parse_all()

    def parse_all(self):
        while True:
            dollar = self.text.find("$", self.pos)
            if dollar < 0:
                break
            nextchar = self.text[dollar + 1]
            if nextchar in self.namechars:
                yield _Node("text", self.text[self.pos : dollar])
                self.pos = dollar + 1
                yield self.parse_expr()

            # for supporting ${x.id}, for backward compataility
            elif nextchar == "{":
                saved_pos = self.pos
                self.pos = dollar + 2  # skip "${"
                expr = self.parse_expr()
                if self.text[self.pos] == "}":
                    self.pos += 1
                    yield _Node("text", self.text[self.pos : dollar])
                    yield expr
                else:
                    self.pos = saved_pos
                    break
            else:
                yield _Node("text", self.text[self.pos : dollar + 1])
                self.pos = dollar + 1
                # $$ is used to escape $
                if nextchar == "$":
                    self.pos += 1

        if self.pos < len(self.text):
            yield _Node("text", self.text[self.pos :])

    def match(self):
        match = tokenprog.match(self.text, self.pos)
        if match is None:
            raise _ItplError(self.text, self.pos)
        return match, match.end()

    def is_literal(self, text):
        return text and text[0] in "0123456789\"'"

    def parse_expr(self):
        match, pos = self.match()
        if self.is_literal(match.group()):
            expr = _Node("literal", match.group())
        else:
            expr = _Node("param", self.text[self.pos : pos])
        self.pos = pos
        while self.pos < len(self.text):
            if (
                self.text[self.pos] == "."
                and self.pos + 1 < len(self.text)
                and self.text[self.pos + 1] in self.namechars
            ):
                self.pos += 1
                match, pos = self.match()
                attr = match.group()
                expr = _Node("getattr", expr, attr)
                self.pos = pos
            elif self.text[self.pos] == "[":
                saved_pos = self.pos
                self.pos += 1
                key = self.parse_expr()
                if self.text[self.pos] == "]":
                    self.pos += 1
                    expr = _Node("getitem", expr, key)
                else:
                    self.pos = saved_pos
                    break
            else:
                break
        return expr


class SafeEval(object):
    """Safe evaluator for binding params to db queries.
    """

    def safeeval(self, text, mapping):
        nodes = Parser().parse(text)
        return SQLQuery.join([self.eval_node(node, mapping) for node in nodes], "")

    def eval_node(self, node, mapping):
        if node.type == "text":
            return node.first
        else:
            return sqlquote(self.eval_expr(node, mapping))

    def eval_expr(self, node, mapping):
        if node.type == "literal":
            return ast.literal_eval(node.first)
        elif node.type == "getattr":
            return getattr(self.eval_expr(node.first, mapping), node.second)
        elif node.type == "getitem":
            return self.eval_expr(node.first, mapping)[
                self.eval_expr(node.second, mapping)
            ]
        elif node.type == "param":
            return mapping[node.first]


def test_parser():
    def f(text, expected):
        p = Parser()
        nodes = list(p.parse(text))
        print(repr(text), nodes)
        assert nodes == expected, "Expected %r" % expected

    f("Hello", [_Node("text", "Hello")])
    f("Hello $name", [_Node("text", "Hello "), _Node("param", "name")])
    f(
        "Hello $name.foo",
        [_Node("text", "Hello "), _Node("getattr", _Node("param", "name"), "foo")],
    )
    f(
        "WHERE id=$self.id LIMIT 1",
        [
            _Node("text", "WHERE id="),
            _Node("getattr", _Node("param", "self", None), "id"),
            _Node("text", " LIMIT 1"),
        ],
    )

    f(
        "WHERE id=$self['id'] LIMIT 1",
        [
            _Node("text", "WHERE id="),
            _Node("getitem", _Node("param", "self", None), _Node("literal", "'id'")),
            _Node("text", " LIMIT 1"),
        ],
    )


def test_safeeval():
    def f(q, vars):
        return SafeEval().safeeval(q, vars)

    print(f("WHERE id=$id", {"id": 1}).items)
    assert f("WHERE id=$id", {"id": 1}).items == ["WHERE id=", sqlparam(1)]


if __name__ == "__main__":
    import doctest

    doctest.testmod()
    test_parser()
    test_safeeval()
