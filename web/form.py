"""
HTML forms
(part of web.py)
"""

import copy, re
import webapi as web
import utils, net
import datetime

def attrget(obj, attr, value=None):
    if hasattr(obj, 'has_key') and obj.has_key(attr): return obj[attr]
    if hasattr(obj, attr): return getattr(obj, attr)
    return value

class Form(object):
    r"""
    HTML form.
    
        >>> f = Form(Textbox("x"))
        >>> f.render()
        u'<table>\n    <tr><th><label for="x">x</label></th><td><input type="text" id="x" name="x"/></td></tr>\n</table>'
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
            if hasattr(i,'inputs'):
                for ii in i.inputs:
                    v = attrget(source, ii.name)
                    if _validate:
                        out = ii.validate(v) and out
                    else:
                        ii.set_value(v)
            else:
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
        raise KeyError, i

    def __getattr__(self, name):
        # don't interfere with deepcopy
        inputs = self.__dict__.get('inputs') or []
        for x in inputs:
            if x.name == name: return x
        raise AttributeError, name
    
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
        raise NotImplementedError
        
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
    <attrs: 'type="text" name="x" value="20"'>
    """
    def copy(self):
        return AttributeList(self)
        
    def __str__(self):
        return " ".join(['%s="%s"' % (k, net.websafe(v)) for k, v in self.items()])
        
    def __repr__(self):
        return '<attrs: %s>' % repr(str(self))

class Textbox(Input):
    """Textbox input.
    
        >>> Textbox(name='foo', value='bar').render()
        u'<input type="text" id="foo" value="bar" name="foo"/>'
        >>> Textbox(name='foo', value=0).render()
        u'<input type="text" id="foo" value="0" name="foo"/>'
    """        
    def get_type(self):
        return 'text'

class Password(Input):
    """Password input.

        >>> Password(name='password', value='secret').render()
        u'<input type="password" id="password" value="secret" name="password"/>'
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
            if isinstance(arg, (tuple, list)):
                value, desc= arg
            else:
                value, desc = arg, arg 

            if self.value == value or (isinstance(self.value, list) and value in self.value):
                select_p = ' selected="selected"'
            else: select_p = ''
            x += '  <option%s value="%s">%s</option>\n' % (select_p, net.websafe(value), net.websafe(desc))
            
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
    u'<input checked="checked" type="checkbox" id="foo_bar" value="bar" name="foo"/>'
    >>> Checkbox('foo', value='bar').render()
    u'<input type="checkbox" id="foo_bar" value="bar" name="foo"/>'
    >>> c = Checkbox('foo', value='bar')
    >>> c.validate('on')
    True
    >>> c.render()
    u'<input checked="checked" type="checkbox" id="foo_bar" value="bar" name="foo"/>'
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
    u'<button id="action" value="save" name="action"><b>Save Changes</b></button>'
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
        u'<input type="hidden" id="foo" value="bar" name="foo"/>'
    """
    def is_hidden(self):
        return True
        
    def get_type(self):
        return 'hidden'

class File(Input):
    """File input.
    
        >>> File(name='f').render()
        u'<input type="file" id="f" name="f"/>'
    """
    def get_type(self):
        return 'file'

class Time(Input): 
    r"""Time input with dropdowns

    >>> Time('the_time', every=10, value='00:00:00').render()
    u'<select id="the_time_hour" name="the_time_hour">\n  <option value="01">01</option>\n  <option value="02">02</option>\n  <option value="03">03</option>\n  <option value="04">04</option>\n  <option value="05">05</option>\n  <option value="06">06</option>\n  <option value="07">07</option>\n  <option value="08">08</option>\n  <option value="09">09</option>\n  <option value="10">10</option>\n  <option value="11">11</option>\n  <option selected="selected" value="12">12</option>\n</select>\n:\n<select id="the_time_minute" name="the_time_minute">\n  <option selected="selected" value="00">00</option>\n  <option value="10">10</option>\n  <option value="20">20</option>\n  <option value="30">30</option>\n  <option value="40">40</option>\n  <option value="50">50</option>\n</select>\n&nbsp;\n<select id="the_time_ampm" name="the_time_ampm">\n  <option selected="selected" value="AM">AM</option>\n  <option value="PM">PM</option>\n</select>\n'

    >>> Time('the_time', iso=True, every=10, value='00:00:00').render()
    u'<select id="the_time_hour" name="the_time_hour">\n  <option selected="selected" value="00">00</option>\n  <option value="01">01</option>\n  <option value="02">02</option>\n  <option value="03">03</option>\n  <option value="04">04</option>\n  <option value="05">05</option>\n  <option value="06">06</option>\n  <option value="07">07</option>\n  <option value="08">08</option>\n  <option value="09">09</option>\n  <option value="10">10</option>\n  <option value="11">11</option>\n  <option value="12">12</option>\n  <option value="13">13</option>\n  <option value="14">14</option>\n  <option value="15">15</option>\n  <option value="16">16</option>\n  <option value="17">17</option>\n  <option value="18">18</option>\n  <option value="19">19</option>\n  <option value="20">20</option>\n  <option value="21">21</option>\n  <option value="22">22</option>\n  <option value="23">23</option>\n</select>\n:\n<select id="the_time_minute" name="the_time_minute">\n  <option selected="selected" value="00">00</option>\n  <option value="10">10</option>\n  <option value="20">20</option>\n  <option value="30">30</option>\n  <option value="40">40</option>\n  <option value="50">50</option>\n</select>\n'
    """

    def __init__(self, name, iso=False, every=15, *validators, **attrs):
        self.iso = iso
        if self.iso: 
            hours_range = range(0,24)
        else:
            hours_range = range(1,13)
        hours = map(lambda h: '%02i' % h, hours_range)
        minutes = map(lambda m: '%02i' % m, range(0, 60, every))

        self.hour_input = Dropdown(name+'_hour',  args=hours)
        self.minute_input = Dropdown(name+'_minute',args=minutes)
        if not self.iso:
            self.ampm_input = Dropdown(name+'_ampm',args=['AM','PM'])

        super(Time, self).__init__(name, *validators, **attrs)
        self.set_value(attrs.get('value'))

    def __setattr__(self, name, value):
        if name == 'value':
            self.set_value(value)
        else:
            object.__setattr__(self, name, value)

    def __getattr__(self, name): 
        if name == 'value':
            return self.get_value()
        elif name == 'inputs':
            if self.iso:            
                return [self.hour_input, self.minute_input]
            else:
                return [self.hour_input, self.minute_input, self.ampm_input]
        raise AttributeError, name

    def set_value(self, value): 
        '''Value in in ISO format: %H:%M:%S
        '''
        if not value: 
            dt = datetime.datetime.now()
        else:
            dt = datetime.datetime.strptime(value, '%H:%M:%S')
        if self.iso: 
            self.hour_input.value = dt.strftime('%H')
        else:
            self.hour_input.value = dt.strftime('%I')
            self.ampm_input.value = dt.strftime('%p')
        self.minute_input.value = dt.strftime('%M')

    def get_value(self): 
        '''Value formatted in ISO: %H:%M:%S
        '''
        if self.iso:
            return '%s:%s:00' % (self.hour_input.value, self.minute_input.value)
        else:
            ds = '%s:%s %s' % (self.hour_input.value, self.minute_input.value, self.ampm_input.value)
            dt = datetime.datetime.strptime(ds, '%I:%M %p')
            return dt.strftime('%H:%M:00')

    def render(self):
        x = self.hour_input.render()
        x += ':\n'
        x += self.minute_input.render()
        if not self.iso:
            x += '&nbsp;\n'
            x += self.ampm_input.render()
        return x


