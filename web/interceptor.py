__author__ = 'quinn'

import inspect


def enum(**enums):
    return type('Enum', (), enums)

Invocation = enum(SUCCESS=True, FAILED=False, SKIP="SKIP")


def interceptor(*classes):
    def decorator(func):
        def _get_params(fun, named):
            params = set(inspect.getargspec(fun)[0])
            return dict([(k, named.get(k)) for k in params if k in named and k != "self"])

        def _wrapper(*args, **kw):
            _interceptors = [cls() for cls in classes]
            call_args = inspect.getcallargs(func, *args, **kw)
            self_arg = ()
            try:
                self_arg = [call_args.pop("self")]
            except Exception:
                pass
            context = Context(*self_arg, **call_args)
            try:
                index = -1
                for inter in _interceptors:
                    named_params = _get_params(inter.before, context.call_args)
                    before = inter.before(context, **named_params)
                    if not before:
                        return None
                    elif before == Invocation.SKIP:
                        index = _interceptors.index(inter)
                        break
                if index > -1:
                    _interceptors = _interceptors[:index + 1]
            except Exception, e:
                raise e
            context.response = func(*context.self_arg, **context.call_args)
            try:
                _interceptors.reverse()
                for inter in _interceptors:
                    named_params = _get_params(inter.after, context.call_args)
                    inter.after(context, **named_params)
            except Exception, e:
                raise e
            return context.response
        return _wrapper
    return decorator


class Context(dict):

    def __init__(self, *self_arg, **call_args):
        if self_arg is None:
            self_arg = ()
        self._self_arg = (s for s in self_arg)
        if call_args is None:
            call_args = {}
        self._call_args = dict([(key, call_args[key]) for key in call_args.keys()])
        self._response = None

    @property
    def self_arg(self):
        return self._self_arg

    @property
    def call_args(self):
        return self._call_args

    def replace_arg(self, name, value):
        if name in self._call_args:
            self._call_args[name] = value
        else:
            raise KeyError('There is no argument "%s" in the intercepted function' % name)

    @property
    def response(self):
        return self._response

    @response.setter
    def response(self, resp=None):
        if resp:
            self._response = resp