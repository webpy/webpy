'''
Session module
(part of web.py)
'''


import time
import random

import errno
import os
import re
import glob

try:                # Python 2.5
    from hashlib import sha512 as sha
except ImportError:
    import sha

try:                # faster C-implementation
    import cPickle as pickle
except ImportError:
    import pickle

import web


session_parameters = web.utils.Storage({
    'cookie_name': 'webpy',
    # name of the cookie which will transfer the session id
    'cookie_domain': None,
    # cookie domain for the setcookie() when setting session id cookie

    'timeout': 600,
    'max_age': 24 * 60 * 60,

    'id_seed': 'web.py',
    'regenerate_id': True, # on every request regenerate id and set again cookie
    'generator': False,    # if False, use default generator

    'ignore_expiration': False,
    'ignore_old_age': True,
    'ignore_change_ip': True,
    # if the pair ( id, ip ) doesn't match the db, then fail/raise exception/...

    'handler': 'db'
})

handler_parameters = web.utils.Storage({
    'file_dir': '/tmp',        # storage dir
    'file_prefix': 'sess',     # session file prefix
    'db_table': 'session_data' # table name
})


def sha_hash(seed):
    '''return SHA hash of seed; wrapper around different modules'''
    try:        # >= Python 2.5
        return sha(seed).hexdigest()
    except TypeError:
        return sha.new(seed).hexdigest()


class Session(web.utils.Storage):
    '''main session object
        main instance variables
        _handler
        _id
        _data - internal Storage object'''

    def __init__(self):
        web.utils.Storage.__init__(self)
        self._id = False
        self._old_id = False
        self._data = {}
        self._handler = None

    def __getattr__(self, key):
        if key in ('_id', '_old_id', '_data', '_handler'):
            return object.__getattribute__(self, key)

        try:
            return self._data[key]
        except KeyError, k:
            raise AttributeError, k

    def __setattr__(self, key, value):
        if key in ('_id', '_old_id', '_data', '_handler'):
            object.__setattr__(self, key, value)
        else:
            self._data[key] = value

    def __delattr__(self, key):
        if key in ('_id', '_old_id', '_data', '_handler'):
            #object.__delattr__(self, key, value)
            return

        try:
            del self._data[key]
        except KeyError, k:
            raise AttributeError, k

    def __getitem__(self, key):
        return self._data[key]

    def __setitem__(self, key, value):
        self._data[key] = value

    def __delitem__(self, key):
        del self._data[key]

    def __repr__(self):
        return '<Session {\'id\': ' + str(self._id) + ', \'data\': ' + str(self._data) + '}>'

    # public methods
    def start(self):
        '''starts the session: creates handler object, sets generator,
        regenerates id, sets cookies, calls _identity, _verify, _generate_id'''
        handler = {'db': DBHandler, 'file': FileHandler}
        self._handler = handler[web.config.session_parameters.handler]()

        self._identify()

        if self._id:
            item = self._retreive()
            if self._verify(item):
                self._data = item.data

        if web.config.session_parameters.regenerate_id:
            self._old_id = self._id
            self._id = self._generate_id()

        if not self._id:
            self._id = self._generate_id()

    def get_id(self):
        '''returns current session id'''
        return self._id

    def cleanup(self):
        '''cleans expired sessions'''
        self._handler.clean(web.config.session_parameters.timeout)

    def save(self):
        '''save session data'''
        self._store()

        web.setcookie(web.config.session_parameters.cookie_name,
            self._id,
            web.config.session_parameters.timeout,
            web.config.session_parameters.cookie_domain)

    def destroy(self):
        '''removes session (including cookies)'''
        self._remove()
        self._id = False
        self._old_id = False
        web.setcookie(web.config.session_parameters.cookie_name,
            '',
            (-1) * web.config.session_parameters.timeout,
            web.config.session_parameters.cookie_domain)

    # private methods
    def _generate_id(self):
        '''generates session id
            using implicit session id generator or user supplied generator'''
        if web.config.session_parameters.generator:
            return web.config.session_parameters.generator()

        seed = '%s %s %s %s' % (random.random(),
                time.time(),
                web.ctx.ip,
                web.config.session_parameters.id_seed)
        return sha_hash(seed)

    def _identify(self):
        '''identifies session id (through cookies)'''
        try:
            self._id = web.cookies().__getattr__(web.config.session_parameters.cookie_name)
        except (AttributeError, KeyError):
            self._id = False

    def _verify(self, item):
        '''verifies with retreived data from handler object'''
        try:
            self._id = item.id
        except AttributeError:
            self._id = False
            return False

        now = time.time()

        if not web.config.session_parameters.ignore_expiration    \
            and now - item.touched >= web.config.session_parameters.timeout:
            self._remove()
            self._id = False
            return False

        if not web.config.session_parameters.ignore_change_ip    \
            and web.ctx.ip != item.ip.strip():
            self._remove()
            self._id = False
            return False

        if not web.config.session_parameters.ignore_old_age    \
            and now - item.created >= web.config.session_parameters.max_age:
            self._remove()
            self._id = False
            return False

        return True

    def _store(self):
        '''stores session data (wrapper around handler object)'''
        self._handler.store(self._id, web.ctx.ip, self._data, self._old_id)

    def _retreive(self):
        '''retreive session data (wrapper around handler object)'''
        return self._handler.retreive(self._id)

    def _remove(self):
        '''removes session data (wrapper around handler object)'''
        self._handler.remove(self._id)

        if self._old_id:
            self._handler.remove(self._old_id)


