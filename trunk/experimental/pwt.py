import web
import simplejson, sudo
urls = (
    '/sudo', 'sudoku',
    '/length', 'length',
)


class pwt(object):
    _inFunc = False
    updated = {}
    page = """
<script src="/static/prototype.js"></script>
<script src="/static/behaviour.js"></script>
<script>
Behaviour.register({'input': function (e) { 
    e.onmouseup = e.onkeyup = e.onchange = function () { send(e) }
}})
</script>

<form name="main" onsubmit="return false;">%s</form>

<script>
function send(e) {
    ajax =  new Ajax.Request(document.location, {method:'post', parameters: 
      Form.serialize(document.forms.main)
    });
}

function receive(d) {
    $H(d).keys().each(function (key) {
        v = d[key];
        k = document.forms.main[key];

        if (k) k.value = v;
        else $(key).innerHTML = v;
    })
}
</script>
"""

    def GET(self):
        web.header('Content-Type', 'text/html')
        print self.page % self.form()
    
    def POST(self):
        i = web.input()
        if '_' in i: del i['_']
        #for k, v in i.iteritems(): setattr(self, k, v)
        
        self._inFunc = True
        self.work(**i)
        self._inFunc = False
        
        web.header('Content-Type', 'text/javascript')
        print 'receive('+simplejson.dumps(self.updated)+');'
    
    def __setattr__(self, k, v):
        if self._inFunc and k != '_inFunc':
            self.updated[k] = v
        object.__setattr__(self, k, v)

class sudoku(pwt):
    def form(self):
        import sudo
        out = ''
        n = 0
        for i in range(9):
            for j in range(9):
                out += '<input type="text" size="1" name="%s" />' % (sudo.squares[n])
                n += 1
            out += '<br />'

        return out
    
    def work(self, **kw):
        values = dict((s, sudo.digits) for s in sudo.squares)
        for k, v in kw.iteritems():
            if v:
                sudo.assign(values, k, v)

        for k, v in values.iteritems():
            if len(v) == 1:
                setattr(self, k, v)

        return values

class length(pwt):
    def form(self):
        return '<p id="output">&nbsp;</p><input type="range" name="n" value="0" />'
    
    def work(self):
        self.output = ('a' * web.intget(self.n, 0) or '&nbsp;')

if __name__ == "__main__":
    web.run(urls, globals(), web.reloader)