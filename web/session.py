"""
Session Management
(from web.py)
"""

import os
import os.path
import time
import datetime
import base64
import threading
from copy import deepcopy

try:
    import cPickle as pickle
except ImportError:
    import pickle

from hashlib import sha1

from . import utils
from . import webapi as web
from .py3helpers import PY2

__all__ = ["Session", "SessionExpired", "Store", "DiskStore", "DBStore"]

web.config.session_parameters = utils.storage(
    {
        "cookie_name": "webpy_session_id",
        "cookie_domain": None,
        "cookie_path": None,
        "samesite": None,
        "timeout": 86400,  # 24 * 60 * 60, # 24 hours in seconds
        "ignore_expiry": True,
        "ignore_change_ip": True,
        "secret_key": "fLjUfxqXtfNoIldA0A0J",
        "expired_message": "Session expired",
        "httponly": True,
        "secure": False,
    }
)


class SessionExpired(web.HTTPError):
    def __init__(self, message):
        web.HTTPError.__init__(self, "200 OK", {}, data=message)


class Session(object):
    """Session management for web.py
    """

    __slots__ = [
        "store",
        "_initializer",
        "_last_cleanup_time",
        "_config",
        "_data",
        "__getitem__",
        "__setitem__",
        "__delitem__",
    ]

    def __init__(self, app, store, initializer=None):
        self.store = store
        self._initializer = initializer
        self._last_cleanup_time = 0
        self._config = utils.storage(web.config.session_parameters)
        self._data = utils.threadeddict()

        self.__getitem__ = self._data.__getitem__
        self.__setitem__ = self._data.__setitem__
        self.__delitem__ = self._data.__delitem__

        if app:
            app.add_processor(self._processor)

    def __contains__(self, name):
        return name in self._data

    def __getattr__(self, name):
        return getattr(self._data, name)

    def __setattr__(self, name, value):
        if name in self.__slots__:
            object.__setattr__(self, name, value)
        else:
            setattr(self._data, name, value)

    def __delattr__(self, name):
        delattr(self._data, name)

    def _processor(self, handler):
        """Application processor to setup session for every request"""

        self._cleanup()
        self._load()

        try:
            return handler()
        finally:
            self._save()

    def _load(self):
        """Load the session from the store, by the id from cookie"""
        cookie_name = self._config.cookie_name
        self.session_id = web.cookies().get(cookie_name)

        # protection against session_id tampering
        if self.session_id and not self._valid_session_id(self.session_id):
            self.session_id = None

        self._check_expiry()
        if self.session_id:
            d = self.store[self.session_id]
            self.update(d)
            self._validate_ip()

        if not self.session_id:
            self.session_id = self._generate_session_id()

            if self._initializer:
                if isinstance(self._initializer, dict):
                    self.update(deepcopy(self._initializer))
                elif hasattr(self._initializer, "__call__"):
                    self._initializer()

        self.ip = web.ctx.ip

    def _check_expiry(self):
        # check for expiry
        if self.session_id and self.session_id not in self.store:
            if self._config.ignore_expiry:
                self.session_id = None
            else:
                return self.expired()

    def _validate_ip(self):
        # check for change of IP
        if self.session_id and self.get("ip", None) != web.ctx.ip:
            if not self._config.ignore_change_ip:
                return self.expired()

    def _save(self):
        current_values = dict(self._data)
        del current_values["session_id"]
        del current_values["ip"]

        if not self.get("_killed") and current_values != self._initializer:
            self._setcookie(self.session_id)
            self.store[self.session_id] = dict(self._data)
        else:
            if web.cookies().get(self._config.cookie_name):
                self._setcookie(
                    self.session_id,
                    expires=self._config.timeout,
                    samesite=self._config.get("samesite"),
                )

    def _setcookie(self, session_id, expires="", **kw):
        cookie_name = self._config.cookie_name
        cookie_domain = self._config.cookie_domain
        cookie_path = self._config.cookie_path
        httponly = self._config.httponly
        secure = self._config.secure
        samesite = kw.get("samesite", self._config.get("samesite", None))
        web.setcookie(
            cookie_name,
            session_id,
            expires=expires or self._config.timeout,
            domain=cookie_domain,
            httponly=httponly,
            secure=secure,
            path=cookie_path,
            samesite=samesite,
        )

    def _generate_session_id(self):
        """Generate a random id for session"""

        while True:
            rand = os.urandom(16)
            now = time.time()
            secret_key = self._config.secret_key

            hashable = "%s%s%s%s" % (rand, now, utils.safestr(web.ctx.ip), secret_key)
            # TODO maybe a better way to deal with this, without using an if-statement
            session_id = sha1(hashable if PY2 else hashable.encode("utf-8"))
            session_id = session_id.hexdigest()
            if session_id not in self.store:
                break
        return session_id

    def _valid_session_id(self, session_id):
        rx = utils.re_compile("^[0-9a-fA-F]+$")
        return rx.match(session_id)

    def _cleanup(self):
        """Cleanup the stored sessions"""
        current_time = time.time()
        timeout = self._config.timeout
        if current_time - self._last_cleanup_time > timeout:
            self.store.cleanup(timeout)
            self._last_cleanup_time = current_time

    def expired(self):
        """Called when an expired session is atime"""
        self._killed = True
        self._save()
        raise SessionExpired(self._config.expired_message)

    def kill(self):
        """Kill the session, make it no longer available"""
        del self.store[self.session_id]
        self._killed = True


