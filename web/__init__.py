"""web.py: makes web apps (http://webpy.org)"""

import sys

if '__all__' not in sys.modules[__name__].__dict__:
    __version__ = "0.35"
    __author__ = [
        "Aaron Swartz <me@aaronsw.com>",
        "Anand Chitipothu <anandology@gmail.com>"
    ]
    __license__ = "public domain"
    __contributors__ = "see http://webpy.org/changes"

    # import mapping to objects in other modules
    all_by_module = {
        'db':      ["UnknownParamstyle", "UnknownDB", "TransactionError",
                    "sqllist", "sqlors", "reparam", "sqlquote",
                    "SQLQuery", "SQLParam", "sqlparam",
                    "SQLLiteral", "sqlliteral", "database", 'DB'],
        'net':     ["validipaddr", "validipport", "validip", "validaddr",
                    "urlquote", "httpdate", "parsehttpdate",
                    "htmlquote", "htmlunquote", "websafe"],
        'http':    ["expires", "lastmodified", "prefixurl", "modified",
                    "changequery", "url", "profiler"],
        'httpserver':   ['runsimple'],
        'debugerror':   ["debugerror", "djangoerror", "emailerrors"],
        'browser': ["BrowserError", "Browser", "AppBrowser", "AppHandler"]
    }

    # modules that should be imported when accessed as attributes of werkzeug
    attribute_modules = ('db', 'net', 'http', 'httpserver', 'debugerror',
                         'template', 'form')

    object_origins = {}
    for module, items in all_by_module.iteritems():
        for item in items:
            object_origins[item] = module

    from types import ModuleType

    class module(ModuleType):
        """Automatically import objects from the modules."""
        __lazy_names__ = object_origins, all_by_module, attribute_modules

        def __init__(self, module):
            ModuleType.__init__(self, module.__name__)
            d = module.__dict__
            for name,value in d.iteritems():
                if name.startswith('__'):
                    setattr(self, name, value)
            for name in ('wsgi', 'utils', 'webapi', 'application'):
                module = '%s.%s' % (self.__name__, name)
                module = __import__(module, None, None, [''])
                setattr(self, name, module)
                for name in module.__all__:
                    setattr(self, name, getattr(module, name))
            for name in ('session',):
                module = '%s.%s' % (self.__name__, name)
                setattr(self, name, __import__(module, None, None, ['']))
            self.__all__ = []
            self.__all__.extend(self.__dict__)
            self.__all__.extend(object_origins)
            self.__all__.extend(attribute_modules)

        def __getattr__(self, name):
            nm_mapping = self.__lazy_names__[0]
            if name in nm_mapping:
                module = '%s.%s' % (self.__name__, nm_mapping[name])
                module = __import__(module, None, None, [name])
                for extra_name in self.__lazy_names__[1][nm_mapping[name]]:
                    setattr(self, extra_name, getattr(module, extra_name))
            elif name in self.__lazy_names__[2]:
                module = '%s.%s' % (self.__name__, name)
                setattr(self, name, __import__(module, None, None, ['']))
            elif name == 'openid':
                try: self.openid = __import__(self.__name__+'.webopenid')
                except ImportError: pass
            return self.__class__.__bases__[0].__getattribute__(self, name)

    sys.modules[__name__] = module(sys.modules[__name__])

del sys
