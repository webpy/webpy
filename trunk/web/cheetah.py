"""
Cheetah API
(from web.py)
"""

__all__ = ["render"]

import re, urlparse, pprint, traceback, sys
from Cheetah.Compiler import Compiler
from Cheetah.Filters import Filter
from utils import re_compile, memoize, dictadd
from net import htmlquote, websafe
from webapi import ctx, header, output, input, cookies

def upvars(level=2):
    """Guido van Rossum sez: don't use this function."""
    return dictadd(
      sys._getframe(level).f_globals,
      sys._getframe(level).f_locals)

r_include = re_compile(r'(?!\\)#include \"(.*?)\"($|#)', re.M)
def __compiletemplate(template, base=None, isString=False):
    if isString: 
        text = template
    else: 
        text = open('templates/'+template).read()
    # implement #include at compile-time
    def do_include(match):
        text = open('templates/'+match.groups()[0]).read()
        return text
    while r_include.findall(text): 
        text = r_include.sub(do_include, text)

    execspace = _compiletemplate.bases.copy()
    tmpl_compiler = Compiler(source=text, mainClassName='GenTemplate')
    tmpl_compiler.addImportedVarNames(execspace.keys())
    exec str(tmpl_compiler) in execspace
    if base: 
        _compiletemplate.bases[base] = execspace['GenTemplate']

    return execspace['GenTemplate']

_compiletemplate = memoize(__compiletemplate)
_compiletemplate.bases = {}

def render(template, terms=None, asTemplate=False, base=None, 
           isString=False):
    """
    Renders a template, caching where it can.
    
    `template` is the name of a file containing the a template in
    the `templates/` folder, unless `isString`, in which case it's the 
    template itself.

    `terms` is a dictionary used to fill the template. If it's None, then
    the caller's local variables are used instead, plus context, if it's not 
    already set, is set to `context`.

    If asTemplate is False, it `output`s the template directly. Otherwise,
    it returns the template object.

    If the template is a potential base template (that is, something other templates)
    can extend, then base should be a string with the name of the template. The
    template will be cached and made available for future calls to `render`.

    Requires [Cheetah](http://cheetahtemplate.org/).
    """
    # terms=['var1', 'var2'] means grab those variables
    if isinstance(terms, list):
        new = {}
        old = upvars()
        for k in terms: 
            new[k] = old[k]
        terms = new
    # default: grab all locals
    elif terms is None:
        terms = {'context': ctx, 'ctx':ctx}
        terms.update(sys._getframe(1).f_locals)
    # terms=d means use d as the searchList
    if not isinstance(terms, tuple): 
        terms = (terms,)
    
    if not isString and template.endswith('.html'): 
        header('Content-Type','text/html; charset=utf-8', unique=True)
        
    compiled_tmpl = _compiletemplate(template, base=base, isString=isString)
    compiled_tmpl = compiled_tmpl(searchList=terms, filter=WebSafe)
    if asTemplate: 
        return compiled_tmpl
    else: 
        return output(str(compiled_tmpl))

class WebSafe(Filter):
    def filter(self, val, **keywords): 
        return websafe(val)