class Store:
    """Base class for session stores"""

    def __contains__(self, key):
        raise NotImplementedError()

    def __getitem__(self, key):
        raise NotImplementedError()

    def __setitem__(self, key, value):
        raise NotImplementedError()

    def cleanup(self, timeout):
        """removes all the expired sessions"""
        raise NotImplementedError()

    def encode(self, session_dict):
        """encodes session dict as a string"""
        pickled = pickle.dumps(session_dict)
        return base64.encodestring(pickled)

    def decode(self, session_data):
        """decodes the data to get back the session dict """
        pickled = base64.decodestring(session_data)
        return pickle.loads(pickled)


class DiskStore(Store):
    """
    Store for saving a session on disk.

        >>> import tempfile
        >>> root = tempfile.mkdtemp()
        >>> s = DiskStore(root)
        >>> s['a'] = 'foo'
        >>> s['a']
        'foo'
        >>> time.sleep(0.01)
        >>> s.cleanup(0.01)
        >>> s['a']
        Traceback (most recent call last):
            ...
        KeyError: 'a'
    """

    def __init__(self, root):
        # if the storage root doesn't exists, create it.
        if not os.path.exists(root):
            os.makedirs(os.path.abspath(root))
        self.root = root

    def _get_path(self, key):
        if os.path.sep in key:
            raise ValueError("Bad key: %s" % repr(key))
        return os.path.join(self.root, key)

    def __contains__(self, key):
        path = self._get_path(key)
        return os.path.exists(path)

    def __getitem__(self, key):
        path = self._get_path(key)

        if os.path.exists(path):
            with open(path, "rb") as fh:
                pickled = fh.read()
            return self.decode(pickled)
        else:
            raise KeyError(key)

    def __setitem__(self, key, value):
        path = self._get_path(key)
        pickled = self.encode(value)
        try:
            tname = path + "." + threading.current_thread().getName()
            f = open(tname, "wb")
            try:
                f.write(pickled)
            finally:
                f.close()
                os.rename(tname, path)  # atomary operation
        except IOError:
            pass

    def __delitem__(self, key):
        path = self._get_path(key)
        if os.path.exists(path):
            os.remove(path)

    def cleanup(self, timeout):
        now = time.time()
        for f in os.listdir(self.root):
            path = self._get_path(f)
            atime = os.stat(path).st_atime
            if now - atime > timeout:
                os.remove(path)


class DBStore(Store):
    """Store for saving a session in database
    Needs a table with the following columns:

        session_id CHAR(128) UNIQUE NOT NULL,
        atime DATETIME NOT NULL default current_timestamp,
        data TEXT
    """

    def __init__(self, db, table_name):
        self.db = db
        self.table = table_name

    def __contains__(self, key):
        data = self.db.select(self.table, where="session_id=$key", vars=locals())
        return bool(list(data))

    def __getitem__(self, key):
        now = datetime.datetime.now()
        try:
            s = self.db.select(self.table, where="session_id=$key", vars=locals())[0]
            self.db.update(
                self.table, where="session_id=$key", atime=now, vars=locals()
            )
        except IndexError:
            raise KeyError(key)
        else:
            return self.decode(s.data)

    def __setitem__(self, key, value):
        pickled = self.encode(value)
        now = datetime.datetime.now()
        if key in self:
            self.db.update(
                self.table,
                where="session_id=$key",
                data=pickled,
                atime=now,
                vars=locals(),
            )
        else:
            self.db.insert(self.table, False, session_id=key, atime=now, data=pickled)

    def __delitem__(self, key):
        self.db.delete(self.table, where="session_id=$key", vars=locals())

    def cleanup(self, timeout):
        timeout = datetime.timedelta(
            timeout / (24.0 * 60 * 60)
        )  # timedelta takes numdays as arg
        last_allowed_time = datetime.datetime.now() - timeout
        self.db.delete(self.table, where="$last_allowed_time > atime", vars=locals())


class ShelfStore:
    """Store for saving session using `shelve` module.

        import shelve
        store = ShelfStore(shelve.open('session.shelf'))

    XXX: is shelve thread-safe?
    """

    def __init__(self, shelf):
        self.shelf = shelf

    def __contains__(self, key):
        return key in self.shelf

    def __getitem__(self, key):
        atime, v = self.shelf[key]
        self[key] = v  # update atime
        return v

    def __setitem__(self, key, value):
        self.shelf[key] = time.time(), value

    def __delitem__(self, key):
        try:
            del self.shelf[key]
        except KeyError:
            pass

    def cleanup(self, timeout):
        now = time.time()
        for k in self.shelf:
            atime, v = self.shelf[k]
            if now - atime > timeout:
                del self[k]


if __name__ == "__main__":
    import doctest

    doctest.testmod()
