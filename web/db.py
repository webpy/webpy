"""
Database API
(part of web.py)
"""

# todo:
#  - test with sqlite
#  - a store function?

__all__ = [
  "UnknownParamstyle", "UnknownDB",
  "sqllist", "sqlors", "aparam", "reparam",
  "SQLQuery", "sqlquote",
  "SQLLiteral", "sqlliteral",
  "connect", 
  "TransactionError", "transaction", "transact", "commit", "rollback",
  "query",
  "select", "insert", "update", "delete"
]

import time
try: import datetime
except ImportError: datetime = None

from utils import storage, iters, iterbetter
import webapi as web

try:
    from DBUtils import PooledDB
    web.config._hasPooling = True
except ImportError:
    web.config._hasPooling = False

class _ItplError(ValueError):
    def __init__(self, text, pos):
        ValueError.__init__(self)
        self.text = text
        self.pos = pos
    def __str__(self):
        return "unfinished expression in %s at char %d" % (
            repr(self.text), self.pos)

def _interpolate(format):
    """
    Takes a format string and returns a list of 2-tuples of the form
    (boolean, string) where boolean says whether string should be evaled
    or not.
    
    from <http://lfw.org/python/Itpl.py> (public domain, Ka-Ping Yee)
    """
    from tokenize import tokenprog
    
    def matchorfail(text, pos):
        match = tokenprog.match(text, pos)
        if match is None:
            raise _ItplError(text, pos)
        return match, match.end()
    
    namechars = "abcdefghijklmnopqrstuvwxyz" \
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_";
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
            chunks.append((1, format[dollar + 2:pos - 1]))

        elif nextchar in namechars:
            chunks.append((0, format[pos:dollar]))
            match, pos = matchorfail(format, dollar + 1)
            while pos < len(format):
                if format[pos] == "." and \
                    pos + 1 < len(format) and format[pos + 1] in namechars:
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
            chunks.append((1, format[dollar + 1:pos]))

        else:
            chunks.append((0, format[pos:dollar + 1]))
            pos = dollar + 1 + (nextchar == "$")

    if pos < len(format): 
        chunks.append((0, format[pos:]))
    return chunks

class UnknownParamstyle(Exception):
    """
    raised for unsupported db paramstyles
    
    (currently supported: qmark, numeric, format, pyformat)
    """
    pass

def aparam():
    """
    Returns the appropriate string to be used to interpolate
    a value with the current `web.ctx.db_module` or simply %s
    if there isn't one.
    
        >>> aparam()
        '%s'
    """
    if hasattr(web.ctx, 'db_module'):
        style = web.ctx.db_module.paramstyle
    else:
        style = 'pyformat'
    
    if style == 'qmark': 
        return '?'
    elif style == 'numeric': 
        return ':1'
    elif style in ['format', 'pyformat']: 
        return '%s'
    raise UnknownParamstyle, style

def reparam(string_, dictionary):
    """
    Takes a string and a dictionary and interpolates the string
    using values from the dictionary. Returns an `SQLQuery` for the result.
    
        >>> reparam("s = $s", dict(s=True))
        <sql: "s = 't'">
    """
    # making a copy of dictionary because eval mangles it
    dictionary = dictionary.copy()
    vals = []
    result = []
    for live, chunk in _interpolate(string_):
        if live:
            result.append(aparam())
            vals.append(eval(chunk, dictionary))
        else: result.append(chunk)
    return SQLQuery(''.join(result), vals)

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
        return 'NULL'
    elif obj is True:
        return "'t'"
    elif obj is False:
        return "'f'"
    elif datetime and isinstance(obj, datetime.datetime):
        return repr(obj.isoformat())
    else:
        return repr(obj)

class SQLQuery:
    """
    You can pass this sort of thing as a clause in any db function.
    Otherwise, you can pass a dictionary to the keyword argument `vars`
    and the function will call reparam for you.
    """
    # tested in sqlquote's docstring
    def __init__(self, s='', v=()):
        self.s, self.v = str(s), tuple(v)
    
    def __getitem__(self, key): # for backwards-compatibility
        return [self.s, self.v][key]

    def __add__(self, other):
        if isinstance(other, str):
            self.s += other
        elif isinstance(other, SQLQuery):
            self.s += other.s
            self.v += other.v
        return self

    def __radd__(self, other):
        if isinstance(other, str):
            self.s = other + self.s
            return self
        else:
            return NotImplemented
    
    def __str__(self):
        try:
            return self.s % tuple([sqlify(x) for x in self.v])
        except (ValueError, TypeError):
            return self.s
    
    def __repr__(self):
        return '<sql: %s>' % repr(str(self))