class Handler:
    '''abstract handler class'''
    def __init__(self):
        pass

    def store(self, id_, client_ip, data, old_id=False):
        '''takes
            client_ip - client ip
            id_ - string
            data - Storage
            old_id - if the id regenerates after every request'''
        pass

    def retreive(self, id_):
        '''returns Storage'''
        pass

    def remove(self, id_):
        '''removes session'''
        pass

    def clean(self, timeout):
        '''removes all expired sessions'''
        pass


class DBHandler(Handler):
    '''needs an table:
    CREATE TABLE session_data (
        id CHAR(129) UNIQUE NOT NULL,
        ip CHAR(16) NOT NULL,
        created int NOT NULL,
        touched int NOT NULL,
        data TEXT
    );'''

    def store(self, id_, client_ip, data, old_id=False):
        '''takes
            client_ip - client ip
            id_ - string
            data - Storage
            old_id - if the id regenerates after every request'''
        do_insert = True

        if not old_id:
            old_id = id_

        if len(list(web.select(web.config.handler_parameters.db_table,
                vars={'id': old_id},
                what='id',
                where='id = $id'))) == 1:
            do_insert = False

        web.transact()

        now = int(time.time())
        try:
            if do_insert:
                web.db.insert(web.config.handler_parameters.db_table,
                    seqname=False, id=id_, ip=client_ip, touched=now,
                    created=now, data=pickle.dumps(data, 0))
            else:
                web.update(web.config.handler_parameters.db_table,
                    where='id = $old_id',
                    vars={'old_id': old_id},
                    id=id_, ip=client_ip, touched=now,
                    data=pickle.dumps(data, 0))
            web.commit()

        except Exception, inst:
            web.rollback()
            raise inst

    def remove(self, id_):
        '''removes session'''
        web.transact()
        try:
            web.delete(web.config.handler_parameters.db_table,
                    where='id = $id', vars={'id': id_})
            web.commit()

        except Exception, inst:
            web.rollback()
            raise inst

    def retreive(self, id_):
        '''returns Storage'''
        try:
            tmp = web.select(web.config.handler_parameters.db_table,
                    what='*',
                    vars={
                            'id': id_,
                            'timeout': web.config.session_parameters.timeout
                        },
                    where='id = $id')

        except Exception, inst:
            raise inst

        try:
            result = tmp[0]
            result.data = pickle.loads(result.data.encode('ascii'))
            return result

        except IndexError:
            return web.Storage()

    def clean(self, timeout):
        '''removes all expired sessions'''
        web.transact()

        try:
            web.delete(web.config.handler_parameters.db_table,
                where='($now - touched) >= $timeout',
                vars={'timeout': timeout, 'now': int(time.time())})
            web.commit()

        except Exception, inst:
            web.rollback()
            raise inst


