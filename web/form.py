"""
HTML forms
(part of web.py)
"""

import copy, re
from . import utils, net, webapi as web

def attrget(obj, attr, value=None):
    try:
        if hasattr(obj, 'has_key') and obj.has_key(attr): 
            return obj[attr]
    except TypeError:
        # Handle the case where has_key takes different number of arguments.
        # This is the case with Model objects on appengine. See #134
        pass
    if hasattr(obj, 'keys') and attr in obj.keys(): #needed for Py3, has_key doesn't exist anymore
        return obj[attr]
    elif hasattr(obj, attr):
        return getattr(obj, attr)
    return value

class Form(object):
    r"""
    HTML form.
    
        >>> f = Form(Textbox("x"))
        >>> f.render()
        u'<table>\n    <tr><th><label for="x">x</label></th><td><input id="x" name="x" type="text"/></td></tr>\n</table>'
        >>> f.fill(x="42")
        True
        >>> f.render()
        u'<table>\n    <tr><th><label for="x">x</label></th><td><input id="x" name="x" type="text" value="42"/></td></tr>\n</table>'
    """
    def __init__(self, *inputs, **kw):
        self.inputs = inputs
        self.valid = True
        self.note = None
        self.validators = kw.pop('validators', [])

    def __call__(self, x=None):
        o = copy.deepcopy(self)
        if x: o.validates(x)
        return o
    
    def render(self):
        out = ''
        out += self.rendernote(self.note)
        out += '<table>\n'
        
        for i in self.inputs:
            html = utils.safeunicode(i.pre) + i.render() + self.rendernote(i.note) + utils.safeunicode(i.post)
            if i.is_hidden():
                out += '    <tr style="display: none;"><th></th><td>%s</td></tr>\n' % (html)
            else:
                out += '    <tr><th><label for="%s">%s</label></th><td>%s</td></tr>\n' % (i.id, net.websafe(i.description), html)
        out += "</table>"
        return out
        
    def render_css(self): 
        out = [] 
        out.append(self.rendernote(self.note)) 
        for i in self.inputs:
            if not i.is_hidden():
                out.append('<label for="%s">%s</label>' % (i.id, net.websafe(i.description))) 
            out.append(i.pre)
            out.append(i.render()) 
            out.append(self.rendernote(i.note))
            out.append(i.post) 
            out.append('\n')
        return ''.join(out) 
        
    def rendernote(self, note):
        if note: return '<strong class="wrong">%s</strong>' % net.websafe(note)
        else: return ""
    
    def validates(self, source=None, _validate=True, **kw):
        source = source or kw or web.input()
        out = True
        for i in self.inputs:
            v = attrget(source, i.name)
            if _validate:
                out = i.validate(v) and out
            else:
                i.set_value(v)
        if _validate:
            out = out and self._validate(source)
            self.valid = out
        return out

    def _validate(self, value):
        self.value = value
        for v in self.validators:
            if not v.valid(value):
                self.note = v.msg
                return False
        return True

    def fill(self, source=None, **kw):
        return self.validates(source, _validate=False, **kw)
    
    def __getitem__(self, i):
        for x in self.inputs:
            if x.name == i: return x
        raise KeyError(i)

    def __getattr__(self, name):
        # don't interfere with deepcopy
        inputs = self.__dict__.get('inputs') or []
        for x in inputs:
            if x.name == name: return x
        raise AttributeError(name)
    
    def get(self, i, default=None):
        try:
            return self[i]
        except KeyError:
            return default
            
    def _get_d(self): #@@ should really be form.attr, no?
        return utils.storage([(i.name, i.get_value()) for i in self.inputs])
    d = property(_get_d)

class Input(object):
    def __init__(self, name, *validators, **attrs):
        self.name = name
        self.validators = validators
        self.attrs = attrs = AttributeList(attrs)
        
        self.description = attrs.pop('description', name)
        self.value = attrs.pop('value', None)
        self.pre = attrs.pop('pre', "")
        self.post = attrs.pop('post', "")
        self.note = None
        
        self.id = attrs.setdefault('id', self.get_default_id())
        
        if 'class_' in attrs:
            attrs['class'] = attrs['class_']
            del attrs['class_']
        
    def is_hidden(self):
        return False
        
    def get_type(self):
        raise NotImplementedError()
        
    def get_default_id(self):
        return self.name

    def validate(self, value):
        self.set_value(value)

        for v in self.validators:
            if not v.valid(value):
                self.note = v.msg
                return False
        return True

    def set_value(self, value):
        self.value = value

    def get_value(self):
        return self.value

    def render(self):
        attrs = self.attrs.copy()
        attrs['type'] = self.get_type()
        if self.value is not None:
            attrs['value'] = self.value
        attrs['name'] = self.name
        return '<input %s/>' % attrs

    def rendernote(self, note):
        if note: return '<strong class="wrong">%s</strong>' % net.websafe(note)
        else: return ""
        
    def addatts(self):
        # add leading space for backward-compatibility
        return " " + str(self.attrs)

