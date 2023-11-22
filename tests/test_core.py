from dataclasses import dataclass

from cntxt import cntxt
from cntxt import DataclassMixin


@dataclass
class Ctx(DataclassMixin):
    a: int | None = None
    b: str | None = None


@dataclass
class SubValue:
    d: int | None = None


@dataclass
class Ctx2(DataclassMixin):
    c: int | None = None
    d: SubValue | None = None


def test_dict_context():
    assert cntxt._current_context() is None

    with cntxt.set(a=1, b=1):
        assert cntxt["a"] == 1
        assert cntxt["b"] == 1

        with cntxt.set(a=2):
            assert cntxt["a"] == 2
            assert cntxt["b"] == 1

        assert cntxt["a"] == 1
        assert cntxt["b"] == 1

    assert cntxt._current_context() is None


def test_dataclass_context():
    assert Ctx._current_context() is None

    with Ctx.set(a=1, b="b"):
        assert Ctx.a == 1
        assert Ctx.b == "b"

        with Ctx.set(a=2):
            assert Ctx.a == 2
            assert Ctx.b == "b"

        assert Ctx.a == 1
        assert Ctx.b == "b"

    assert Ctx._current_context() is None


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


def test_multiple_contexts():
    assert Ctx._class_identifier() != Ctx2._class_identifier()

    assert Ctx._current_context() is None
    assert Ctx2._current_context() is None

    with Ctx.set(a=1):
        assert Ctx.a == 1
        assert Ctx2._current_context() is None

        with Ctx2.set(c=2):
            assert Ctx.a == 1
            assert Ctx2.c == 2

            with Ctx.set(b="b"), Ctx2.set(c=1):
                assert Ctx.a == 1
                assert Ctx.b == "b"
                assert Ctx2.c == 1


def test_wrap():
    def some_func(a):
        assert a == 1
        assert Ctx.b == 2

    some_func = Ctx.wrap(some_func, b=2)

    some_func(1)
