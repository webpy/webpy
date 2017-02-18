import web

print(web.__file__)

def test_storage():
    d = web.storage(a=1)

    assert d['a'] == 1
    assert d.a == 1

    d.a = 2
    assert d['a'] == 2

    del d.a
    assert 'a' not in d
