import copy
import inspect
import uuid
from contextlib import contextmanager
from dataclasses import asdict
from dataclasses import is_dataclass
from typing import Self


_cntxt_context_stack_variable = f"_cntxt_{uuid.uuid4}"


# class ClassGetter(type):
#     def __getitem
#     def now(cls) -> "ContextMixin":
#         frame = inspect.currentframe()
#         while frame:
#             context_stack = frame.f_locals.get(_cntxt_context_stack_variable)
#             if context_stack:
#                 return context_stack[-1]
#             frame = frame.f_back
#         return None


class classproperty:
    def __init__(self, func):
        self.fget = func

    def __get__(self, instance, owner):
        return self.fget(owner)


class DictMixinMeta(type):
    def __getitem__(self, item):
        current_context = self.now
        if not current_context:
            {}[item]  # noqa: raise IndexError
        return current_context[item]


class DataclassMixinMeta(type):
    def __getattribute__(self, item):
        if item == "_current_context":
            return super().__getattribute__(item)
        current_context = self._current_context()
        if not current_context:
            return super().__getattribute__(item)
        return getattr(current_context, item)


class ContextMixin:

    @classmethod
    @contextmanager
    def set(cls, **kwargs):
        return cls._wrap_context_frame(**kwargs)

    @classmethod
    def _wrap_context_frame(cls, **kwargs):
        current_frame = frame = inspect.currentframe().f_back.f_back
        while frame:
            if context_stack := frame.f_locals.get(_cntxt_context_stack_variable, []):
                break
            frame = frame.f_back
        else:
            frame = current_frame
            context_stack = []
        prev_context: Self = context_stack and context_stack[-1] or cls()
        context = prev_context._merge(kwargs)
        context_stack.append(context)
        frame.f_locals[_cntxt_context_stack_variable] = context_stack

        yield

        context_stack.pop()
        if not context_stack:
            del frame.f_locals[_cntxt_context_stack_variable]

    def _merge(self, kwargs):
        if is_dataclass(self):
            new_dict = asdict(self)
        elif isinstance(self, dict):
            new_dict = copy.deepcopy(self)
        else:
            raise TypeError(f"Context class is not a dict or a dataclass but {type(self)}")
        new_dict.update(kwargs)
        return type(self)(**new_dict)

    @classproperty
    def now(cls) -> Self | None:
        return cls._current_context()

    @classmethod
    def _current_context(cls) -> Self | None:
        frame = inspect.currentframe()
        while frame:
            context_stack = frame.f_locals.get(_cntxt_context_stack_variable)
            if context_stack:
                return context_stack[-1]
            frame = frame.f_back
        return None

class DictMixin(ContextMixin, metaclass=DictMixinMeta):
    pass


class DataclassMixin(ContextMixin, metaclass=DataclassMixinMeta):
    pass