class SQLLiteral:
    """
    Protects a string from `sqlquote`.

        >>> insert('foo', time=SQLLiteral('NOW()'), _test=True)
        <sql: 'INSERT INTO foo (time) VALUES (NOW())'>
    """
    def __init__(self, v): 
        self.v = v

    def __repr__(self): 
        return self.v

sqlliteral = SQLLiteral

def sqlquote(a):
    """
    Ensures `a` is quoted properly for use in a SQL query.
    
        >>> 'WHERE x = ' + sqlquote(True) + ' AND y = ' + sqlquote(3)
        <sql: "WHERE x = 't' AND y = 3">
    """
    return SQLQuery(aparam(), (a,))

class UnknownDB(Exception):
    """raised for unsupported dbms"""
    pass

def connect(dbn, **keywords):
    """
    Connects to the specified database. 
    
    `dbn` currently must be "postgres", "mysql", or "sqlite". 
    
    If DBUtils is installed, connection pooling will be used.
    """
    if dbn == "postgres": 
        try: 
            import psycopg2 as db
            
            # fix for Bug#177265
            import psycopg2.extensions
            psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)            
        except ImportError: 
            try: 
                import psycopg as db
            except ImportError: 
                import pgdb as db
        if 'pw' in keywords:
            keywords['password'] = keywords['pw']
            del keywords['pw']
        keywords['database'] = keywords['db']
        del keywords['db']

    elif dbn == "mysql":
        import MySQLdb as db
        if 'pw' in keywords:
            keywords['passwd'] = keywords['pw']
            del keywords['pw']
        db.paramstyle = 'pyformat' # it's both, like psycopg

    elif dbn == "sqlite":
        try:
            import sqlite3 as db
            db.paramstyle = 'qmark'
        except ImportError:
            try:
                from pysqlite2 import dbapi2 as db
                db.paramstyle = 'qmark'
            except ImportError:
                import sqlite as db
        web.config._hasPooling = False
        keywords['database'] = keywords['db']
        del keywords['db']
    
    elif dbn == "firebird":
        import kinterbasdb as db
        if 'pw' in keywords:
            keywords['passwd'] = keywords['pw']
            del keywords['pw']
        keywords['database'] = keywords['db']
        del keywords['db']

    else: 
        raise UnknownDB, dbn

    web.ctx.db_name = dbn
    web.ctx.db_module = db
    web.ctx.db_transaction = 0
    web.ctx.db = keywords

    def _PooledDB(db, keywords):
        # In DBUtils 0.9.3, `dbapi` argument is renamed as `creator`
        # see Bug#122112
        if PooledDB.__version__.split('.') < '0.9.3'.split('.'):
            return PooledDB.PooledDB(dbapi=db, **keywords)
        else:
            return PooledDB.PooledDB(creator=db, **keywords)
    
    def db_cursor():
        if isinstance(web.ctx.db, dict):
            keywords = web.ctx.db
            if web.config._hasPooling:
                if 'db' not in globals(): 
                    globals()['db'] = _PooledDB(db, keywords)
                web.ctx.db = globals()['db'].connection()
            else:
                web.ctx.db = db.connect(**keywords)  
    
            # fix for Bug#177265
            if web.ctx.get('db_name') == "postgres":
                try:
                    if web.config._hasPooling:
                        # hack to call a function in actual db connection
                        web.ctx.db._con._con.set_client_encoding('UTF8')
                    else:
                        web.ctx.db.set_client_encoding('UTF8')
                except Exception, e:
                   print >> web.debug, 'Error in setting utf-8 encoding:', str(e), '(ignored)' 

        return web.ctx.db.cursor()
    web.ctx.db_cursor = db_cursor

    web.ctx.dbq_count = 0
    
    def db_execute(cur, sql_query, dorollback=True):
        """executes an sql query"""

        web.ctx.dbq_count += 1
        
        try:
            a = time.time()
            out = cur.execute(sql_query.s, sql_query.v)
            b = time.time()
        except:
            if web.config.get('db_printing'):
                print >> web.debug, 'ERR:', str(sql_query)
            if dorollback and not web.ctx.db_transaction: web.ctx.db.rollback() 
            raise

        if web.config.get('db_printing'):
            print >> web.debug, '%s (%s): %s' % (round(b-a, 2), web.ctx.dbq_count, str(sql_query))

        return out
    web.ctx.db_execute = db_execute
    return web.ctx.db

