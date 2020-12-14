import web.utils
import web
import web.db
import web.py3helpers
import web.webapi
import web.debugerror
import web.net
import web.template
import web.form
import web.http
import web.httpserver
import web.session
import web.wsgi
import web.application
import web.browser


def test_init_CaptureStdout_0():
    var = web.utils.CaptureStdout(None)
    ret = var
    assert isinstance(ret, web.utils.CaptureStdout)


def test_repr_Counter_0():
    var = web.utils.Counter()
    ret = var.__repr__()
    assert ret is not None


def test_add_Counter_0():
    var = web.utils.Counter()
    ret = var.add(None)
    assert ret is None


def test_sorted_items_Counter_0():
    var = web.utils.Counter()
    ret = var.sorted_items()
    assert ret is not None


def test_sorted_values_Counter_0():
    var = web.utils.Counter()
    ret = var.sorted_values()
    assert ret is not None


def test_init_Profile_0():
    var = web.utils.Profile(None)
    ret = var
    assert isinstance(ret, web.utils.Profile)


def test_repr_Storage_0():
    var = web.utils.Storage()
    ret = var.__repr__()
    assert ret is not None


def test_del_ThreadedDict_0():
    var = web.utils.ThreadedDict()
    ret = var.__del__()
    assert ret is None


def test_setitem_ThreadedDict_0():
    var = web.utils.ThreadedDict()
    ret = var.__setitem__(None, None)
    assert ret is None


def test_copy_ThreadedDict_0():
    var = web.utils.ThreadedDict()
    ret = var.copy()
    assert ret is not None


def test_iter_ThreadedDict_0():
    var = web.utils.ThreadedDict()
    ret = var.iter()
    assert ret is not None


def test_iteritems_ThreadedDict_0():
    var = web.utils.ThreadedDict()
    ret = var.iteritems()
    assert ret is not None


def test_itervalues_ThreadedDict_0():
    var = web.utils.ThreadedDict()
    ret = var.itervalues()
    assert ret is not None


def test_pop_ThreadedDict_0():
    var = web.utils.ThreadedDict()
    ret = var.pop(None, None)
    assert ret is None


def test_setdefault_ThreadedDict_0():
    var = web.utils.ThreadedDict()
    ret = var.setdefault(None, None)
    assert ret is None


def test_values_ThreadedDict_0():
    var = web.utils.ThreadedDict()
    ret = var.values()
    assert ret is not None


def test_commify_0():
    ret = web.utils.commify(None)
    assert ret is None


def test_cond_0():
    ret = web.utils.cond(None, None, None)
    assert ret is None


def test_datestr_0():
    ret = web.utils.datestr(None, None)
    assert ret is not None


def test_intget_0():
    ret = web.utils.intget(None, None)
    assert ret is None


def test_numify_0():
    ret = web.utils.numify(None)
    assert ret is not None


def test_call_CaptureStdout_0():
    try:
        var = web.utils.CaptureStdout(None)
        var.__call__(None, None)
    except Exception as e:
        assert isinstance(e, TypeError)


def test_delattr_Counter_0():
    try:
        var = web.utils.Counter()
        var.__delattr__(None)
    except Exception as e:
        assert isinstance(e, AttributeError)


def test_least_Counter_0():
    try:
        var = web.utils.Counter()
        var.least()
    except Exception as e:
        assert isinstance(e, AttributeError)


def test_most_Counter_0():
    try:
        var = web.utils.Counter()
        var.most()
    except Exception as e:
        assert isinstance(e, ValueError)


def test_percent_Counter_0():
    try:
        var = web.utils.Counter()
        var.percent(None)
    except Exception as e:
        assert isinstance(e, KeyError)


def test_bool_IterBetter_0():
    try:
        var = web.utils.IterBetter(None)
        var.__bool__()
    except Exception as e:
        assert isinstance(e, TypeError)


def test_getitem_IterBetter_0():
    try:
        var = web.utils.IterBetter(None)
        var.__getitem__(None)
    except Exception as e:
        assert isinstance(e, TypeError)


def test_first_IterBetter_0():
    try:
        var = web.utils.IterBetter(None)
        var.first(None)
    except Exception as e:
        assert isinstance(e, TypeError)


def test_call_Profile_0():
    try:
        var = web.utils.Profile(None)
        var.__call__(None)
    except Exception as e:
        assert isinstance(e, TypeError)


def test_delitem_ThreadedDict_0():
    try:
        var = web.utils.ThreadedDict()
        var.__delitem__(None)
    except Exception as e:
        assert isinstance(e, KeyError)


def test_popitem_ThreadedDict_0():
    try:
        var = web.utils.ThreadedDict()
        var.popitem()
    except Exception as e:
        assert isinstance(e, KeyError)


def test__strips_0():
    try:
        web.utils._strips(None, None, None)
    except Exception as e:
        assert isinstance(e, ValueError)


def test_dateify_0():
    try:
        web.utils.dateify(None)
    except Exception as e:
        assert isinstance(e, TypeError)


def test_dictfindall_0():
    try:
        web.utils.dictfindall(None, None)
    except Exception as e:
        assert isinstance(e, AttributeError)


def test_dictincr_0():
    try:
        web.utils.dictincr(None, None)
    except Exception as e:
        assert isinstance(e, AttributeError)


def test_dictreverse_0():
    try:
        web.utils.dictreverse(None)
    except Exception as e:
        assert isinstance(e, AttributeError)


def test_lstrips_0():
    try:
        web.utils.lstrips(None, None)
    except Exception as e:
        assert isinstance(e, AttributeError)


def test_nthstr_0():
    try:
        web.utils.nthstr(None)
    except Exception as e:
        assert isinstance(e, TypeError)


def test_requeue_0():
    try:
        web.utils.requeue(None, -1)
    except Exception as e:
        assert isinstance(e, AttributeError)


def test_restack_0():
    try:
        web.utils.restack(None, 0)
    except Exception as e:
        assert isinstance(e, AttributeError)


def test_rstrips_0():
    try:
        web.utils.rstrips(None, None)
    except Exception as e:
        assert isinstance(e, AttributeError)


def test_safewrite_0():
    try:
        web.utils.safewrite(None, None)
    except Exception as e:
        assert isinstance(e, TypeError)


def test_strips_0():
    try:
        web.utils.strips(None, None)
    except Exception as e:
        assert isinstance(e, AttributeError)


def test_to36_0():
    try:
        web.utils.to36(None)
    except Exception as e:
        assert isinstance(e, TypeError)


def test_tryall_0():
    try:
        web.utils.tryall(None, None)
    except Exception as e:
        assert isinstance(e, AttributeError)


def test_uniq_0():
    try:
        web.utils.uniq(None, None)
    except Exception as e:
        assert isinstance(e, TypeError)
