"""
Cheetah API
(from web.py)
"""

__all__ = ["render", "djangoerror", "debugerror"]

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

# adapted from Django <djangoproject.com> 
# Copyright (c) 2005, the Lawrence Journal-World
# Used under the modified BSD license:
# http://www.xfree86.org/3.3.6/COPYRIGHT2.html#5

DJANGO_500_PAGE = """#import inspect
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">
<html lang="en">
<head>
  <meta http-equiv="content-type" content="text/html; charset=utf-8" />
  <meta name="robots" content="NONE,NOARCHIVE" />
  <title>$exception_type at $ctx.path</title>
  <style type="text/css">
    html * { padding:0; margin:0; }
    body * { padding:10px 20px; }
    body * * { padding:0; }
    body { font:small sans-serif; }
    body>div { border-bottom:1px solid #ddd; }
    h1 { font-weight:normal; }
    h2 { margin-bottom:.8em; }
    h2 span { font-size:80%; color:#666; font-weight:normal; }
    h3 { margin:1em 0 .5em 0; }
    h4 { margin:0 0 .5em 0; font-weight: normal; }
    table { 
        border:1px solid #ccc; border-collapse: collapse; background:white; }
    tbody td, tbody th { vertical-align:top; padding:2px 3px; }
    thead th { 
        padding:1px 6px 1px 3px; background:#fefefe; text-align:left; 
        font-weight:normal; font-size:11px; border:1px solid #ddd; }
    tbody th { text-align:right; color:#666; padding-right:.5em; }
    table.vars { margin:5px 0 2px 40px; }
    table.vars td, table.req td { font-family:monospace; }
    table td.code { width:100%;}
    table td.code div { overflow:hidden; }
    table.source th { color:#666; }
    table.source td { 
        font-family:monospace; white-space:pre; border-bottom:1px solid #eee; }
    ul.traceback { list-style-type:none; }
    ul.traceback li.frame { margin-bottom:1em; }
    div.context { margin: 10px 0; }
    div.context ol { 
        padding-left:30px; margin:0 10px; list-style-position: inside; }
    div.context ol li { 
        font-family:monospace; white-space:pre; color:#666; cursor:pointer; }
    div.context ol.context-line li { color:black; background-color:#ccc; }
    div.context ol.context-line li span { float: right; }
    div.commands { margin-left: 40px; }
    div.commands a { color:black; text-decoration:none; }
    #summary { background: #ffc; }
    #summary h2 { font-weight: normal; color: #666; }
    #explanation { background:#eee; }
    #template, #template-not-exist { background:#f6f6f6; }
    #template-not-exist ul { margin: 0 0 0 20px; }
    #traceback { background:#eee; }
    #requestinfo { background:#f6f6f6; padding-left:120px; }
    #summary table { border:none; background:transparent; }
    #requestinfo h2, #requestinfo h3 { position:relative; margin-left:-100px; }
    #requestinfo h3 { margin-bottom:-1em; }
    .error { background: #ffc; }
    .specific { color:#cc3300; font-weight:bold; }
  </style>
  <script type="text/javascript">
  //<!--
    function getElementsByClassName(oElm, strTagName, strClassName){
        // Written by Jonathan Snook, http://www.snook.ca/jon; 
        // Add-ons by Robert Nyman, http://www.robertnyman.com
        var arrElements = (strTagName == "*" && document.all)? document.all :
        oElm.getElementsByTagName(strTagName);
        var arrReturnElements = new Array();
        strClassName = strClassName.replace(/\-/g, "\\-");
        var oRegExp = new RegExp("(^|\\s)" + strClassName + "(\\s|$)");
        var oElement;
        for(var i=0; i<arrElements.length; i++){
            oElement = arrElements[i];
            if(oRegExp.test(oElement.className)){
                arrReturnElements.push(oElement);
            }
        }
        return (arrReturnElements)
    }
    function hideAll(elems) {
      for (var e = 0; e < elems.length; e++) {
        elems[e].style.display = 'none';
      }
    }
    window.onload = function() {
      hideAll(getElementsByClassName(document, 'table', 'vars'));
      hideAll(getElementsByClassName(document, 'ol', 'pre-context'));
      hideAll(getElementsByClassName(document, 'ol', 'post-context'));
    }
    function toggle() {
      for (var i = 0; i < arguments.length; i++) {
        var e = document.getElementById(arguments[i]);
        if (e) {
          e.style.display = e.style.display == 'none' ? 'block' : 'none';
        }
      }
      return false;
    }
    function varToggle(link, id) {
      toggle('v' + id);
      var s = link.getElementsByTagName('span')[0];
      var uarr = String.fromCharCode(0x25b6);
      var darr = String.fromCharCode(0x25bc);
      s.innerHTML = s.innerHTML == uarr ? darr : uarr;
      return false;
    }
    //-->
  </script>
</head>
<body>

<div id="summary">
  <h1>$exception_type at $ctx.path</h1>
  <h2>$exception_value</h2>
  <table><tr>
    <th>Python</th>
    <td>$lastframe.filename in $lastframe.function, line $lastframe.lineno</td>
  </tr><tr>
    <th>Web</th>
    <td>$ctx.method $ctx.home$ctx.path</td>
  </tr></table>
</div>
<div id="traceback">
  <h2>Traceback <span>(innermost first)</span></h2>
  <ul class="traceback">
    #for frame in $frames
      <li class="frame">
        <code>$frame.filename</code> in <code>$frame.function</code>

        #if $frame.context_line
          <div class="context" id="c$frame.id">
            #if $frame.pre_context
              <ol start="$frame.pre_context_lineno" class="pre-context" id="pre$frame.id">#for line in $frame.pre_context#<li onclick="toggle('pre$frame.id', 'post$frame.id')">$line</li>#end for#</ol>
            #end if
            <ol start="$frame.lineno" class="context-line"><li onclick="toggle('pre$frame.id', 'post$frame.id')">$frame.context_line <span>...</span></li></ol>
            #if $frame.post_context
              <ol start='$(frame.lineno+1)' class="post-context" id="post$frame.id">#for line in $frame.post_context#<li onclick="toggle('pre$frame.id', 'post$frame.id')">$line</li>#end for#</ol>
            #end if
          </div>
        #end if

        #if $frame.vars
          <div class="commands">
              <a href='#' onclick="return varToggle(this, '$frame.id')"><span>&#x25b6;</span> Local vars</a>## $inspect.formatargvalues(*inspect.getargvalues(frame['tb'].tb_frame))
          </div>
          <table class="vars" id="v$frame.id">
            <thead>
              <tr>
                <th>Variable</th>
                <th>Value</th>
              </tr>
            </thead>
            <tbody>
              #set frameitems = $frame.vars
              #silent frameitems.sort(lambda x,y: cmp(x[0], y[0]))
              #for (key, val) in frameitems
                <tr>
                  <td>$key</td>
                  <td class="code"><div>$prettify(val)</div></td>
                </tr>
              #end for
            </tbody>
          </table>
        #end if
      </li>
    #end for
  </ul>
</div>

<div id="requestinfo">
  #if $context_.output or $context_.headers
    <h2>Response so far</h2>
    <h3>HEADERS</h3>
    #if $ctx.headers
      <p class="req"><code>
      #for (k, v) in $context_.headers
        $k: $v<br />
      #end for
      
      </code></p>
    #else
      <p>No headers.</p>
    #end if
    <h3>BODY</h3>
    <p class="req" style="padding-bottom: 2em"><code>
    $context_.output
    </code></p>
  #end if
  
  <h2>Request information</h2>

  <h3>INPUT</h3>
  #if $input_
    <table class="req">
      <thead>
        <tr>
          <th>Variable</th>
          <th>Value</th>
        </tr>
      </thead>
      <tbody>
        #set myitems = $input_.items()
        #silent myitems.sort(lambda x,y: cmp(x[0], y[0]))
        #for (key, val) in myitems
          <tr>
            <td>$key</td>
            <td class="code"><div>$val</div></td>
          </tr>
        #end for
      </tbody>
    </table>
  #else
  <p>No input data.</p>
  #end if

  <h3 id="cookie-info">COOKIES</h3>
  #if $cookies_
    <table class="req">
      <thead>
        <tr>
          <th>Variable</th>
          <th>Value</th>
        </tr>
      </thead>
      <tbody>
        #for (key, val) in $cookies_.items()
          <tr>
            <td>$key</td>
            <td class="code"><div>$val</div></td>
          </tr>
        #end for
      </tbody>
    </table>
  #else
    <p>No cookie data</p>
  #end if

  <h3 id="meta-info">META</h3>
  <table class="req">
    <thead>
      <tr>
        <th>Variable</th>
        <th>Value</th>
      </tr>
    </thead>
    <tbody>
      #set myitems = $context_.items()
      #silent myitems.sort(lambda x,y: cmp(x[0], y[0]))
      #for (key, val) in $myitems
      #if not $key.startswith('_') and $key not in ['env', 'output', 'headers', 'environ', 'status', 'db_execute']
        <tr>
          <td>$key</td>
          <td class="code"><div>$prettify($val)</div></td>
        </tr>
      #end if
      #end for
    </tbody>
  </table>

  <h3 id="meta-info">ENVIRONMENT</h3>
  <table class="req">
    <thead>
      <tr>
        <th>Variable</th>
        <th>Value</th>
      </tr>
    </thead>
    <tbody>
      #set myitems = $context_.env.items()
      #silent myitems.sort(lambda x,y: cmp(x[0], y[0]))  
      #for (key, val) in $myitems
        <tr>
          <td>$key</td>
          <td class="code"><div>$prettify($val)</div></td>
        </tr>
      #end for
    </tbody>
  </table>

</div>

<div id="explanation">
  <p>
    You're seeing this error because you have <code>web.internalerror</code>
    set to <code>web.debugerror</code>. Change that if you want a different one.
  </p>
</div>

</body>
</html>"""

