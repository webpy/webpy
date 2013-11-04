Accessing the database
======================

Web.py provides a simple and uniform interface to the database that you want to work with, whether it is PostgreSQL, MySQL, SQLite or any other. It doesn't try to build layers between you and your database. Rather, it tries to make it easy to perform common tasks, and get out of your way when you need to do more advanced things.


Create a database object
------------------------

You could create a database object with `web.database()`. Make sure that you have appropriate database library installed.

PostgreSQL
``````````
Database Library: `psycopg2`
::

    db = web.database(dbn='postgres', db='dbname', user='username', pw='password')

MySQL
`````
Database Library: `MySQLdb`
::

    db = web.database(dbn='mysql', db='dbname', user='username', pw='password')


SQLite
``````

Database Library: `sqlite3`
::

    db = web.database(dbn='sqlite', db='dbname')


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

For bulk insertion rather than inserting record by record, use `multiple_insert` rather.

Bulk Inserting
``````````````


Selecting
`````````
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


Advanced querying
`````````````````

Many a times, there is more to do with the database, rather than the simple operations which can be done by `insert`, `select`, `delete` and `update` - Things like your favorite (or scary) joins, counts etc. All these are possible with `query` method, which also takes `vars`.

::

    results = db.query("SELECT COUNT(*) AS total_users FROM users")
    print results[0].total_users # prints number of entries in 'users' table

Joining tables
::

    results = db.query("SELECT * FROM entries JOIN users WHERE entries.author_id = users.id")


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




