from web.form import Form, Textbox


def test_id_escape_issue():
    f = Form(Textbox("x", id="x <unsafe>"))
    assert "<unsafe>" not in f.render()
    assert "<unsafe>" not in f.render_css()