def djangoerror():
    def _get_lines_from_file(filename, lineno, context_lines):
        """
        Returns context_lines before and after lineno from file.
        Returns (pre_context_lineno, pre_context, context_line, post_context).
        """
        try:
            source = open(filename).readlines()
            lower_bound = max(0, lineno - context_lines)
            upper_bound = lineno + context_lines

            pre_context = \
                [line.strip('\n') for line in source[lower_bound:lineno]]
            context_line = source[lineno].strip('\n')
            post_context = \
                [line.strip('\n') for line in source[lineno + 1:upper_bound]]

            return lower_bound, pre_context, context_line, post_context
        except (OSError, IOError):
            return None, [], None, []    
    
    exception_type, exception_value, tback = sys.exc_info()
    frames = []
    while tback is not None:
        filename = tback.tb_frame.f_code.co_filename
        function = tback.tb_frame.f_code.co_name
        lineno = tback.tb_lineno - 1
        pre_context_lineno, pre_context, context_line, post_context = \
            _get_lines_from_file(filename, lineno, 7)
        frames.append({
            'tback': tback,
            'filename': filename,
            'function': function,
            'lineno': lineno,
            'vars': tback.tb_frame.f_locals.items(),
            'id': id(tback),
            'pre_context': pre_context,
            'context_line': context_line,
            'post_context': post_context,
            'pre_context_lineno': pre_context_lineno,
        })
        tback = tback.tb_next
    lastframe = frames[-1]
    frames.reverse()
    urljoin = urlparse.urljoin
    input_ = input()
    cookies_ = cookies()
    context_ = ctx
    def prettify(x):
        try: 
            out = pprint.pformat(x)
        except Exception, e: 
            out = '[could not display: <' + e.__class__.__name__ + \
                  ': '+str(e)+'>]'
        return out
    return render(DJANGO_500_PAGE, asTemplate=True, isString=True)

def debugerror():
    """
    A replacement for `internalerror` that presents a nice page with lots
    of debug information for the programmer.

    (Based on the beautiful 500 page from [Django](http://djangoproject.com/), 
    designed by [Wilson Miner](http://wilsonminer.com/).)

    Requires [Cheetah](http://cheetahtemplate.org/).
    """
    # need to do django first, so it can get the old stuff
    out = str(djangoerror())
    if 0:
        # Cheetah isn't installed
        out = """<p>You've set web.py to use the fancier debugerror error 
messages, but these messages require you install the Cheetah template 
system. For more information, see 
<a href="http://webpy.org/">the web.py website</a>.</p>

<p>In the meantime, here's a plain old error message:</p>

<pre>%s</pre>

<p>(If it says something about 'Compiler', then it's probably
because you're trying to use templates and you haven't
installed Cheetah. See above.)</p>
""" % htmlquote(traceback.format_exc())
    ctx.status = "500 Internal Server Error"
    ctx.headers = [('Content-Type', 'text/html')]
    ctx.output = out
