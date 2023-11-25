import time
from dataclasses import is_dataclass
from threading import Thread

from cntxt import context
from cntxt import Context


class Ctx(Context):
    a: int = None
    b: str = None


class SubValue(Context):
    e: int = None


class Ctx2(Context):
    c: int = None
    d: SubValue = None


def test_dict_based_context():
    """
    Check that dict-based contexts are created, updated and dropped as expected.
    """

    assert context._current_context() is None

    with context.set(a=1, b=1):
        assert context["a"] == 1
        assert context["b"] == 1

        with context.set(a=2):
            assert context["a"] == 2
            assert context["b"] == 1

        assert context["a"] == 1
        assert context["b"] == 1

    assert context._current_context() is None


def test_object_based_context():
    """
    Check that contexts get created, updated and dropped as expected.

    Also check that our Context-based contexts are internally dataclasses.
    """

    assert is_dataclass(Ctx)

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
    """
    Check that several layers of function calls work as expected.
    """
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
    """
    Check that contexts are separate even if inherited from the same Context class.
    """

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


# def test_sub_contexts():  # TODO
#     c = Ctx2(c=1, d=SubValue(e=2))
#     assert asdict(c) == {'c': 1, 'd': {'e': 2}}
#     new_c = Ctx2(**asdict(c))
#
#     assert new_c.d.e == 2


def test_wrap():
    """
    Check operation of the method for wrapping an existing function in a context.
    """
    def some_func(a):
        assert a == 0
        assert Ctx.a == 1

    some_func = Ctx.wrap(some_func, a=1)

    some_func(0)


def test_double_wrap():
    """
    Check that wrapping a wrapped function creates no surprises.
    """
    def some_func(a):
        assert a == 0
        assert Ctx.a == 1
        assert Ctx.b == 2

    some_func = Ctx.wrap(some_func, a=1)
    some_func = Ctx.wrap(some_func, b=2)

    some_func(0)


def test_thread_safety__calling_thread():
    """
    Confirm that thread stacks are separate.

    Non-captured exceptions generate visible warnings in pytest.
    """
    def thread():
        # Context is not passed from the calling thread
        assert Ctx.a is None

    with Ctx.set(a=1):
        assert Ctx.a == 1
        Thread(target=thread).start()


def test_thread_safety__between_threads():
    """
    Really confirm that thread stacks are separate.
    """
    def thread(delay_before_start, delay_after_get):
        with Ctx.set(a=1):
            time.sleep(delay_before_start)
            with Ctx.set(a=Ctx.a + 1):
                time.sleep(delay_after_get)
                assert Ctx.a == 2

    (thread1 := Thread(target=thread, args=(0.05, 0.3))).start()
    (thread2 := Thread(target=thread, args=(0.1, 0.1))).start()
    thread1.join()
    thread2.join()


def test_recursion():
    """
    Check that nothing surprising happens with recursion.
    """

    # Define a recursive function with a regular counter for asserting that context behaves as expected.
    def recursive(counter=0):
        counter += 1
        with Ctx.set(a=Ctx.a + 1 if Ctx.a else 1):
            assert Ctx.a == counter
            if Ctx.a < 10:
                return recursive(counter)
            else:
                return counter

    counter = recursive()

    assert counter == 10
    assert Ctx.a is None
