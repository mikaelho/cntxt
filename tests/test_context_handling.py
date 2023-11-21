from dataclasses import dataclass

from cntxt import DataclassMixin
from cntxt import DictMixin


class ctx(dict, DictMixin):
    pass


@dataclass
class Ctx(DataclassMixin):
    a: int | None = None
    b: str | None = None


def test_dict_context():
    assert ctx.now is None

    with ctx.set(a=1, b=1):
        assert ctx["a"] == 1
        assert ctx["b"] == 1

        with ctx.set(a=2):
            assert ctx["a"] == 2
            assert ctx["b"] == 1

        assert ctx["a"] == 1
        assert ctx["b"] == 1

    assert ctx.now is None


def test_dataclass_context():
    assert Ctx.now is None

    with Ctx.set(a=1, b="b"):
        assert Ctx.a == 1
        assert Ctx.b == "b"

        with Ctx.set(a=2):
            assert Ctx.a == 2
            assert Ctx.b == "b"

        assert Ctx.a == 1
        assert Ctx.b == "b"

    assert Ctx.now is None


def test_multilevel():
    def func1():
        assert Ctx.a == 1
        assert Ctx.b == "b"

        func2()

    def func2():
        with Ctx.set(a=2):
            assert Ctx.a == 2
            assert Ctx.b == "b"

    with Ctx.set(a=1, b="b"):
        assert Ctx.a == 1
        assert Ctx.b == "b"
        func1()
