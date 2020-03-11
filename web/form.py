"""
HTML forms
(part of web.py)
"""

import copy
import re

from . import net, utils
from . import webapi as web


def attrget(obj, attr, value=None):
    try:
        if hasattr(obj, "has_key") and attr in obj:
            return obj[attr]
    except TypeError:
        # Handle the case where has_key takes different number of arguments.
        # This is the case with Model objects on appengine. See #134
        pass
    if (
        hasattr(obj, "keys") and attr in obj
    ):  # needed for Py3, has_key doesn't exist anymore
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
        self.validators = kw.pop("validators", [])

    def __call__(self, x=None):
        o = copy.deepcopy(self)
        if x:
            o.validates(x)
        return o

    def render(self):
        out = ""
        out += self.rendernote(self.note)
        out += "<table>\n"

        for i in self.inputs:
            html = (
                utils.safeunicode(i.pre)
                + i.render()
                + self.rendernote(i.note)
                + utils.safeunicode(i.post)
            )
            if i.is_hidden():
                out += '    <tr style="display: none;"><th></th><td>%s</td></tr>\n' % (
                    html
                )
            else:
                out += (
                    '    <tr><th><label for="%s">%s</label></th><td>%s</td></tr>\n'
                    % (net.websafe(i.id), net.websafe(i.description), html)
                )
        out += "</table>"
        return out

    def render_css(self):
        out = []
        out.append(self.rendernote(self.note))
        for i in self.inputs:
            if not i.is_hidden():
                out.append(
                    '<label for="%s">%s</label>'
                    % (net.websafe(i.id), net.websafe(i.description))
                )
            out.append(i.pre)
            out.append(i.render())
            out.append(self.rendernote(i.note))
            out.append(i.post)
            out.append("\n")
        return "".join(out)

    def rendernote(self, note):
        if note:
            return '<strong class="wrong">%s</strong>' % net.websafe(note)
        else:
            return ""

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
            if x.name == i:
                return x
        raise KeyError(i)

    def __getattr__(self, name):
        # don't interfere with deepcopy
        inputs = self.__dict__.get("inputs") or []
        for x in inputs:
            if x.name == name:
                return x
        raise AttributeError(name)

    def get(self, i, default=None):
        try:
            return self[i]
        except KeyError:
            return default

    def _get_d(self):  # @@ should really be form.attr, no?
        return utils.storage([(i.name, i.get_value()) for i in self.inputs])

    d = property(_get_d)


class Input(object):
    """Generic input. Type attribute must be specified when called directly.

    See also: <https://www.w3.org/TR/html52/sec-forms.html#the-input-element>

    Currently only types which can be written inside one `<input />` tag are
    supported.

    - For checkbox, please use `Checkbox` class for better control.
    - For radiobox, please use `Radio` class for better control.

        >>> Input(name='foo', type='email', value="user@domain.com").render()
        u'<input id="foo" name="foo" type="email" value="user@domain.com"/>'
        >>> Input(name='foo', type='number', value="bar").render()
        u'<input id="foo" name="foo" type="number" value="bar"/>'
        >>> Input(name='num', type="number", min='0', max='10', step='2', value='5').render()
        u'<input id="num" max="10" min="0" name="num" step="2" type="number" value="5"/>'
        >>> Input(name='foo', type="tel", value='55512345').render()
        u'<input id="foo" name="foo" type="tel" value="55512345"/>'
        >>> Input(name='search', type="search", value='Search').render()
        u'<input id="search" name="search" type="search" value="Search"/>'
        >>> Input(name='search', type="search", value='Search', required='required', pattern='[a-z0-9]{2,30}', placeholder='Search...').render()
        u'<input id="search" name="search" pattern="[a-z0-9]{2,30}" placeholder="Search..." required="required" type="search" value="Search"/>'
        >>> Input(name='url', type="url", value='url').render()
        u'<input id="url" name="url" type="url" value="url"/>'
        >>> Input(name='range', type="range", min='0', max='10', step='2', value='5').render()
        u'<input id="range" max="10" min="0" name="range" step="2" type="range" value="5"/>'
        >>> Input(name='color', type="color").render()
        u'<input id="color" name="color" type="color"/>'
        >>> Input(name='f', type="file", accept=".doc,.docx,.xml").render()
        u'<input accept=".doc,.docx,.xml" id="f" name="f" type="file"/>'
    """

    def __init__(self, name, *validators, **attrs):
        self.name = name
        self.validators = validators
        self.attrs = attrs = AttributeList(attrs)

        self.type = attrs.pop("type", None)
        self.description = attrs.pop("description", name)
        self.value = attrs.pop("value", None)
        self.pre = attrs.pop("pre", "")
        self.post = attrs.pop("post", "")
        self.note = None

        self.id = attrs.setdefault("id", self.get_default_id())

        if "class_" in attrs:
            attrs["class"] = attrs["class_"]
            del attrs["class_"]

    def is_hidden(self):
        return False

    def get_type(self):
        if self.type is not None:
            return self.type
        else:
            raise AttributeError("missing attribute 'type'")

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
        attrs["type"] = self.get_type()
        if self.value is not None:
            attrs["value"] = self.value
        attrs["name"] = self.name
        attrs["id"] = self.id
        return "<input %s/>" % attrs

    def rendernote(self, note):
        if note:
            return '<strong class="wrong">%s</strong>' % net.websafe(note)
        else:
            return ""

    def addatts(self):
        # add leading space for backward-compatibility
        return " " + str(self.attrs)


