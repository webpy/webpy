import web
from web import http


class TestModified:
    def test_empty_cases(self, monkeypatch):
        monkeypatch.setattr(web, 'ctx', web.storage(env={}))
        assert http.modified() is True
