import asyncio
import time
from asyncio import TaskGroup
from dataclasses import asdict
from dataclasses import is_dataclass
from threading import Thread

import pytest

from cntxt import Stack
from cntxt import context
from cntxt import Context
from cntxt import dynamic
from cntxt import stack


class Ctx(Context):
    a: int = None
    b: str = None


class SubValue(Context):
    e: int = None


class Ctx2(Context):
    c: int = None
    d: SubValue = None


variable_with_global_module_scope = 1

def test_scopes():

    global variable_with_global_module_scope

    variable_with_global_module_scope = 2

    def main():

        def func(variable_with_lexical_local_scope):
            assert variable_with_lexical_local_scope == 1
            assert variable_with_global_module_scope == 2
            assert variable_with_lexical_enclosing_scope == 3
            with pytest.raises(NameError):
                assert variable_with_dynamic_scope == 4

        def func_earlier_in_the_call_stack():
            variable_with_dynamic_scope = 4
            func(variable_with_lexical_local_scope=1)

        variable_with_lexical_enclosing_scope = 3

        func_earlier_in_the_call_stack()

    main()


def test_dynamic():
    stack = dynamic(dict())

    stack["a"] = 1
    stack["b"] = {"c": {"d": 2}}

    c = stack["b"]["c"]

    c["d"] = 3

    assert False


def test_dynamic_scope():
    with pytest.raises(AttributeError):
        stack.not_set  # noqa

    def enclosing_func():
        stack.b = 1
        stack.a = 1
        func(1)

    def func(expected_value):
        assert stack.a == expected_value
        assert stack.b == 1

    stack.b = 1
    stack.a = 2
    func(2)
    enclosing_func()


def test_compare_with_global_scope():
    global a

    def enclosing_func():
        global a
        a = 1
        func()

    def func():
        global a
        assert a == 1

    a = 2
    enclosing_func()
    func()
    assert a == 1


def test_compare_with_lexical_scope():
    def enclosing_func():
        a = 1
        func()

    def func():
        assert a == 2

    a = 2
    enclosing_func()
    func()
    assert a == 2


def test_stack_with_deep_values():
    stack.a = {"b": 1, "c": 1}

    stack.a__b = 2

    assert stack.a == {"b": 2, "c": 1}


def test_stack_with_context():
    stack.a = 1

    with stack.set(a=2):
        assert stack.a == 2

    assert stack.a == 1


def test_deep_values_with_context():
    stack.a = {"b": 1}

    with stack.set(a__b=2):
        assert stack.a == {"b": 2}

    assert stack.a == {"b": 1}


def test_stack_with_values_set_within_context_block():
    stack.a = 1

    with stack.set(a=2):
        assert stack.a == 2
        stack.a = 3
        assert stack.a == 3

    assert stack.a == 1


def test_stack_with_multiple_levels_of_contexts_and_functions():
    def func1():
        stack.a = 2
        with stack.set(a=3):
            func2()

    def func2():
        assert stack.a == 3
        with stack.set(a=4):
            stack.a = 5
            assert stack.a == 5
        assert stack.a == 3

    stack.a = 1
    func1()
    assert stack.a == 1


def test_dataclass_stack():
    class Conf:
        hostname: str = "https://host.net"

    conf = Stack(Conf)

    assert conf.hostname == "https://host.net"

    def calling_func():
        conf.hostname = "https://newhost.net"
        func()

    def func():
        assert conf.hostname == "https://newhost.net"

    calling_func()

    with pytest.raises(TypeError):
        conf.port = 80


def test_dict_based_context():
    """
    Check that dict-based contexts are created, updated and dropped as expected.
    """

    assert context._current_scope() is None

    with context.set(a=1, b=1):
        assert context["a"] == 1
        assert context["b"] == 1

        with context.set(a=2):
            assert context["a"] == 2
            assert context["b"] == 1

        assert context["a"] == 1
        assert context["b"] == 1

    assert context._current_scope() is None


def test_nested_references__dict_based_context():
    with context.set(a={"b": 1}):
        assert context["a"]["b"] == 1
        with context.set(a__b=2):
            assert context["a"]["b"] == 2


def test_object_based_context():
    """
    Check that Context-based contexts get created, updated and dropped as expected.

    Also check that they are internally dataclasses.
    """

    assert is_dataclass(Ctx)

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
        assert asdict(Ctx._current_scope()) == {"a": 1, "b": None}
    assert Ctx.a is None


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

    assert Ctx._current_scope() is None
    assert Ctx2._current_scope() is None

    with Ctx.set(a=1):
        assert Ctx.a == 1
        assert Ctx2._current_scope() is None

        with Ctx2.set(c=2):
            assert Ctx.a == 1
            assert Ctx2.c == 2

            with Ctx.set(b="b"), Ctx2.set(c=1):
                assert Ctx.a == 1
                assert Ctx.b == "b"
                assert Ctx2.c == 1


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


def test_asyncio():
    """
    Test context behavior with asyncio:
    - acyncio.run() inherits the enclosing context (stack)
    - Workers need to be configured as a group, or inside the (top-level) worker function
    """
    with Ctx.set(a=1):
        async def worker(b_should_be: str):
            assert Ctx.a == 1
            assert Ctx.b == b_should_be
            with Ctx.set(b="d"):
                assert Ctx.b == "d"

        async def main():
            with Ctx.set(b="b"):
                async with TaskGroup() as group:
                    group.create_task(worker(b_should_be="b"))
                    with Ctx.set(b="c"):
                        # Tasks are executed in the "group" context, not in this context
                        assert Ctx.b == "c"
                        group.create_task(worker(b_should_be="b"))

        asyncio.run(main())


def test_recursion():
    """
    Check that nothing surprising happens with recursion.
    """
    assert Ctx.a is None

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
