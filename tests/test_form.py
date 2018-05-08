from web.form import Form, Textbox

def test_id_escape_issue():
    f = Form(Textbox("x", id="x <unsafe>"))
    assert "<unsafe>" not in f.render()
    assert "<unsafe>" not in f.render_css()

def test_checkbox_value_issue():
    c = Checkbox("x")
    c.set_value('')
    assert True == c.get_value()
    c.set_value(None)
    assert False == c.get_value()