class AttributeList(dict):
    """List of attributes of input.

    >>> a = AttributeList(type='text', name='x', value=20)
    >>> a
    <attrs: 'name="x" type="text" value="20"'>
    """

    def copy(self):
        return AttributeList(self)

    def __str__(self):
        return " ".join(
            ['%s="%s"' % (k, net.websafe(v)) for k, v in sorted(self.items())]
        )

    def __repr__(self):
        return "<attrs: %s>" % repr(str(self))


class Textbox(Input):
    """Textbox input.

        >>> Textbox(name='foo', value='bar').render()
        u'<input id="foo" name="foo" type="text" value="bar"/>'
        >>> Textbox(name='foo', value=0).render()
        u'<input id="foo" name="foo" type="text" value="0"/>'
    """

    def get_type(self):
        return "text"


class Password(Input):
    """Password input.

        >>> Password(name='password', value='secret').render()
        u'<input id="password" name="password" type="password" value="secret"/>'
    """

    def get_type(self):
        return "password"


class Textarea(Input):
    """Textarea input.

        >>> Textarea(name='foo', value='bar').render()
        u'<textarea id="foo" name="foo">bar</textarea>'
    """

    def render(self):
        attrs = self.attrs.copy()
        attrs["name"] = self.name
        value = net.websafe(self.value or "")
        return "<textarea %s>%s</textarea>" % (attrs, value)


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
        attrs["name"] = self.name

        x = "<select %s>\n" % attrs

        for arg in self.args:
            x += self._render_option(arg)

        x += "</select>\n"
        return x

    def _render_option(self, arg, indent="  "):
        if isinstance(arg, (tuple, list)):
            value, desc = arg
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
            select_p = ""
        return indent + '<option%s value="%s">%s</option>\n' % (
            select_p,
            net.websafe(value),
            net.websafe(desc),
        )


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
        attrs["name"] = self.name

        x = "<select %s>\n" % attrs

        for label, options in self.args:
            x += '  <optgroup label="%s">\n' % net.websafe(label)
            for arg in options:
                x += self._render_option(arg, indent="    ")
            x += "  </optgroup>\n"

        x += "</select>\n"
        return x


class Radio(Input):
    def __init__(self, name, args, *validators, **attrs):
        self.args = args
        super(Radio, self).__init__(name, *validators, **attrs)

    def render(self):
        x = "<span>"
        for idx, arg in enumerate(self.args, start=1):
            if isinstance(arg, (tuple, list)):
                value, desc = arg
            else:
                value, desc = arg, arg
            attrs = self.attrs.copy()
            attrs["name"] = self.name
            attrs["type"] = "radio"
            attrs["value"] = value
            attrs["id"] = self.name + str(idx)
            if self.value == value:
                attrs["checked"] = "checked"
            x += "<input %s/> %s" % (attrs, net.websafe(desc))
        x += "</span>"
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
        self.checked = attrs.pop("checked", False)
        Input.__init__(self, name, *validators, **attrs)

    def get_default_id(self):
        value = utils.safestr(self.value or "")
        return self.name + "_" + value.replace(" ", "_")

    def render(self):
        attrs = self.attrs.copy()
        attrs["type"] = "checkbox"
        attrs["name"] = self.name
        attrs["value"] = self.value

        if self.checked:
            attrs["checked"] = "checked"
        return "<input %s/>" % attrs

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
        attrs["name"] = self.name
        if self.value is not None:
            attrs["value"] = self.value
        html = attrs.pop("html", None) or net.websafe(self.name)
        return "<button %s>%s</button>" % (attrs, html)


class Hidden(Input):
    """Hidden Input.

        >>> Hidden(name='foo', value='bar').render()
        u'<input id="foo" name="foo" type="hidden" value="bar"/>'
    """

    def is_hidden(self):
        return True

    def get_type(self):
        return "hidden"


