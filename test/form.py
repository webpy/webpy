"""DB test"""
from __future__ import print_function

import webtest
from web.form import Form, Textbox

class FormTest(webtest.TestCase):
    def test_id_escape_issue(self):
        f = Form(Textbox("x", id="x <unsafe>"))
        self.assertTrue("<unsafe>" not in f.render())
        self.assertTrue("<unsafe>" not in f.render_css())

if __name__ == '__main__':
    webtest.main()
