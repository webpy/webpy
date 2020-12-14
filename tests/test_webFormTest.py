import web.form
import web
import web.db
import web.py3helpers
import web.utils
import web.webapi
import web.debugerror
import web.net
import web.template
import web.http
import web.httpserver
import web.session
import web.wsgi
import web.application
import web.browser


def test_repr_AttributeList_0():
    var = web.form.AttributeList()
    ret = var.__repr__()
    assert ret is not None


def test_init_Button_0():
    var = web.form.Button(None, None, None)
    ret = var
    assert isinstance(ret, web.form.Button)


def test_addatts_Button_0():
    var = web.form.Button(None, None, None)
    ret = var.addatts()
    assert ret is not None


def test_get_value_Button_0():
    var = web.form.Button(None, None, None)
    ret = var.get_value()
    assert ret is None


def test_render_Button_0():
    var = web.form.Button(None, None, None)
    ret = var.render()
    assert ret is not None


def test_rendernote_Button_0():
    var = web.form.Button(None, None, None)
    ret = var.rendernote(None)
    assert ret is not None


def test_set_value_Button_0():
    var = web.form.Button(None, None, None)
    ret = var.set_value(None)
    assert ret is None


def test_get_type_Color_0():
    var = web.form.Color(None, None, None)
    ret = var.get_type()
    assert ret is not None


def test_init_Datalist_0():
    var = web.form.Datalist(None, None, None, None)
    ret = var
    assert isinstance(ret, web.form.Datalist)


def test_get_type_Date_0():
    var = web.form.Date(None, None, None)
    ret = var.get_type()
    assert ret is not None


def test_init_Dropdown_0():
    var = web.form.Dropdown(None, None, None, None)
    ret = var
    assert isinstance(ret, web.form.Dropdown)


def test_render_option_Dropdown_0():
    var = web.form.Dropdown(None, None, None, None)
    ret = var._render_option(None, r"  ")
    assert ret is not None


def test_get_type_Email_0():
    var = web.form.Email(None, None, None)
    ret = var.get_type()
    assert ret is not None


def test_get_type_File_0():
    var = web.form.File(None, None, None)
    ret = var.get_type()
    assert ret is not None


def test_call_Form_0():
    var = web.form.Form(None, None)
    ret = var.__call__(None)
    assert isinstance(ret, web.form.Form)


def test_validate_Form_0():
    var = web.form.Form(None, None)
    ret = var._validate(None)
    assert ret is not None


def test_init_GroupedDropdown_0():
    var = web.form.GroupedDropdown(None, None, None, None)
    ret = var
    assert isinstance(ret, web.form.GroupedDropdown)


def test_get_type_Hidden_0():
    var = web.form.Hidden(None, None, None)
    ret = var.get_type()
    assert ret is not None


def test_is_hidden_Hidden_0():
    var = web.form.Hidden(None, None, None)
    ret = var.is_hidden()
    assert ret is not None


def test_get_type_Number_0():
    var = web.form.Number(None, None, None)
    ret = var.get_type()
    assert ret is not None


def test_get_type_Password_0():
    var = web.form.Password(None, None, None)
    ret = var.get_type()
    assert ret is not None


def test_init_Radio_0():
    var = web.form.Radio(None, None, None, None)
    ret = var
    assert isinstance(ret, web.form.Radio)


def test_get_type_Range_0():
    var = web.form.Range(None, None, None)
    ret = var.get_type()
    assert ret is not None


def test_get_type_Search_0():
    var = web.form.Search(None, None, None)
    ret = var.get_type()
    assert ret is not None


def test_get_type_Telephone_0():
    var = web.form.Telephone(None, None, None)
    ret = var.get_type()
    assert ret is not None


def test_render_Textarea_0():
    var = web.form.Textarea(None, None, None)
    ret = var.render()
    assert ret is not None


def test_get_type_Time_0():
    var = web.form.Time(None, None, None)
    ret = var.get_type()
    assert ret is not None


def test_get_type_Url_0():
    var = web.form.Url(None, None, None)
    ret = var.get_type()
    assert ret is not None


def test_deepcopy_Validator_0():
    var = web.form.Validator(None, None, None)
    ret = var.__deepcopy__(None)
    assert isinstance(ret, web.form.Validator)


def test_valid_Validator_0():
    var = web.form.Validator(None, None, None)
    ret = var.valid(None)
    assert ret is not None


def test_get_type_Button_0():
    try:
        var = web.form.Button(None, None, None)
        var.get_type()
    except Exception as e:
        assert isinstance(e, AttributeError)


def test_validate_Button_0():
    try:
        var = web.form.Button(None, None, None)
        var.validate(None)
    except Exception as e:
        assert isinstance(e, AttributeError)


def test_init_Checkbox_0():
    try:
        var = web.form.Checkbox(None, None, None)
        var
    except Exception as e:
        assert isinstance(e, TypeError)


def test_render_Datalist_0():
    try:
        var = web.form.Datalist(None, None, None, None)
        var.render()
    except Exception as e:
        assert isinstance(e, TypeError)


def test_render_Dropdown_0():
    try:
        var = web.form.Dropdown(None, None, None, None)
        var.render()
    except Exception as e:
        assert isinstance(e, TypeError)


def test_getitem_Form_0():
    try:
        var = web.form.Form(None, None)
        var.__getitem__(None)
    except Exception as e:
        assert isinstance(e, AttributeError)


def test_get_d_Form_0():
    try:
        var = web.form.Form(None, None)
        var._get_d()
    except Exception as e:
        assert isinstance(e, AttributeError)


def test_get_Form_0():
    try:
        var = web.form.Form(None, None)
        var.get(None, None)
    except Exception as e:
        assert isinstance(e, AttributeError)


def test_render_GroupedDropdown_0():
    try:
        var = web.form.GroupedDropdown(None, None, None, None)
        var.render()
    except Exception as e:
        assert isinstance(e, TypeError)


def test_render_Radio_0():
    try:
        var = web.form.Radio(None, None, None, None)
        var.render()
    except Exception as e:
        assert isinstance(e, TypeError)


def test_init_regexp_0():
    try:
        var = web.form.regexp(None, None)
        var
    except Exception as e:
        assert isinstance(e, TypeError)


def test_attrget_0():
    try:
        web.form.attrget(None, None, None)
    except Exception as e:
        assert isinstance(e, TypeError)
