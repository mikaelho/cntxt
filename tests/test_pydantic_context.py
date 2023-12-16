import pytest

from cntxt.pydantic import Context


class Ctx(Context):
    a: int = None
    b: str | None = None


class SubValue(Context):
    e: int = None


class Ctx2(Context):
    c: int = None
    d: SubValue | None = None


def test_pydantic_based_context():
    """
    Check that contexts get created, updated and dropped as expected.
    """
    assert Ctx._current_scope() is None

    with Ctx.set(a=1, b="b"):
        assert Ctx.a == 1
        assert Ctx.b == "b"

        with Ctx.set(a=2):
            assert Ctx.a == 2
            assert Ctx.b == "b"

        assert Ctx.a == 1
        assert Ctx.b == "b"

    assert Ctx._current_scope() is None


def test_direct_modification_not_allowed():
    with pytest.raises(RuntimeError):
        Ctx.a = 4
    assert Ctx.a is None

    with Ctx.set(a=1):
        assert Ctx.a == 1

        with pytest.raises(RuntimeError):
            Ctx.a = 3

        assert Ctx.a == 1
    assert Ctx.a is None


def test_nested_context_updates():
    with Ctx2.set(c=1):
        assert Ctx2.c == 1
        with Ctx2.set(d=SubValue(e=1)):
            assert Ctx2.d.e == 1
            with Ctx2.set(d__e=2):
                assert Ctx2.d.e == 2
