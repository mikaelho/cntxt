import copy
import inspect
from contextlib import contextmanager
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import is_dataclass
from typing import Self


__all__ = "context", "Context", "DictContext"


class ContextStack(list):
    pass


class IdentifiedClass:
    @classmethod
    def _class_identifier(cls):
        return f"_cntxt_{str(cls)}"


class Stack(IdentifiedClass):
    def __getattribute__(self, item):
        if item == "_class_identifier":
            return super().__getattribute__(item)
        identifier = type(self)._class_identifier()
        frame = inspect.currentframe()
        while frame := frame.f_back:
            if scope := frame.f_locals.get(identifier):
                if value := scope.get(item):
                    return value
        return super().__getattribute__(item)

    def __setattr__(self, key, value):
        identifier = type(self)._class_identifier()
        stack_locals = inspect.currentframe().f_back.f_locals
        scope = stack_locals.get(identifier) or dict()
        scope[key] = value
        stack_locals[identifier] = scope


stack = Stack()


class DictMixinMeta(type):
    def __getitem__(self, item):
        current_scope = self._current_scope()
        if not current_scope:
            {}[item]  # noqa: raise IndexError
        return current_scope[item]


class DataclassMixinMeta(type):
    def __new__(cls, *args, use_dataclass=dataclass, **kwargs):
        new_cls = super().__new__(cls, *args, **kwargs)
        as_dataclass = use_dataclass(new_cls)
        return as_dataclass

    def __getattribute__(self, item):
        if item in ("_current_scope", "_class_identifier"):
            return super().__getattribute__(item)
        current_scope = self._current_scope()
        if not current_scope:
            return super().__getattribute__(item)
        return getattr(current_scope, item)

    def __setattr__(self, key, value):
        """
        Only support setting attributes on initialization.
        """
        frame = inspect.currentframe()
        while frame:
            if frame.f_code.co_qualname == f"DataclassMixinMeta.__new__":
                super().__setattr__(key, value)
                break
            frame = frame.f_back
        else:
            raise RuntimeError("Set context values only in context manager set() method")


class ContextMixin(IdentifiedClass):

    @classmethod
    @contextmanager
    def set(cls, **ctx):
        return cls._wrap_context_frame(**ctx)

    @classmethod
    def wrap(cls, func, **ctx):
        def wrapper(*args, **kwargs):
            with cls.set(**ctx):
                return func(*args, **kwargs)

        return wrapper

    @classmethod
    def _wrap_context_frame(cls, **ctx):
        current_frame = frame = inspect.currentframe().f_back.f_back
        while frame:
            if context_stack := frame.f_locals.get(cls._class_identifier()):
                break
            frame = frame.f_back
        else:
            frame = current_frame
            context_stack = ContextStack()

        prev_context: Self = context_stack and context_stack[-1] or cls()
        updated_context = prev_context._merge(ctx)
        context_stack.append(updated_context)
        frame.f_locals[cls._class_identifier()] = context_stack

        yield

        context_stack.pop()
        if not context_stack:
            del frame.f_locals[cls._class_identifier()]


    def _merge(self, ctx):
        if is_dataclass(self):
            new_dict = update_dict(asdict(self), **ctx)
        elif isinstance(self, dict):
            new_dict = update_dict(self, **ctx)
        else:
            raise TypeError(f"Context class is not a dict or a dataclass but {type(self)}")

        new_context = type(self)(**new_dict)

        return new_context


    @classmethod
    def _current_scope(cls) -> Self | None:
        frame = inspect.currentframe()
        while frame:
            context_stack = frame.f_locals.get(cls._class_identifier())
            if context_stack:
                return context_stack[-1]
            frame = frame.f_back
        return None


class Context(ContextMixin, metaclass=DataclassMixinMeta):
    """
    Default Context class.

    Is also a dataclass, with all the associated behavior.
    """
    pass


class DictContext(ContextMixin, metaclass=DictMixinMeta):
    pass


class context(dict, DictContext):
    """
    Default convenience dict-based context
    """
    pass


REMOVED = object()


def update_dict(dct, **updates):
    """
    Updates nested dict values with Django-like query syntax. Returns an updated copy of the original dict.

    If some parameter has value REMOVED, it is removed from the dict.

    Example:
        >>> dct = {"a": {"b": 1}, "c": [1, 2], "d": 3}
        >>> update_dict(dct, a__b=4, c__0=5, c__1=REMOVED, d=REMOVED, e=6, f={"g": 1})
        {'a': {'b': 4}, 'c': [5], 'e': 6, 'f': {'g': 1}}
    """
    copy_of_dct = copy.deepcopy(dct)

    for key, value in updates.items():
        node = copy_of_dct
        key_parts = key.split("__")
        for i, key_part in enumerate(key_parts, 1):
            if key_part.isdigit():
                key_part = int(key_part)

            if i < len(key_parts):  # Not a leaf node
                node = node[key_part]
            else:
                if value is REMOVED:
                    try:
                        node.pop(key_part)
                    except (IndexError, KeyError):
                        pass
                else:
                    node[key_part] = value

    return copy_of_dct
