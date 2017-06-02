"""
Interceptor support
e.g.
if __name__ == '__main__':
    class I(object):

        def before(self, context, name):
            print "I'm before in I"
            print context
            print name
            context.replace_arg('sex', '2')
            context["before"] = "hello"
            return Invocation.SUCCESS

        def after(self, context, name):
            print "I'm after in I"
            print context
            print name
            context["after"] = "world1"

    class O(object):

        def before(self, context, sex):
            print "I'm before in O"
            print context
            print sex
            context["before"] = "hello1"
            return Invocation.SUCCESS

        def after(self, context, name):
            print "I'm after in O"
            print context
            print name
            context["after"] = "world"

    class C(object):

        def before(self, context, name):
            print "I'm before in C"
            print context
            print name
            context["before"] = "hello2"
            context.replace_arg('name', 'quinn')
            return Invocation.SUCCESS

        def after(self, context, name):
            print "I'm after in C"
            print context
            print name
            context["after"] = "world2"
            context.response = "Response has bean replaced."

    class T(object):
        @interceptor(I, O, C)
        def test(self, name, sex):
            print "aaa" + name + sex
            return "I'm test"


    print T().test("bbb", '1')
"""

import inspect


def enum(**enums):
    return type('Enum', (), enums)

# The return type of Interceptors
Invocation = enum(SUCCESS=True, FAILED=False, SKIP="SKIP")


def interceptor(*classes):
    """
    Use decorator to implement interceptor.
    Every interceptor has two methods, One method is before that execute before the controller;
    the other method is after that execute after the controller.
    Each method(before or after) can accept the parameters that accepted by controller,they
    must define the parameter that named 'context' at first,and framework should pass all these
    values for you automatically.
    Also you can change the parameter of the controller with the method 'replace_arg' in context,
    and you can use 'context.response' to change the result of the controller.
    :param classes: interceptor classes
    :return:
    """
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