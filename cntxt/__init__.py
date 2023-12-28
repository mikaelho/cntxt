import copy
import inspect
from contextlib import contextmanager
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import fields
from dataclasses import is_dataclass
from types import SimpleNamespace
from typing import Self


__all__ = "context", "Context", "DictContext"

from typing import TypeVar

from cntxt.manager import Manager
from cntxt.wrappers import wrap_target


def locals_key(instance):
    return f"_dynascope_{str(type(instance))}"


T = TypeVar("T")


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



class ContextStack(list):
    pass


class IdentifiedClass:
    @classmethod
    def _class_identifier(cls):
        # return f"_cntxt_{str(cls)}"
        return cls


class Stack:

    def __init__(self, stack_class=None, dataclass_converter=dataclass):
        if stack_class:
            if not is_dataclass(stack_class):
                stack_class = dataclass_converter(stack_class)
            inspect.currentframe().f_back.f_locals[locals_key(self)] = [stack_class()]
        else:
            stack_class = SimpleNamespace
        self._stack_class = stack_class

    def __getattribute__(self, key):
        print(self, key)
        if key in ("_stack_class", "set", "_get_scope_dict"):
            return object.__getattribute__(self, key)

        frame = inspect.currentframe()
        while frame := frame.f_back:
            if scopes := frame.f_locals.get(locals_key(self)):
                return object.__getattribute__(scopes[-1], key)

        return object.__getattribute__(self, key)

    def __setattr__(self, key, value):
        print(self, key, value)
        if key == "_stack_class":
            object.__setattr__(self, key, value)
            return

        previous_scope_dict = self._get_scope_dict(inspect.currentframe())

        current_scopes = inspect.currentframe().f_back.f_locals.setdefault(locals_key(self), [])
        new_scope_dict = update_dict(previous_scope_dict, **{key: value})
        current_scopes.append(self._stack_class(**new_scope_dict))

    @contextmanager
    def set(self, **kwargs):
        previous_scope_dict = self._get_scope_dict(inspect.currentframe().f_back)

        current_locals = inspect.currentframe().f_back.f_back.f_locals
        current_scopes = current_locals.setdefault(locals_key(self), [])
        items_before_block = len(current_scopes)

        new_scope_dict = update_dict(previous_scope_dict, **kwargs)
        current_scopes.append(self._stack_class(**new_scope_dict))

        yield

        current_locals[locals_key(self)] = current_scopes[:items_before_block]

    def _get_scope_dict(self, frame):
        while frame := frame.f_back:
            if previous_scopes := frame.f_locals.get(locals_key(self)):
                previous_scope = previous_scopes[-1]
                if is_dataclass(previous_scope):
                    return asdict(previous_scope)
                else:
                    return previous_scope.__dict__
        else:
            return {}


class DataclassStack(Stack):
    def __new__(cls, *args, **kwargs):
        datacls = super().__new__(dataclass(cls))
        datacls.__init__(*args, **kwargs)
        return datacls

    def __setattr__(self, key, value):
        print(key, "-", value)
        # Plain attribute setting when initializing
        frame = inspect.currentframe()
        while frame:
            print("-", frame.f_code.co_qualname)
            if frame.f_code.co_qualname == f"DataclassStack.__new__":
                object.__setattr__(self, key, value)
                return
            frame = frame.f_back

        # Set values in stack if part of dataclass fields
        if any(key == field.name for field in fields(self)):
            super().__setattr__(key, value)
            return

        raise AttributeError(f"{key} is not an attribute of {type(self)}")


stack = Stack()


# class DataclassStack:
#     def __getattribute__(self, key):
#         # if key.startswith("_"):
#         #     return super().__getattribute__(key)
#         if key in [field.name for field in fields(self)]:
#             frame = inspect.currentframe()
#             while frame := frame.f_back:
#                 if scopes := frame.f_locals.get(self):
#                     return object.__getattribute__(scopes[-1], key)
#         return super().__getattribute__(key)
#
#     def __setattr__(self, key, value):
#         ...


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