class FileHandler(Handler):
    '''needs dir with rw permission to create session files'''
    def __init__(self):
        '''normalizes file_dir path'''
        Handler.__init__(self)
        self._path = os.path.abspath(web.config.handler_parameters.file_dir)

    def store(self, id_, client_ip, data, old_id=False):
        '''takes
            client_ip - client ip
            id_ - string
            data - Storage
            old_id - if the id regenerates after every request'''
        created = False
        self._acquire_lock(id_)

        if old_id:
            self._acquire_lock(old_id)

            try:
                file_desc = file(self._session_file(old_id), 'rb')
            except (IOError, OSError), inst:
                if inst.errno != errno.ENOENT:
                    self._release_lock(old_id)
                    self._release_lock(id_)
                    raise inst
            else:
                result = pickle.load(file_desc)
                created = result.created
                file_desc.close()
                os.unlink(self._session_file(old_id))

            self._release_lock(old_id)

        if not created:
            created = int(time.time())

        file_desc = file(self._session_file(id_), 'wb')
        box = web.Storage({
                'id': id_,
                'ip': client_ip,
                'data': data,
                'created': created
            })

        pickle.dump(box, file_desc, 0)
        file_desc.close()

        self._release_lock(id_)

    def retreive(self, id_):
        '''returns Storage'''
        self._acquire_lock(id_)

        try:
            file_desc = file(self._session_file(id_), 'rb')
        except (IOError, OSError), inst:
            if inst.errno != errno.ENOENT:
                raise inst

            result = web.Storage()
        else:
            result = pickle.load(file_desc)
            result.touched = os.fstat(file_desc.fileno()).st_mtime
            file_desc.close()

        self._release_lock(id_)
        return result

    def remove(self, id_):
        '''removes session'''
        self._acquire_lock(id_)

        try:
            os.unlink(self._session_file(id_))
        except (IOError, OSError), inst:
            if inst.errno != errno.ENOENT:
                raise inst

        self._release_lock(id_)

    def clean(self, timeout):
        '''removes all expired sessions'''
        files = glob.glob('%s/%s*' % (self._path,
            web.config.handler_parameters.file_prefix))
        patern = '%s/%s(?P<id>[0-9a-f]{40,128})(?!.lock)' % (self._path,
            web.config.handler_parameters.file_prefix)

        compiled = re.compile(patern)
        now = time.time()

        for file_name in files:
            try:
                id_ = compiled.match(file_name).group('id')
            except AttributeError:
                continue

            if self._acquire_lock(id_, False):
                if now - os.path.getmtime(file_name) > timeout:
                    os.unlink(file_name)

                self._release_lock(id_)

    # private methods
    def _session_file(self, id_):
        '''returns session file name'''
        return '%s/%s%s' % (self._path, web.config.handler_parameters.file_prefix, id_)

    def _lock_file(self, id_):
        '''returns session lock file name'''
        return '%s.lock' % self._session_file(id_)

    def _acquire_lock(self, id_, blocking=True):
        '''create lock file
            if blocking is False, don't loop'''
        file_name = self._lock_file(id_)

        while True:
            try:
                file_desc = os.open(file_name, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
            except (IOError, OSError), inst:
                if inst.errno != errno.EEXIST:
                    raise inst
            else:
                os.close(file_desc)
                break

            try:
                now = time.time()
                if now - os.path.getmtime(file_name) > 60:
                    os.unlink(file_name)

            except (IOError, OSError), inst:
                if inst.errno != errno.ENOENT:
                    raise inst

            if not blocking:
                return False

            time.sleep(0.1)

        return True

    def _release_lock(self, id_):
        '''unlink lock file'''
        try:
            os.unlink(self._lock_file(id_))
        except (IOError, OSError), inst:
            if inst.errno != errno.ENOENT:
                raise inst


def _load_session():
    '''loadhook function
        create session object, sets parameters'''
    web.webapi.config.session_parameters = session_parameters
    web.webapi.config.handler_parameters = handler_parameters
    web.webapi.ctx.session = Session()


web.webapi.loadhooks['session'] = _load_session

