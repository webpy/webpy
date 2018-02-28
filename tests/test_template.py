import web

class TestRender:
    def test_template_without_ext(self, tmpdir):
        tmpdir.join("foobar").write("hello")
        render = web.template.render(str(tmpdir))
        assert str(render.foobar()).strip() == "hello"