class AttributeList(dict):
    """List of atributes of input.
    
    >>> a = AttributeList(type='text', name='x', value=20)
    >>> a
    <attrs: 'name="x" type="text" value="20"'>
    """
    def copy(self):
        return AttributeList(self)
        
    def __str__(self):
        return " ".join(['%s="%s"' % (k, net.websafe(v)) for k, v in sorted(self.items())])
        
    def __repr__(self):
        return '<attrs: %s>' % repr(str(self))

class Textbox(Input):
    """Textbox input.
    
        >>> Textbox(name='foo', value='bar').render()
        u'<input id="foo" name="foo" type="text" value="bar"/>'
        >>> Textbox(name='foo', value=0).render()
        u'<input id="foo" name="foo" type="text" value="0"/>'
    """        
    def get_type(self):
        return 'text'

class Password(Input):
    """Password input.

        >>> Password(name='password', value='secret').render()
        u'<input id="password" name="password" type="password" value="secret"/>'
    """
    
    def get_type(self):
        return 'password'

class Textarea(Input):
    """Textarea input.
    
        >>> Textarea(name='foo', value='bar').render()
        u'<textarea id="foo" name="foo">bar</textarea>'
    """
    def render(self):
        attrs = self.attrs.copy()
        attrs['name'] = self.name
        value = net.websafe(self.value or '')
        return '<textarea %s>%s</textarea>' % (attrs, value)

class Dropdown(Input):
    r"""Dropdown/select input.
    
        >>> Dropdown(name='foo', args=['a', 'b', 'c'], value='b').render()
        u'<select id="foo" name="foo">\n  <option value="a">a</option>\n  <option selected="selected" value="b">b</option>\n  <option value="c">c</option>\n</select>\n'
        >>> Dropdown(name='foo', args=[('a', 'aa'), ('b', 'bb'), ('c', 'cc')], value='b').render()
        u'<select id="foo" name="foo">\n  <option value="a">aa</option>\n  <option selected="selected" value="b">bb</option>\n  <option value="c">cc</option>\n</select>\n'
    """
    def __init__(self, name, args, *validators, **attrs):
        self.args = args
        super(Dropdown, self).__init__(name, *validators, **attrs)

    def render(self):
        attrs = self.attrs.copy()
        attrs['name'] = self.name
        
        x = '<select %s>\n' % attrs
        
        for arg in self.args:
            x += self._render_option(arg)

        x += '</select>\n'
        return x

    def _render_option(self, arg, indent='  '):
        if isinstance(arg, (tuple, list)):
            value, desc= arg
        else:
            value, desc = arg, arg 

        value = utils.safestr(value)
        if isinstance(self.value, (tuple, list)):
            s_value = [utils.safestr(x) for x in self.value]
        else:
            s_value = utils.safestr(self.value)
        
        if s_value == value or (isinstance(s_value, list) and value in s_value):
            select_p = ' selected="selected"'
        else:
            select_p = ''
        return indent + '<option%s value="%s">%s</option>\n' % (select_p, net.websafe(value), net.websafe(desc))
        

