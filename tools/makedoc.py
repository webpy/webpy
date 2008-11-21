import sys
sys.path.insert(0, '..')
import web
import inspect
import cStringIO
import markdown

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

indent = '<indent>' #This gets around the markdown bug of not working
uindent = '</indent>'#between divs. At the cost of not-strictly-legal html.

tab_width = 20 #width for tabs in px

def process_func(name, f, tablevel=1):
    sys.stdout.write(qstart + name + inspect.formatargspec(*inspect.getargspec(f)) + qend)
    doc = inspect.getdoc(f)
    if not doc is None:
        print ": "
        print doc
    print
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
    print indent
    for m in methods: process_func(m[0], m[1], 2)
    print uindent

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
    print '    span * {margin-left: inherits;}'
    print '</style>'
    print

def post_process(text):
    """
    Processes the text into a properly formatted wiki page.
    """
    text = text.replace(indent, '<div style="margin-left:40px;"')
    text = text.replace(uindent, '</div>')
    return text

def main():
    data = cStringIO.StringIO()
    sys.stdout = data #This is needed for post-processing
    print '<a name="top"></a>'
    print
    for name in modules:
        print '* <a href="#%s">%s</a>' %(name, name)
    print
    
    for name in modules:
        mod = __import__(name, {}, {}, 'x')
        process_mod(name, mod)
    
    print_css()
    text = markdown.Markdown(data.getvalue())
    sys.stdout = sys.__stdout__
    print post_process(text)

if __name__ == '__main__':
    main()