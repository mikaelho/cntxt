import copy
import inspect
from contextlib import contextmanager
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import is_dataclass
from typing import Self


class DictMixinMeta(type):
    def __getitem__(self, item):
        current_context = self._current_context()
        if not current_context:
            {}[item]  # noqa: raise IndexError
        return current_context[item]


class DataclassMixinMeta(type):
    def __new__(cls, *args, **kwargs):
        new_cls = super().__new__(cls, *args, **kwargs)
        return dataclass(new_cls)

    def __getattribute__(self, item):
        if item in ("_current_context", "_class_identifier"):
            return super().__getattribute__(item)
        current_context = self._current_context()
        if not current_context:
            return super().__getattribute__(item)
        return getattr(current_context, item)


class ContextMixin:

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
    def _class_identifier(cls):
        return f"_cntxt_{str(cls)}"

    @classmethod
    def _wrap_context_frame(cls, **ctx):
        current_frame = frame = inspect.currentframe().f_back.f_back
        while frame:
            if context_stack := frame.f_locals.get(cls._class_identifier(), []):
                break
            frame = frame.f_back
        else:
            frame = current_frame
            context_stack = []
        prev_context: Self = context_stack and context_stack[-1] or cls()
        context = prev_context._merge(ctx)
        context_stack.append(context)
        frame.f_locals[cls._class_identifier()] = context_stack

        yield

        context_stack.pop()
        if not context_stack:
            del frame.f_locals[cls._class_identifier()]

    def _merge(self, ctx):
        if is_dataclass(self):
            new_dict = asdict(self)
        elif isinstance(self, dict):
            new_dict = copy.deepcopy(self)
        else:
            raise TypeError(f"Context class is not a dict or a dataclass but {type(self)}")
        new_dict.update(ctx)
        return type(self)(**new_dict)

    @classmethod
    def _current_context(cls) -> Self | None:
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