class TransactionError(Exception): pass

class transaction:
    """
    A context that can be used in conjunction with "with" statements
    to implement SQL transactions. Starts a transaction on enter,
    rolls it back if there's an error; otherwise it commits it at the
    end.
    """
    def __enter__(self):
        self.db_transaction = web.ctx.db_transaction
        transact()

    def __exit__(self, exctype, excvalue, traceback):
        if exctype is not None:
            while self.db_transaction < web.ctx.db_transaction:
                rollback()
        else:
            commit()

def transact():
    """Start a transaction."""
    if not web.ctx.db_transaction:
        # commit everything up to now, so we don't rollback it later
        if hasattr(web.ctx.db, 'commit'): 
            web.ctx.db.commit()
    else:
        db_cursor = web.ctx.db_cursor()
        web.ctx.db_execute(db_cursor, 
            SQLQuery("SAVEPOINT webpy_sp_%s" % web.ctx.db_transaction))
    web.ctx.db_transaction += 1

def commit():
    """Commits a transaction."""
    web.ctx.db_transaction -= 1
    if web.ctx.db_transaction < 0: 
        raise TransactionError, "not in a transaction"

    if not web.ctx.db_transaction:
        if hasattr(web.ctx.db, 'commit'): 
            web.ctx.db.commit()
    else:
        db_cursor = web.ctx.db_cursor()
        web.ctx.db_execute(db_cursor, 
            SQLQuery("RELEASE SAVEPOINT webpy_sp_%s" % web.ctx.db_transaction))

def rollback(care=True):
    """Rolls back a transaction."""
    web.ctx.db_transaction -= 1     
    if web.ctx.db_transaction < 0:
        web.ctx.db_transaction = 0
        if care:
            raise TransactionError, "not in a transaction"
        else:
            return

    if not web.ctx.db_transaction:
        if hasattr(web.ctx.db, 'rollback'): 
            web.ctx.db.rollback()
    else:
        db_cursor = web.ctx.db_cursor()
        web.ctx.db_execute(db_cursor,
            SQLQuery("ROLLBACK TO SAVEPOINT webpy_sp_%s" % web.ctx.db_transaction),
            dorollback=False)

def query(sql_query, vars=None, processed=False, _test=False):
    """
    Execute SQL query `sql_query` using dictionary `vars` to interpolate it.
    If `processed=True`, `vars` is a `reparam`-style list to use 
    instead of interpolating.
    
        >>> query("SELECT * FROM foo", _test=True)
        <sql: 'SELECT * FROM foo'>
        >>> query("SELECT * FROM foo WHERE x = $x", vars=dict(x='f'), _test=True)
        <sql: "SELECT * FROM foo WHERE x = 'f'">
        >>> query("SELECT * FROM foo WHERE x = " + sqlquote('f'), _test=True)
        <sql: "SELECT * FROM foo WHERE x = 'f'">
    """
    if vars is None: vars = {}
    
    if not processed and not isinstance(sql_query, SQLQuery):
        sql_query = reparam(sql_query, vars)
    
    if _test: return sql_query
    
    db_cursor = web.ctx.db_cursor()
    web.ctx.db_execute(db_cursor, sql_query)
    
    if db_cursor.description:
        names = [x[0] for x in db_cursor.description]
        def iterwrapper():
            row = db_cursor.fetchone()
            while row:
                yield storage(dict(zip(names, row)))
                row = db_cursor.fetchone()
        out = iterbetter(iterwrapper())
        if web.ctx.db_name != "sqlite":
            out.__len__ = lambda: int(db_cursor.rowcount)
        out.list = lambda: [storage(dict(zip(names, x))) \
                           for x in db_cursor.fetchall()]
    else:
        out = db_cursor.rowcount
    
    if not web.ctx.db_transaction: web.ctx.db.commit()
    return out

