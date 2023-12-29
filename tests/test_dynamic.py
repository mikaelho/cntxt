from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field

from pydantic.dataclasses import dataclass as pydantic_dataclass
import pytest

from cntxt.manager import dynamic
from cntxt.manager import fix
from cntxt.manager import stack


def test_vanilla_scopes():

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


def test_dynamic_scope_added():

    global variable_with_global_module_scope

    variable_with_global_module_scope = 2

    def main():

        def func(variable_with_lexical_local_scope):
            assert variable_with_lexical_local_scope == 1
            assert variable_with_global_module_scope == 2
            assert variable_with_lexical_enclosing_scope == 3
            assert stack.variable_with_dynamic_scope == 4

        def func_earlier_in_the_call_stack():
            stack.variable_with_dynamic_scope = 4
            func(variable_with_lexical_local_scope=1)

        variable_with_lexical_enclosing_scope = 3

        func_earlier_in_the_call_stack()

    main()



def test_dynamic_dict():
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


def test_dynamic_dataclass():
    @dataclass
    class ServerSettings:
        host: str = ""

    @dataclass
    class Configuration:
        setting_1: int = 1
        server_settings: ServerSettings = field(default_factory=ServerSettings)

    conf = dynamic(Configuration)  # Or dynamic(Configuration())
    assert isinstance(conf, Configuration)
    assert asdict(fix(conf)) == {"server_settings": {"host": ""}, "setting_1": 1}
    assert conf.setting_1 == 1

    def child():
        conf.setting_1 = 2
        conf.server_settings.host = "https://example.com"
        assert conf.setting_1 == 2
        assert isinstance(conf.server_settings, ServerSettings)
        assert conf.server_settings.host == "https://example.com"

        return conf.setting_1, conf.server_settings

    setting_1, server_settings = child()

    assert conf.setting_1 == setting_1 == 1
    assert server_settings.host == ""


def test_context_manager():
    def child():
        assert stack.dynamic_variable == 3
        stack.dynamic_variable = 4

        with stack:
            stack.dynamic_variable = 5
            assert stack.dynamic_variable == 5

        assert stack.dynamic_variable == 4

    stack.dynamic_variable = 1

    with stack:
        stack.dynamic_variable = 2
        assert stack.dynamic_variable == 2

    assert stack.dynamic_variable == 1

    with stack:
        stack.dynamic_variable = 3
        child()
        assert stack.dynamic_variable == 3

    assert stack.dynamic_variable == 1
