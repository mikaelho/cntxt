import copy
import inspect
import threading
from collections.abc import MutableMapping
from collections.abc import MutableSequence
from collections.abc import MutableSet
from typing import Any
from typing import TypeVar

from cntxt.wrappers import DynamicObject
from cntxt.wrappers import wrap_target


T = TypeVar("T")


class Manager:

    LOCK_TIMEOUT = 1.0

    def __init__(self, initial_value, frame):
        self.initial_value = initial_value
        self.root_type = type(initial_value)

        self.add_to_stack(initial_value, frame)

        self.lock = threading.RLock()

    @property
    def locals_key(self):
        return f"_dynascope_{str(self.root_type)}"

    def get_subject(self, path, frame):
        root_value = self.get_from_stack(frame)
        return self.get_value_by_path(root_value, path)

    def get_plain_value(self, frame, path):
        root_value = self.get_from_stack(frame)
        return self.get_value_by_path(root_value, path)

    def get_value(self, frame, path):
        value = self.get_plain_value(frame, path)
        return wrap_target(value, path, self)

    def mutate(self, frame, path, function_name, args, kwargs):
        stack_value = self.get_from_stack(frame)
        new_value = copy.deepcopy(stack_value)
        value_for_mutation = self.get_value_by_path(new_value, path)
        result = getattr(value_for_mutation, function_name)(*args, **kwargs)
        self.add_to_stack(new_value, frame)
        return wrap_target(result, path, self)

    def add_to_stack(self, obj, frame):
        frame.f_locals.setdefault(self.locals_key, []).append(obj)

    def get_from_stack(self, frame) -> Any | None:
        while frame:
            previous_scopes = frame.f_locals.get(self.locals_key)
            if previous_scopes:
                return previous_scopes[-1]
            frame = frame.f_back

        return self.initial_value

    def lock_acquire(self):
        if not self.lock.acquire(timeout=self.LOCK_TIMEOUT):
            raise RuntimeError(f'Trying to acquire lock for: {self.root_type}')

    def lock_release(self):
        self.lock.release()

    @staticmethod
    def get_value_by_path(obj, path: list):
        path = path.copy()

        while path:
            key = path.pop(0)
            if isinstance(obj, (MutableSequence, MutableMapping)):
                obj = obj[key]
            elif isinstance(obj, MutableSet):
                obj = key
            else:
                obj = object.__getattribute__(obj, key)
        return obj


def dynamic(
    target: T,
) -> T:
    """
    Tag target data structure to get notified of any changes.

    Return value is a proxy type, but type hinted to match the tagged object for editor convenience.
    """
    if type(target) is type:
        target = target()

    frame = inspect.currentframe().f_back
    manager = Manager(target, frame)
    wrapped = wrap_target(target, [], manager)

    return wrapped


def is_dynamic(obj):
    return isinstance(obj, DynamicObject)


def fix(obj):
    if is_dynamic(obj):
        obj = obj.__subject__
    return copy.deepcopy(obj)


class Stack:
    """Empty object container."""
    pass


stack = dynamic(Stack)