class File(Input):
    """File input.

        >>> File(name='f', accept=".doc,.docx,.xml").render()
        u'<input accept=".doc,.docx,.xml" id="f" name="f" type="file"/>'
    """

    def get_type(self):
        return "file"


class Telephone(Input):
    """Telephone input.

    See: <https://html.spec.whatwg.org/#telephone-state-(type=tel)>

    >>> Telephone(name='tel', value='55512345').render()
    u'<input id="tel" name="tel" type="tel" value="55512345"/>'
    """

    def get_type(self):
        return "tel"


class Email(Input):
    """Email input.

    See: <https://html.spec.whatwg.org/#e-mail-state-(type=email)>

    >>> Email(name='email', value='me@example.org').render()
    u'<input id="email" name="email" type="email" value="me@example.org"/>'

    """

    def get_type(self):
        return "email"


class Search(Input):
    """Search input.

    See: <https://html.spec.whatwg.org/#text-(type=text)-state-and-search-state-(type=search)>

    >> Search(name='search', value='Search').render()
    u'<input id="search" name="search" type="search" value="Search"/>'
    >>> Search(name='search', value='Search', required='required', pattern='[a-z0-9]{2,30}', placeholder='Search...').render()
    u'<input id="search" name="search" pattern="[a-z0-9]{2,30}" placeholder="Search..." required="required" type="search" value="Search"/>'

    """

    def get_type(self):
        return "search"


class Url(Input):
    """URL input.

    See: <https://html.spec.whatwg.org/#url-state-(type=url)>

    >>> Url(name='url', value='url').render()
    u'<input id="url" name="url" type="url" value="url"/>'
    """

    def get_type(self):
        return "url"


class Number(Input):
    """Number input.

    See: <https://html.spec.whatwg.org/#number-state-(type=number)>

    >>> Number(name='num', min='0', max='10', step='2', value='5').render()
    u'<input id="num" max="10" min="0" name="num" step="2" type="number" value="5"/>'
    """

    def get_type(self):
        return "number"


class Range(Input):
    """Range input.

    See: <https://html.spec.whatwg.org/#range-state-(type=range)>

    >>> Range(name='range', min='0', max='10', step='2', value='5').render()
    u'<input id="range" max="10" min="0" name="range" step="2" type="range" value="5"/>'
    """

    def get_type(self):
        return "range"


class Color(Input):
    """Color input.

    Note: Not supported by Internet Explorer or Opera Mini

    See: <https://html.spec.whatwg.org/#color-stat://html.spec.whatwg.org/#color-state-(type=color)>

    >>> Color(name='color').render()
    u'<input id="color" name="color" type="color"/>'
    """

    def get_type(self):
        return "color"


class Datalist(Input):
    """Datalist input.

    This is currently supported by Chrome, Firefox, Edge, and Opera. It is not
    supported on Safari or Internet Explorer. Use it with caution. 

    Datalist cannot be used separately. It must be bound to an input.

    <https://html.spec.whatwg.org/#the-datalist-element>

    >>> Datalist(name='list', args=[('a', 'b'), ('c', 'd')]).render()
    u'<datalist id="list" name="list"><option label="a" value="b"/><option label="c" value="d"/></datalist>'
    >>> Datalist(name='list', args=[['a', 'b'], ['c', 'd']]).render()
    u'<datalist id="list" name="list"><option label="a" value="b"/><option label="c" value="d"/></datalist>'
    >>> Datalist(name='list', args=['a', 'b', 'c', 'd']).render()
    u'<datalist id="list" name="list"><option value="a"/><option value="b"/><option value="c"/><option value="d"/></datalist>'
    """

    def __init__(self, name, args, *validators, **kwargs):
        self.args = args
        super(Datalist, self).__init__(name, *validators, **kwargs)

    def render(self):
        attrs = self.attrs.copy()
        attrs["name"] = self.name
        label_p = ""
        x = "<datalist %s>" % attrs
        for arg in self.args:
            if isinstance(arg, (tuple, list)):
                label_p = ' label="%s"' % net.websafe(arg[0])
                label = net.websafe(arg[1])
            else:
                label = net.websafe(arg)
            x += '<option%s value="%s"/>' % (label_p, label)
        x += "</datalist>"
        return x


class Validator:
    def __deepcopy__(self, memo):
        return copy.copy(self)

    def __init__(self, msg, test, jstest=None):
        utils.autoassign(self, locals())

    def valid(self, value):
        try:
            return self.test(value)
        except:
            return False


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
