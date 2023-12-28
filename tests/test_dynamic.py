import pytest

from cntxt.manager import dynamic
from cntxt.wrappers import fix


def test_create():
    wrapped = dynamic({})
    assert isinstance(wrapped, dict)
    assert wrapped == {}
    assert wrapped.__subject__ == {}

    wrapped["a"] = 1
    assert wrapped.__subject__ == {"a": 1}
    assert wrapped["a"] == 1

    def child():
        assert wrapped["a"] == 1

        wrapped["a"] = {"b": 2}
        assert wrapped["a"]["b"] == 2
        assert wrapped["a"] == {"b": 2}

        a = wrapped["a"]
        assert a == {"b": 2}

        b = a["b"]
        c = int(a["b"])
        d = fix(a["b"])
        assert b == c == d == 2  # In this scope b looks the same as the "static" c and d

        return a, b, c, d

    a, b, c, d = child()

    assert wrapped["a"] == 1

    assert a == 1
    with pytest.raises(AttributeError, match="'int' object has no attribute 'b'"):
        assert b == 2  # Trying to resolve a["b"] but in this scope a == 1
    assert c == 2
    assert d == 2