class GroupedDropdown(Dropdown):
    r"""Grouped Dropdown/select input.
    
        >>> GroupedDropdown(name='car_type', args=(('Swedish Cars', ('Volvo', 'Saab')), ('German Cars', ('Mercedes', 'Audi'))), value='Audi').render()
        u'<select id="car_type" name="car_type">\n  <optgroup label="Swedish Cars">\n    <option value="Volvo">Volvo</option>\n    <option value="Saab">Saab</option>\n  </optgroup>\n  <optgroup label="German Cars">\n    <option value="Mercedes">Mercedes</option>\n    <option selected="selected" value="Audi">Audi</option>\n  </optgroup>\n</select>\n'
        >>> GroupedDropdown(name='car_type', args=(('Swedish Cars', (('v', 'Volvo'), ('s', 'Saab'))), ('German Cars', (('m', 'Mercedes'), ('a', 'Audi')))), value='a').render()
        u'<select id="car_type" name="car_type">\n  <optgroup label="Swedish Cars">\n    <option value="v">Volvo</option>\n    <option value="s">Saab</option>\n  </optgroup>\n  <optgroup label="German Cars">\n    <option value="m">Mercedes</option>\n    <option selected="selected" value="a">Audi</option>\n  </optgroup>\n</select>\n'

    """
    def __init__(self, name, args, *validators, **attrs):
        self.args = args
        super(Dropdown, self).__init__(name, *validators, **attrs)

    def render(self):
        attrs = self.attrs.copy()
        attrs['name'] = self.name
        
        x = '<select %s>\n' % attrs
        
        for label, options in self.args:
            x += '  <optgroup label="%s">\n' % net.websafe(label)
            for arg in options:
                x += self._render_option(arg, indent = '    ')
            x +=  '  </optgroup>\n'
            
        x += '</select>\n'
        return x

class Radio(Input):
    def __init__(self, name, args, *validators, **attrs):
        self.args = args
        super(Radio, self).__init__(name, *validators, **attrs)

    def render(self):
        x = '<span>'
        for arg in self.args:
            if isinstance(arg, (tuple, list)):
                value, desc= arg
            else:
                value, desc = arg, arg 
            attrs = self.attrs.copy()
            attrs['name'] = self.name
            attrs['type'] = 'radio'
            attrs['value'] = value
            if self.value == value:
                attrs['checked'] = 'checked'
            x += '<input %s/> %s' % (attrs, net.websafe(desc))
        x += '</span>'
        return x

class Checkbox(Input):
    """Checkbox input.

    >>> Checkbox('foo', value='bar', checked=True).render()
    u'<input checked="checked" id="foo_bar" name="foo" type="checkbox" value="bar"/>'
    >>> Checkbox('foo', value='bar').render()
    u'<input id="foo_bar" name="foo" type="checkbox" value="bar"/>'
    >>> c = Checkbox('foo', value='bar')
    >>> c.validate('on')
    True
    >>> c.render()
    u'<input checked="checked" id="foo_bar" name="foo" type="checkbox" value="bar"/>'
    """
    def __init__(self, name, *validators, **attrs):
        self.checked = attrs.pop('checked', False)
        Input.__init__(self, name, *validators, **attrs)
        
    def get_default_id(self):
        value = utils.safestr(self.value or "")
        return self.name + '_' + value.replace(' ', '_')

    def render(self):
        attrs = self.attrs.copy()
        attrs['type'] = 'checkbox'
        attrs['name'] = self.name
        attrs['value'] = self.value

        if self.checked:
            attrs['checked'] = 'checked'            
        return '<input %s/>' % attrs

    def set_value(self, value):
        self.checked = bool(value)

    def get_value(self):
        return self.checked

class Button(Input):
    """HTML Button.
    
    >>> Button("save").render()
    u'<button id="save" name="save">save</button>'
    >>> Button("action", value="save", html="<b>Save Changes</b>").render()
    u'<button id="action" name="action" value="save"><b>Save Changes</b></button>'
    """
    def __init__(self, name, *validators, **attrs):
        super(Button, self).__init__(name, *validators, **attrs)
        self.description = ""

    def render(self):
        attrs = self.attrs.copy()
        attrs['name'] = self.name
        if self.value is not None:
            attrs['value'] = self.value
        html = attrs.pop('html', None) or net.websafe(self.name)
        return '<button %s>%s</button>' % (attrs, html)

class Hidden(Input):
    """Hidden Input.
    
        >>> Hidden(name='foo', value='bar').render()
        u'<input id="foo" name="foo" type="hidden" value="bar"/>'
    """
    def is_hidden(self):
        return True
        
    def get_type(self):
        return 'hidden'

class File(Input):
    """File input.
    
        >>> File(name='f').render()
        u'<input id="f" name="f" type="file"/>'
    """
    def get_type(self):
        return 'file'
    
class Validator:
    def __deepcopy__(self, memo): return copy.copy(self)
    def __init__(self, msg, test, jstest=None): utils.autoassign(self, locals())
    def valid(self, value): 
        try: return self.test(value)
        except: return False

notnull = Validator("Required", bool)

class regexp(Validator):
    def __init__(self, rexp, msg):
        self.rexp = re.compile(rexp)
        self.msg = msg
    
    def valid(self, value):
        return bool(self.rexp.match(value))

if __name__ == "__main__":
    import doctest
    doctest.testmod()
