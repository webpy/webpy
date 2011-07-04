"""Python 2.3 compatabilty"""
import threading

class threadlocal(object):
    """Implementation of threading.local for python2.3.
    """
    def __getattribute__(self, name):
        if name == "__dict__":
            return threadlocal._getd(self)
        else:
            try:
                return object.__getattribute__(self, name)
            except AttributeError:
                try:
                    return self.__dict__[name]
                except KeyError:
                    raise AttributeError, name
            
    def __setattr__(self, name, value):
        self.__dict__[name] = value
        
    def __delattr__(self, name):
        try:
            del self.__dict__[name]
        except KeyError:
            raise AttributeError, name
    
    def _getd(self):
        t = threading.currentThread()
        if not hasattr(t, '_d'):
            # using __dict__ of thread as thread local storage
            t._d = {}
        
        _id = id(self)
        # there could be multiple instances of threadlocal.
        # use id(self) as key
        if _id not in t._d:
            t._d[_id] = {}
        return t._d[_id]
        
if __name__ == '__main__':
     d = threadlocal()
     d.x = 1
     print d.__dict__
     print d.x
     