def sqllist(lst):
    """
    Converts the arguments for use in something like a WHERE clause.
    
        >>> sqllist(['a', 'b'])
        'a, b'
        >>> sqllist('foo')
        'foo'
        >>> sqllist(u'foo')
        u'foo'
    """
    if isinstance(lst, (str, unicode)): 
        return lst
    else:
        return ', '.join(lst)

def sqlors(left, lst):
    """
    `left is a SQL clause like `tablename.arg = ` 
    and `lst` is a list of values. Returns a reparam-style
    pair featuring the SQL that ORs together the clause
    for each item in the lst.

        >>> sqlors('foo = ', [])
        <sql: '2+2=5'>
        >>> sqlors('foo = ', [1])
        <sql: 'foo = 1'>
        >>> sqlors('foo = ', 1)
        <sql: 'foo = 1'>
        >>> sqlors('foo = ', [1,2,3])
        <sql: '(foo = 1 OR foo = 2 OR foo = 3)'>
    """
    if isinstance(lst, iters):
        lst = list(lst)
        ln = len(lst)
        if ln == 0:
            return SQLQuery("2+2=5", [])
        if ln == 1: 
            lst = lst[0]

    if isinstance(lst, iters):
        return SQLQuery('(' + left + 
               (' OR ' + left).join([aparam() for param in lst]) + ")", lst)
    else:
        return SQLQuery(left + aparam(), [lst])

def sqlwhere(dictionary, grouping=' AND '):
    """
    Converts a `dictionary` to an SQL WHERE clause `SQLQuery`.
    
        >>> sqlwhere({'cust_id': 2, 'order_id':3})
        <sql: 'order_id = 3 AND cust_id = 2'>
        >>> sqlwhere({'cust_id': 2, 'order_id':3}, grouping=', ')
        <sql: 'order_id = 3, cust_id = 2'>
    """
    
    return SQLQuery(grouping.join([
      '%s = %s' % (k, aparam()) for k in dictionary.keys()
    ]), dictionary.values())

def select(tables, vars=None, what='*', where=None, order=None, group=None, 
           limit=None, offset=None, _test=False):
    """
    Selects `what` from `tables` with clauses `where`, `order`, 
    `group`, `limit`, and `offset`. Uses vars to interpolate. 
    Otherwise, each clause can be a SQLQuery.
    
        >>> select('foo', _test=True)
        <sql: 'SELECT * FROM foo'>
        >>> select(['foo', 'bar'], where="foo.bar_id = bar.id", limit=5, _test=True)
        <sql: 'SELECT * FROM foo, bar WHERE foo.bar_id = bar.id LIMIT 5'>
    """
    if vars is None: vars = {}
    qout = ""
    
    def gen_clause(sql, val):
        if isinstance(val, (int, long)):
            if sql == 'WHERE':
                nout = 'id = ' + sqlquote(val)
            else:
                nout = SQLQuery(val)
        elif isinstance(val, (list, tuple)) and len(val) == 2:
            nout = SQLQuery(val[0], val[1]) # backwards-compatibility
        elif isinstance(val, SQLQuery):
            nout = val
        elif val:
            nout = reparam(val, vars)
        else: 
            return ""

        out = ""
        if qout: out += " " 
        out += sql + " " + nout
        return out
    
    if web.ctx.get('db_name') == "firebird":
        for (sql, val) in (
           ('FIRST', limit),
           ('SKIP', offset)
        ):
            qout += gen_clause(sql, val)
        if qout:
            SELECT = 'SELECT ' + qout
        else:
            SELECT = 'SELECT'
        qout = ""
        sql_clauses = (
          (SELECT, what),
          ('FROM', sqllist(tables)),
          ('WHERE', where),
          ('GROUP BY', group),
          ('ORDER BY', order)
        )
    else:
        sql_clauses = (
          ('SELECT', what),
          ('FROM', sqllist(tables)),
          ('WHERE', where),
          ('GROUP BY', group),
          ('ORDER BY', order),
          ('LIMIT', limit),
          ('OFFSET', offset)
        )

    for (sql, val) in sql_clauses:
        qout += gen_clause(sql, val)

    if _test: return qout
    return query(qout, processed=True)

