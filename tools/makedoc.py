"""
Outputs web.py docs as html
version 2.0: documents all code, and indents nicely.
By Colin Rothwell (TheBoff)
"""
import sys
import inspect
import markdown
sys.path.insert(0, '..')

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

item_start = '<code class="%s">'
item_end = '</code>'

indent_amount = 30

doc_these = ( #These are the types of object that should be docced
    'module',
    'classobj',
    'instancemethod',
    'function',
    'type',
    'property',    
)

not_these_names = ( #Any particular object names that shouldn't be doced
    'fget',
    'fset',
    'fdel',
    'storage', #These stop the lower case versions getting docced
    'memoize',
    'iterbetter',
    'capturesstdout',
    'profile',
    'threadeddict',
    'd', #Don't know what this is, but only only conclude it shouldn't be doc'd
)

css = '''
<style type="text/css">
.module {
    font-size: 130%;
    font-weight: bold;
}

.function, .class, .type {
    font-size: 120%;
    font-weight: bold;
}

.method, .property {
    font-size: 115%;
    font-weight: bold;
}

.ts {
    font-size: small;
    font-weight: lighter;
    color: grey;
}

#contents_link {
    position: fixed;
    top: 0;
    right: 0;
    padding: 5px;
    background: rgba(255, 255, 255, 0.5);
}

#contents_link a:hover {
    font-weight: bold;
}
</style>
'''


indent_start = '<div style="margin-left:%dpx">'
indent_end = '</div>'

header = '''
<div id="contents_link">
<a href="#top">Back to contents</a>
</div>
'''

def type_string(ob):
    return str(type(ob)).split("'")[1]
    
def ts_css(text):
    """applies nice css to the type string"""
    return '<span class="ts">%s</span>' % text
    
def arg_string(func):
    """Returns a nice argstring for a function or method"""
    return inspect.formatargspec(*inspect.getargspec(func))

def recurse_over(ob, name, indent_level=0):
    ts = type_string(ob)    
    if not ts in doc_these: return #stos what shouldn't be docced getting docced
    if indent_level > 0 and ts == 'module': return #Stops it getting into the stdlib    
    if name in not_these_names: return #Stops things we don't want getting docced
    
    indent = indent_level * indent_amount #Indents nicely
    ds_indent = indent + (indent_amount / 2)
    if indent_level > 0: print indent_start % indent
    
    argstr = ''
    if ts.endswith(('function', 'method')):
        argstr = arg_string(ob)
    elif ts == 'classobj' or ts == 'type':
        if ts == 'classobj': ts = 'class'
        if hasattr(ob, '__init__'):
            if type_string(ob.__init__) == 'instancemethod':
                argstr = arg_string(ob.__init__)
        else:
            argstr = '(self)'
    if ts == 'instancemethod': ts = 'method' #looks much nicer
    
    ds = inspect.getdoc(ob)
    if ds is None: ds = ''
    ds = markdown.Markdown(ds)
    
    mlink = '<a name="%s">' % name if ts == 'module' else '' 
    mend = '</a>' if ts == 'module' else ''
                
    print ''.join(('<p>', ts_css(ts), item_start % ts, ' ', mlink, name, argstr,
            mend, item_end, '<br />'))
    print ''.join((indent_start % ds_indent, ds, indent_end, '</p>'))
    #Although ''.join looks wierd, it's alot faster is string addition    
    members = ''
    
    if hasattr(ob, '__all__'): members = ob.__all__
    else: members = [item for item in dir(ob) if not item.startswith('_')] 
    
    if not 'im_class' in members:    
        for name in members:
            recurse_over(getattr(ob, name), name, indent_level + 1)
    if indent_level > 0: print indent_end

def main():
    print '<div>' #Stops markdown vandalising my html.
    print css
    print header
    print '<ul>'
    for name in modules:
        print '<li><a href="#%(name)s">%(name)s</a></li>' % dict(name=name)
    print '</ul>' 
    for name in modules:
        mod = __import__(name, {}, {}, 'x')
        recurse_over(mod, name)
    print '</div>'
        
if __name__ == '__main__':
    main()