class Date(Input):
    r"""Date input with three dropdowns.

    >>> Date('the_date', years=2, start_year=2010, value='2011-12-01').render()
    u'<select id="the_date_day" name="the_date_day">\n  <option selected="selected" value="01">01</option>\n  <option value="02">02</option>\n  <option value="03">03</option>\n  <option value="04">04</option>\n  <option value="05">05</option>\n  <option value="06">06</option>\n  <option value="07">07</option>\n  <option value="08">08</option>\n  <option value="09">09</option>\n  <option value="10">10</option>\n  <option value="11">11</option>\n  <option value="12">12</option>\n  <option value="13">13</option>\n  <option value="14">14</option>\n  <option value="15">15</option>\n  <option value="16">16</option>\n  <option value="17">17</option>\n  <option value="18">18</option>\n  <option value="19">19</option>\n  <option value="20">20</option>\n  <option value="21">21</option>\n  <option value="22">22</option>\n  <option value="23">23</option>\n  <option value="24">24</option>\n  <option value="25">25</option>\n  <option value="26">26</option>\n  <option value="27">27</option>\n  <option value="28">28</option>\n  <option value="29">29</option>\n  <option value="30">30</option>\n  <option value="31">31</option>\n</select>\n<select id="the_date_month" name="the_date_month">\n  <option value="01">Jan</option>\n  <option value="02">Feb</option>\n  <option value="03">Mar</option>\n  <option value="04">Apr</option>\n  <option value="05">May</option>\n  <option value="06">Jun</option>\n  <option value="07">Jul</option>\n  <option value="08">Aug</option>\n  <option value="09">Sep</option>\n  <option value="10">Oct</option>\n  <option value="11">Nov</option>\n  <option selected="selected" value="12">Dec</option>\n</select>\n<select id="the_date_year" name="the_date_year">\n  <option value="2010">2010</option>\n  <option selected="selected" value="2011">2011</option>\n</select>\n'
    """
    
    def __init__(self, name, start_year=-1, years=2, *validators, **attrs):
        if start_year == -1:
            start = datetime.datetime.now().year
        else:
            start = start_year
        years_range = map(lambda y: '%02i' % y, range(start, start + years))
        now = datetime.datetime.now()
        months_range = map(lambda m: ('%02i' % m, '%s' % now.replace(2000, m).strftime('%b')), range(1,13))
        days_range = map(lambda d: '%02i' % d, range(1,32))

        self.day_input = Dropdown(name+'_day',  args=days_range)
        self.month_input = Dropdown(name+'_month',args=months_range)
        self.year_input = Dropdown(name+'_year', args=years_range)        

        super(Date, self).__init__(name, *validators, **attrs)
        self.set_value(attrs.get('value'))
                           
    def __setattr__(self, name, value):
        if name == 'value':
            self.set_value(value)
        else:
            object.__setattr__(self, name, value)

    def __getattr__(self, name): 
        if name == 'value':
            return self.get_value()
        elif name == 'inputs':
            return [self.day_input, self.month_input, self.year_input]
        raise AttributeError, name

    def set_value(self, value): 
        '''Value in ISO format: %Y-%m-%d
        '''
        if not value:
            dt = datetime.datetime.now()
        else:
            dt = datetime.datetime.strptime(value, '%Y-%m-%d')
        self.day_input.value = dt.strftime('%d')
        self.month_input.value = dt.strftime('%m')
        self.year_input.value = dt.strftime('%Y')

    def get_value(self): 
        '''Value formatted in ISO: %Y-%m-%d
        '''
        return '%s-%s-%s' % (self.year_input.value, self.month_input.value, self.day_input.value)

    def render(self):
        x = self.day_input.render()
        x += self.month_input.render()
        x += self.year_input.render()
        return x
    
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
