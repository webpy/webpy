Authentication and authorization
================================

Web.py handles basic requirements for users and access rights management. It
is not meant to introduce a complex system but a simple set of tools that is
often sufficient and can be easily expanded if needed.


Create auth object
------------------

If you want to handle users and permissions you must create an instance of Auth
object with `web.auth.Auth()`. It has all methods you need for authentication
and authorization. Object requires parameters `session` and `database`.
Optionaly attribute `lgn_pg` defines the URL on which is made redirection in
case when you have not the right permissions, if it is not defined,
`web.forbidden()` is raised.    

.. code:: python

    db = web.database(...)
    session = web.session.Session(...)

    auth = web.auth.Auth(session, db, lgn_pg='/login')


Users storage
-------------

Next next step is to create a users storage. It consist from a table which
contains username, crypted password (BINARY or VARCHAR, length depends on used
algoritm) and role.

SQL command which can be used for creation of a sample users table in MySQL:

::

    CREATE TABLE users (
        usr VARCHAR(30) NOT NULL PRIMARY KEY,
        passwd BINARY(60) NOT NULL,
        role VARCHAR(30) NOT NULL
    );


Authorization – login
---------------------

Authorization is carried out via a simple form. It may looks like this:

::
    
    <form action="/login" method="POST">
    <input type="text" name="usr" placeHolder="Username" /><br />
    <input type="password" name="passwd" placeHolder="Password" /><br />
    <input type="submit" value="Log in" />
    </form>
    

Submited form is then processed by function `login`. In case of wrong password
or non-existing user function returns *WrongPassword* or *UserNotFound*
exception.

.. code:: python
    
    def POST(self):
        usr = web.input().usr
        passwd = web.input().passwd
        try:
            auth.login(usr, passwd)
            raise web.seeother('/private')
        except web.auth.UserNotFound, web.auth.WrongPassword:
            return render.login()

*Hint: It's still possible to return to a login form with browser's back button
after login. If you want to prevent it, you can add following code to the start
of GET function which generates login page:*

.. code:: python
    
    web.header("Cache-Control", "no-cache, max-age=0, must-revalidate, no-store")


For log out from Auth object use `logout()` function:

.. code:: python
    
    def GET(self):
        auth.logout()


Authentication – rights
-----------------------

For user rights and roles handling you can use following three functions.

Decorator
`````````
The main way to define page's roles is decorator `auth`. If you want to define
allowed roles, just add `@role(role1, role2,...)` before the `GET` or `POST`
method.

.. code:: python
    
    @auth.role('admin')
    def GET(self):
        return render.text("Admin's page")


Has role
````````
Another rights checking method is `hasRole`. It returns `True` if logged user
has one of listed roles.

.. code:: python
    
    >>> auth.hasRole('user', 'admin')
    True

Get role
````````
Method `getRole` returns logged user's role. If there is no logged user,
returns `None`.

.. code:: python
    
    >>> auth.getRole()
    'admin'


Password crypting
-----------------

Auth module also contains crypting and passwords-comparing functions. These can
be use while saving new users etc.

Standard crypting uses SHA256 (`sha256salt`) algorithm with generated salt. It
may be sufficient for most purposes. Standard format is
`64alfanumericpass$64alfanumericsalt`, you must reserve at least 129 chars long
VARCHAR or BINARY column in database.

If you want to use extra-save and slower algorithm, you may use Bcrypt
(`bcrypt`). It requires extra library installed (it's named `py-bcrypt` in
pip). You must reserve at least 60 chars long VARCHAR or BINARY column in
database.

By default it uses standard algorithm defined in configuration, if you want to
use another one, you must define it as key. 

.. code:: python
    
    crypt = auth.Crypt()

    >>> crypt.encrypt("tiger") # encrypt with default sha256 alg
    '0a57e44ff2...a2dc11f5$05f54e...495020d6f'
    >>> crypt['sha256salt'].encrypt("tiger") # do the same (with other salt)
    '6b0b76fcd5...0734f80a$fa8f35...26d5b8cc0'
    >>> crypt['bcrypt'].encrypt("tiger") # uses bcrypt alg
    '$2a$10$aKiFSfoppYby82G.qFFDa.qL9DKOgGiiixedqC8f62UzgJpJ/j19.'

    >>> crypt.compare("tiger", cryptedPassword1) # compare plain and crypted pass
    True
    >>> crypt['sha256salt'].compare("tiger", cryptedPassword1) # do the same
    True
    >>> crypt['bcrypt'].compare("tiger", cryptedPassword2) # uses bcrypt alg
    True


Additional settings
-------------------

Default Auth settings is stored in `web.config.auth`.

.. code:: python
    
    web.config.auth = utils.storage({
        # database settings
        'table_name': 'users',
        'user_column': 'usr',
        'password_column': 'passwd',
        'role_column': 'role',
        # hashing/crypting (bcrypt|sha256salt)
        'crypt': 'sha256salt',
        'bcrypt_loops': 10,
        'sha_salt_len': 64
    })

You can change default options in the beginning of the application.

.. code:: python
    
    web.config.auth.crypt = 'bcrypt'
