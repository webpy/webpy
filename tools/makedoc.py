import sys
sys.path.insert(0, '..')
import web
import inspect

modules = [
    'web.application', 
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

def process_func(name, f):
    print qstart + name + inspect.formatargspec(*inspect.getargspec(f)) + qend + ': '
    print inspect.getdoc(f)
    print
    
def process_class(name, cls):
    bases = [b.__name__ for b in cls.__bases__]
    if bases:
        name = name + '(' + ",".join(bases) + ')'
        
    print qstart + 'class ' + name + qend + ': '
    print inspect.getdoc(cls)
    print

def process_storage(name, d):
    print qstart + name + qend + ': '
    print d['__doc__']
    
def process_mod(name, mod):
    print '<a name="%s"></a>' % name
    print '##', name
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
    print '    .content {margin-left: 20px;}'
    print '    .head {margin-left: -20px;}'
    print '    h2 {margin-left: -20px;}'
    print '</style>'
    print

def main():
    for name in modules:
        print '* <a href="#%s">%s</a>' %(name, name)
    print
    
    for name in modules:
        mod = __import__(name, {}, {}, 'x')
        process_mod(name, mod)

    print_css()

if __name__ == '__main__':
    main()
