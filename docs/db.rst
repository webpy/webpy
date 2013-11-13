Accessing the database
======================

Web.py provides a simple and uniform interface to the database that you want to work with, whether it is PostgreSQL, MySQL, SQLite or any other. It doesn't try to build layers between you and your database. Rather, it tries to make it easy to perform common tasks, and get out of your way when you need to do more advanced things.


Create database object
------------------------

The first thing to work with databases from web.py is to create a
create a database object with `web.database()`. It returns database object, which has convenient methods for you to use.

Make sure that you have appropriate database library installed (`psycopg2` for PostgreSQL, `MySQLdb` for MySQL, `sqlite3` for SQLite).

::

    db = web.database(dbn='postgres', db='dbname', user='username', pw='password')

`dbn` for MySQL is `mysql` and `sqlite` for SQLite. SQLite doesn't take `user` `pw` parameters.

Multiple databases
``````````````````

Working with more databases is not at all difficult with web.py. Here's what you do.

::

    db1 = web.database(dbn='postgres', db='dbname1', user='username1', pw='password2')
    db2 = web.database(dbn='postgres', db='dbname2', user='username2', pw='password2')

And use `db1`, `db2` to access those databases respectively.


Operations
----------
`web.database()` returns an object which provide you all the functionality to insert, select, update and delete data from your database. For each of the methods on `db` below, you can pass `_test=True` to see the SQL statement rather than executing it.


Inserting
`````````
::

    # Insert an entry into table 'user'
    userid = db.insert('user', firstname="Bob", lastname="Smith", joindate=web.SQLLiteral("NOW()"))


The first argument is the table name and the rest of them are set of named arguments which represent the fields in the table. If values are not given, the database may create default values or issue a warning.

For bulk insertion rather than inserting record by record, use `Multiple Inserts` rather.

Selecting
`````````

The `select` method is used for selecting rows from the database. It returns a `web.iterbetter` object, which can be looped through.

To select `all` the rows from the `user` table, you would simply do

::

    users = db.select('user')

For the real world use cases, `select` method takes `vars`, `what`, `where`, `order`, `group`, `limit`, `offset`, and `_test` optional parameters.

::

    users = db.select('users', where="id>100")

To prevent SQL injection attacks, you can use `$key` in where clause and pass the `vars` which has { 'key': value }.

::

    vars = dict(name="Bob")
    results = db.select('users', where="name = $name", vars=vars, _test=True)
    >>> results
    <sql: "SELECT * FROM users WHERE name = 'Bob'">


Updating
````````
The `update` method accepts same kind of arguments as Select. It returns the number of rows updated.

::

    num_updated  = db.update('users', where="id = 10", firstname = "Foo")

Deleting
````````
The `delete` method returns the number of rows deleted. It also accepts "using" and "vars" parameters. See ``Selecting`` for more details on `vars`.

::

    num_deleted = db.delete('users', where="id=10")

Multiple Inserts
````````````````
The `multiple_insert` method on the `db` object allows you to do that. All that's needed is to prepare a list of dictionaries, one for each row to be inserted, each with the same set of keys and pass it to `multiple_insert` along with the table name. It returns the list of ids of the inserted rows.

The value of `db.supports_multiple_insert` tells you if your database supports multiple inserts.
::

    values = [{"name": "foo", "email": "foo@example.com"}, {"name": "bar", "email": "bar@example.com"}]
    db.multiple_insert('person', values=values)


Advanced querying
`````````````````
Many a times, there is more to do with the database, rather than the simple operations which can be done by `insert`, `select`, `delete` and `update` - Things like your favorite (or scary) joins, counts etc. All these are possible with `query` method, which also takes `vars`.

::

    results = db.query("SELECT COUNT(*) AS total_users FROM users")
    print results[0].total_users # prints number of entries in 'users' table

Joining tables
::

    results = db.query("SELECT * FROM entries JOIN users WHERE entries.author_id = users.id")


Transactions
````````````
The database object has a method `transaction` which starts a new transaction and returns the transaction object. The transaction object can be used to commit or rollback that transaction. It is also possible to have nested transactions.

From Python 2.5 onwards, which support `with` statements, you would do

::

    with db.transaction():
        userid = db.insert('users', name='foo')
        authorid = db.insert('authors', userid=userid)


For earlier versions of Python, you can do

::

    t = db.transaction()
    try:
        userid = db.insert('users', name='foo')
        authorid = db.insert('authors', userid=userid)
    except:
        t.rollback()
        raise
    else:
        t.commit()
