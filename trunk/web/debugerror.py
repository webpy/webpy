"""
pretty debug errors
(part of web.py)

adapted from Django <djangoproject.com> 
Copyright (c) 2005, the Lawrence Journal-World
Used under the modified BSD license:
http://www.xfree86.org/3.3.6/COPYRIGHT2.html#5
"""

__all__ = ["debugerror", "djangoerror"]

import sys, urlparse, pprint
from net import websafe
from template import Template
import webapi as web

import os, os.path
whereami = os.path.join(os.getcwd(), __file__)
whereami = os.path.sep.join(whereami.split(os.path.sep)[:-1])
djangoerror_t = """\
$def with (exception_type, exception_value, frames)
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
    <td>$frames[0].filename in $frames[0].function, line $frames[0].lineno</td>
  </tr><tr>
    <th>Web</th>
    <td>$ctx.method $ctx.home$ctx.path</td>
  </tr></table>
</div>
<div id="traceback">
<h2>Traceback <span>(innermost first)</span></h2>
<ul class="traceback">
$for frame in frames:
    <li class="frame">
    <code>$frame.filename</code> in <code>$frame.function</code>
    $if frame.context_line:
        <div class="context" id="c$frame.id">
        $if frame.pre_context:
            <ol start="$frame.pre_context_lineno" class="pre-context" id="pre$frame.id">
            $for line in frame.pre_context:
                <li onclick="toggle('pre$frame.id', 'post$frame.id')">$line</li>
            </ol>
            <ol start="$frame.lineno" class="context-line"><li onclick="toggle('pre$frame.id', 'post$frame.id')">$frame.context_line <span>...</span></li></ol>
        $if frame.post_context:
          <ol start='${frame.lineno + 1}' class="post-context" id="post$frame.id">
          $for line in frame.post_context:
              <li onclick="toggle('pre$frame.id', 'post$frame.id')">$line</li>
          </ol>
      </div>
    
    $if frame.vars:
        <div class="commands">
        <a href='#' onclick="return varToggle(this, '$frame.id')"><span>&#x25b6;</span> Local vars</a>
        $# $inspect.formatargvalues(*inspect.getargvalues(frame['tb'].tb_frame))
        </div>
        $:dicttable(frame.vars, kls='vars', id=('v' + str(frame.id)))
      </li>
  </ul>
</div>

<div id="requestinfo">
$if ctx.output or ctx.headers:
    <h2>Response so far</h2>
    <h3>HEADERS</h3>
    <p class="req"><code>
    $for kv in ctx.headers:
        $kv[0]: $kv[1]<br />
    $else:
        [no headers]
    </code></p>

    <h3>BODY</h3>
    <p class="req" style="padding-bottom: 2em"><code>
    $ctx.output
    </code></p>
  
<h2>Request information</h2>

<h3>INPUT</h3>
$:dicttable(web.input())

<h3 id="cookie-info">COOKIES</h3>
$:dicttable(web.cookies())

<h3 id="meta-info">META</h3>
$ newctx = []
$# ) and (k not in ['env', 'output', 'headers', 'environ', 'status', 'db_execute']):
$for k, v in ctx.iteritems():
    $if not k.startswith('_') and (k in x):
        $newctx.append(kv)
$:dicttable(dict(newctx))

<h3 id="meta-info">ENVIRONMENT</h3>
$:dicttable(ctx.env)
</div>

<div id="explanation">
  <p>
    You're seeing this error because you have <code>web.internalerror</code>
    set to <code>web.debugerror</code>. Change that if you want a different one.
  </p>
</div>

</body>
</html>
"""

dicttable_t = r"""$def with (d, kls='req', id=None)
$if d:
    <table class="$kls"\
    $if id:  id="$id"\
    ><thead><tr><th>Variable</th><th>Value</th></tr></thead>
    <tbody>
    $ temp = d.items()
    $temp.sort()
    $for kv in temp:
        <tr><td>$kv[0]</td><td class="code"><div>$prettify(kv[1])</div></td></tr>
    </tbody>
    </table>
$else:
    <p>No data.</p>
"""

dicttable_r = Template(dicttable_t, filter=websafe)
djangoerror_r = Template(djangoerror_t, filter=websafe)

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
        frames.append(web.storage({
            'tback': tback,
            'filename': filename,
            'function': function,
            'lineno': lineno,
            'vars': tback.tb_frame.f_locals,
            'id': id(tback),
            'pre_context': pre_context,
            'context_line': context_line,
            'post_context': post_context,
            'pre_context_lineno': pre_context_lineno,
        }))
        tback = tback.tb_next
    frames.reverse()
    urljoin = urlparse.urljoin
    def prettify(x):
        try: 
            out = pprint.pformat(x)
        except Exception, e: 
            out = '[could not display: <' + e.__class__.__name__ + \
                  ': '+str(e)+'>]'
        return out
    dt = dicttable_r
    dt.globals = {'prettify': prettify}
    t = djangoerror_r
    t.globals = {'ctx': web.ctx, 'web':web, 'dicttable':dt, 'dict':dict, 'str':str}
    return t(exception_type, exception_value, frames)

def debugerror():
    """
    A replacement for `internalerror` that presents a nice page with lots
    of debug information for the programmer.

    (Based on the beautiful 500 page from [Django](http://djangoproject.com/), 
    designed by [Wilson Miner](http://wilsonminer.com/).)
    """
    
    web.ctx.headers = [('Content-Type', 'text/html')]
    web.ctx.output = djangoerror()

if __name__ == "__main__":
    urls = (
        '/', 'index'
    )
    
    class index:
        def GET(self):
            thisdoesnotexist
    
    web.internalerror = web.debugerror
    web.run(urls)