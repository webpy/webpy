import sys
sys.path.insert(0, '..')
import web
import inspect

modules = [
    'web.application',
    'web.contrib.template',
    'web.db',
    'web.debugerror',
    'web.form',
    'web.http',
    'web.httpserver',
    'web.net',
    'web.session',
    'web.template',
    'web.utils',
    'web.webapi',
    'web.webopenid',
    'web.wsgi'
]


qstart = '<code class="head">'
qend = '</code>'

func_start = '<div style="margin-left:%dpx">'
func_end = '</div>'

tab_width = 20 #width for tabs in px

def process_func(name, f, tablevel=1):
    if tablevel != 1: print func_start % (tablevel * tab_width)
    sys.stdout.write(qstart + name + inspect.formatargspec(*inspect.getargspec(f)) + qend)
    doc = inspect.getdoc(f)
    if not doc is None:
        print ": "
        print doc
    print
    if tablevel != 1: print func_end
    print

def process_class(name, cls):
    bases = [b.__name__ for b in cls.__bases__]
    if bases:
        name = name + '(' + ",".join(bases) + ')'
    
    sys.stdout.write(qstart + 'class ' + name + qend)
    doc = inspect.getdoc(cls)
    if not doc is None:
        print ': '
        print inspect.getdoc(cls)
    print
    methods = [(m, getattr(cls, m)) for m in dir(cls)
				if not m.startswith('_') and inspect.ismethod(getattr(cls, m))]
	#Possible todo: see if code is faster with the get method in the rendering
	#loop.
    for m in methods: process_func(m[0], m[1], 2)

def process_storage(name, d):
    print qstart + name + qend + ': '
    print d['__doc__']

def process_mod(name, mod):
    print '<a name="%s"></a>' % name
    print '##', name
    print '<a href="#top">Back to top</a>'
    print
    
    all = getattr(mod, '__all__', None)
    
    for k, v in inspect.getmembers(mod):
        if k.startswith('_'):
            continue
        
        if inspect.getmodule(v) == mod:
            if inspect.isclass(v):
                process_class(k, v)
            elif inspect.isfunction(v):
                process_func(k, v)
        
        # specical case for generating docs for web.ctx and web.config
        elif all and k in all and isinstance(v, (web.storage, web.threadeddict)) and hasattr(v, '__doc__'):
            process_storage(k, v)

def print_css():
    print
    print '<style type="text/css">'
    print '    #content {margin-left: %dpx;}'% (tab_width)
    print '    .head {margin-left: -20px;}'
    print '    h2 {margin-left: -20px;}'
    print '</style>'
    print

def main():
    print '<a name="top"></a>'
    for name in modules:
        print '* <a href="#%s">%s</a>' %(name, name)
    print
    
    for name in modules:
        mod = __import__(name, {}, {}, 'x')
        process_mod(name, mod)
    
    print_css()

if __name__ == '__main__':
    main()