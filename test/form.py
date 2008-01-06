import webtest
from web import form
 
class FormTest(webtest.TestCase):
    def testUnicode(self):
        t = form.Textbox('first_name', maxlength='255', description=u'\u1234', value=u'\u1234')
        f = form.Form(t)
        f.render() # this fails if unicode is not supported.

        t = form.Textbox('first_name', maxlength='255', description=u'\u1234', value=u'\u1234')
        t.note = u'\u1234'
        f = form.Form(t)
        f.render() # this fails if unicode is not supported.

if __name__ == "__main__":
    webtest.main()
