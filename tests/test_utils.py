from web import utils


def test_group():
    assert list(utils.group([], 2)) == []
    assert list(utils.group([1, 2, 3, 4, 5, 6, 7, 8, 9], 3)) == [
        [1, 2, 3],
        [4, 5, 6],
        [7, 8, 9],
    ]
    assert list(utils.group([1, 2, 3, 4, 5, 6, 7, 8, 9], 4)) == [
        [1, 2, 3, 4],
        [5, 6, 7, 8],
        [9],
    ]


class TestIterBetter:
    def test_iter(self):
        assert list(utils.IterBetter(iter([]))) == []
        assert list(utils.IterBetter(iter([1, 2, 3]))) == [1, 2, 3]
