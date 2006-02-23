"""form.py: A simple Python form library."""
__version__ = '0.11' # first draft
__author__ = 'Aaron Swartz <me@aaronsw.com>'

import copy
import web

class Form:
    def __init__(self, *inputs):
        self.inputs = inputs
        self.valid = True

    def __call__(self): return copy.deepcopy(self)
    def render(self):
        out = ''
        out += '<p>'
        for i in self.inputs:
            out += "<label><strong class='label'>%s</strong> " % i.name
            out += i.render()
            out += '<span id="note_%s">%s</span><br /></label>' % (i.name, self.rendernotes(i.notes()))
        return out
    
    def _rendernotes(self, notes):
        x = []
        for (n, b) in notes:
            if not b: n = '<strong class="wrong">%s</strong>' % n
            x.append(n)
        return x

    def rendernotes(self, notes):
        return ' '.join(self._rendernotes(notes))
    
    def rendernoteslist(self, notes):
        return '<ul><li>' + '</li><li>'.join(self._rendernotes(notes)) +'</li></ul>'
        
    def validates(self):
        out = True
        v = web.input()
        for i in self.inputs:
            out = i.validate(v.get(i.name)) and out
        self.valid = out
        return out
    
    def _get_d(self):
        return dict([(i.name, i.value) for i in self.inputs])
    d = property(_get_d)

class Input(object):
    def __init__(self, name, value=None, *validators):
        if isinstance(value, Validator): validators, value = (value,)+validators, None
        web.autoassign()

    def validate(self, value):
        self.value = value
        self.validates = {}
        for v in self.validators: self.validates[v] = v.valid(value)
        return reduce(lambda x,y: x and y, self.validates.values(), True)
    
    def render(self): raise NotImplementedError
    
    def notes(self):
        if hasattr(self, 'validates'):
            return [(v.msg, b) for (v, b) in self.validates.iteritems()]
        else:
            return [(v.msg, True) for v in self.validators]

#@@ quoting

class Textbox(Input):
    def render(self):
        x = '<input type="text" name="%s"' % web.htmlquote(self.name)
        if self.value: x += ' value="%s"' % web.htmlquote(self.value)
        x += ' />'
        return x

class Textarea(Input):
    def render(self):
        x = '<textarea name="%s">' % web.htmlquote(self.name)
        print>>web.debug, self.value
        if self.value is not None: x += web.htmlquote(self.value)
        x += '</textarea>'
        return x

class Dropdown(Input):
    def __init__(self, name, args, value=None, *validators):
        self.args = args
        super(Dropdown, self).__init__(name, value, *validators)

    def render(self):
        x = '<select name="%s">\n' % web.htmlquote(self.name)
        for arg in self.args:
            if self.value == arg: select_p = ' selected="selected"'
            else: select_p = ''
            x += "  <option"+select_p+">%s</option>\n" % web.htmlquote(arg)
        x += '</select>\n'
        return x

class Checkbox(Input):
    def render(self):
        x = '<input name="%s" type="checkbox"' % web.htmlquote(self.name)
        if self.value: x += ' checked="checked"'
        x += ' />'
        return x

class Validator:
    def __deepcopy__(self, memo): return copy.copy(self)
    def __init__(self, msg, test, jstest=None): web.autoassign()
    def valid(self, value): 
        try: return self.test(value)
        except: return False

notnull = Validator("Required", bool)