def insert(tablename, seqname=None, _test=False, **values):
    """
    Inserts `values` into `tablename`. Returns current sequence ID.
    Set `seqname` to the ID if it's not the default, or to `False`
    if there isn't one.
    
        >>> insert('foo', joe='bob', a=2, _test=True)
        <sql: "INSERT INTO foo (a, joe) VALUES (2, 'bob')">
    """
    
    if values:
        sql_query = SQLQuery("INSERT INTO %s (%s) VALUES (%s)" % (
            tablename,
            ", ".join(values.keys()),
            ', '.join([aparam() for x in values])
        ), values.values())
    else:
        sql_query = SQLQuery("INSERT INTO %s DEFAULT VALUES" % tablename)

    if _test: return sql_query
    
    db_cursor = web.ctx.db_cursor()
    if seqname is False: 
        pass
    elif web.ctx.db_name == "postgres": 
        if seqname is None: 
            seqname = tablename + "_id_seq"
        sql_query += "; SELECT currval('%s')" % seqname
    elif web.ctx.db_name == "mysql":
        web.ctx.db_execute(db_cursor, sql_query)
        sql_query = SQLQuery("SELECT last_insert_id()")
    elif web.ctx.db_name == "sqlite":
        web.ctx.db_execute(db_cursor, sql_query)
        # not really the same...
        sql_query = SQLQuery("SELECT last_insert_rowid()")
    
    web.ctx.db_execute(db_cursor, sql_query)
    try: 
        out = db_cursor.fetchone()[0]
    except Exception: 
        out = None
    
    if not web.ctx.db_transaction: web.ctx.db.commit()

    return out

def update(tables, where, vars=None, _test=False, **values):
    """
    Update `tables` with clause `where` (interpolated using `vars`)
    and setting `values`.
    
        >>> joe = 'Joseph'
        >>> update('foo', where='name = $joe', name='bob', age=5,
        ...   vars=locals(), _test=True)
        <sql: "UPDATE foo SET age = 5, name = 'bob' WHERE name = 'Joseph'">
    """
    if vars is None: vars = {}
    
    if isinstance(where, (int, long)):
        where = "id = " + sqlquote(where)
    elif isinstance(where, (list, tuple)) and len(where) == 2:
        where = SQLQuery(where[0], where[1])
    elif isinstance(where, SQLQuery):
        pass
    else:
        where = reparam(where, vars)
    
    query = (
      "UPDATE " + sqllist(tables) + 
      " SET " + sqlwhere(values, ', ') + 
      " WHERE " + where)
    
    if _test: return query
    
    db_cursor = web.ctx.db_cursor()
    web.ctx.db_execute(db_cursor, query)
    
    if not web.ctx.db_transaction: web.ctx.db.commit()
    return db_cursor.rowcount

def delete(table, where=None, using=None, vars=None, _test=False):
    """
    Deletes from `table` with clauses `where` and `using`.
    
        >>> name = 'Joe'
        >>> delete('foo', where='name = $name', vars=locals(), _test=True)
        <sql: "DELETE FROM foo WHERE name = 'Joe'">
    """
    if vars is None: vars = {}

    if isinstance(where, (int, long)):
        where = "id = " + sqlquote(where)
    elif isinstance(where, (list, tuple)) and len(where) == 2:
        where = SQLQuery(where[0], where[1])
    elif isinstance(where, SQLQuery):
        pass
    elif where is None:
        pass
    else:
        where = reparam(where, vars)

    q = 'DELETE FROM ' + table
    if where:
        q += ' WHERE ' + where
    if using and web.ctx.get('db_name') != "firebird":
        q += ' USING ' + sqllist(using)
    
    if _test: return q
    
    db_cursor = web.ctx.db_cursor()
    web.ctx.db_execute(db_cursor, q)

    if not web.ctx.db_transaction: web.ctx.db.commit()
    return db_cursor.rowcount

if __name__ == "__main__":
    import doctest
    doctest.testmod()
