"""
Proxy wrappers for different data types to detect any changes.
"""

import copy
import inspect
from functools import partial
from typing import MutableMapping
from typing import MutableSequence
from typing import MutableSet
from typing import TypeVar

from cntxt.proxies import CallbackWrapper


T = TypeVar('T')


class DynamicObject(CallbackWrapper):

    def __init__(self, path, manager, osa=object.__setattr__):
        super().__init__(partial(manager.get_subject, path))

        osa(self, '_path', path)  # noqa
        osa(self, '_manager', manager)  # noqa

    def __repr__(self):
        return self.__subject__.__repr__()

    def __deepcopy__(self, memo):
        """
        Deepcopy mechanism is used to unwrap the wrapped data structure.
        """
        return copy.deepcopy(self.__subject__, memo)  # noqa

    def __enter__(self):
        self._manager.start_with_block()

        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._manager.end_with_block()

    # def __getattribute__(self, attr, oga=object.__getattribute__):
    #     subject = oga(self, "__subject__")
    #     if attr == "__subject__":
    #         return subject
    #     elif attr in ("_path", "_manager"):
    #         return oga(self, attr)
    #     return wrap_target(getattr(subject, attr), self._path + [attr], self._manager)

    def __getitem__(self, arg):
        return wrap_target(self.__subject__[arg], self._path + [arg], self._manager)


def is_dynamic(obj):
    return isinstance(obj, DynamicObject)


def fix(obj):
    if is_dynamic(obj):
        return obj.__subject__
    else:
        return obj


class DynamicMapping(DynamicObject):
    """
    Wrapper for MutableMappings.
    """


class DynamicSequence(DynamicObject):
    """
    Wrapper for MutableSequences.
    """


class DynamicSet(DynamicObject):
    """
    Wrapper for MutableSets.
    """


class DynamicCustomObject(DynamicObject):
    """ If an object has a __dict__ attribute, we track attribute changes. """


dynamic_types = {
    MutableSequence: DynamicSequence,
    MutableMapping: DynamicMapping,
    MutableSet: DynamicSet,
}

mutating_methods = {
    DynamicCustomObject: [
        '__setattr__', '__delattr__',  # '__iadd__', '__isub__', '__imul__', '__imatmul__', '__itruediv__',
        # '__ifloordiv__', '__imod__', '__ipow__', '__ilshift__', '__irshift__', '__iand__', '__ixor__', '__ior__',
    ],
    DynamicMapping: [
        '__setitem__', '__delitem__', 'pop', 'popitem', 'clear', 'update', 'setdefault',
    ],
    DynamicSequence: [
        '__setitem__', '__delitem__', 'insert', 'append', 'reverse', 'extend', 'pop', 'remove', 'clear', '__iadd__',
    ],
    DynamicSet: [
        'add', 'discard', 'clear', 'pop', 'remove', '__ior__', '__iand__', '__ixor__', '__isub__',
    ],
}

# Add tracking wrappers to all mutating functions.

for dynamic_type in mutating_methods:
    for func_name in mutating_methods[dynamic_type]:
        def func(self, *args, tracker_function_name=func_name, **kwargs):
            self._manager.lock_acquire()
            try:
                result = self._manager.mutate(
                    inspect.currentframe().f_back,
                    self._path,
                    tracker_function_name,
                    args,
                    kwargs,
                )
                return result

            finally:
                self._manager.lock.release()

        setattr(dynamic_type, func_name, func)
        getattr(dynamic_type, func_name).__name__ = func_name


def wrap_target(target: T, path: list, manager: "Manager") -> T:
    tracked = None
    is_object = False

    for abc, wrapper in dynamic_types.items():
        if isinstance(target, abc):
            tracked = wrapper(path, manager)
            break
    else:
        if type(target) is type:
            target = target()
        # if hasattr(target, '__dict__'):
        #     tracked = DynamicCustomObject(path + ['__dict__'], manager)
        #     is_object = True
        # else:
        tracked = DynamicObject(path, manager)

    # if not path:  # i.e. root
    #     manager.root = tracked
    #     manager.root_type = type(target)
    #     manager.instantiate_root_with_keywords = is_object

    # wrap_members(tracked)

    return tracked


def wrap_members(tracked: DynamicObject):
    """
    Checks to see if some of the changed node's contents now need to be tracked.
    """
    to_wrap = []
    path = tracked._path

    # if type(tracked) is DynamicCustomObject:
    #    path.append('__dict__')

    for key, value in get_iterable(tracked.__subject__):
        if is_dynamic(value):
            updated_path = path + [key]
            if value._path != updated_path:
                to_wrap.append((key, value.__subject__))
        elif should_wrap(value):
            to_wrap.append((key, value))
    for key, value in to_wrap:
        set_value(
            tracked.__subject__,
            key,
            value,
            wrap_target(value, path + [key], tracked._manager),
        )


def get_iterable(obj):
    """
    Attempts to return a (key, value) iterator regardless of object type.

    For class instances, only returns attributes that do not start with '_' (public attributes).
    """
    if isinstance(obj, MutableSequence):
        return enumerate(obj)
    elif isinstance(obj, MutableMapping):
        return obj.items()
    elif isinstance(obj, MutableSet):
        return ((value, value) for value in obj)
    elif hasattr(obj, '__dict__'):
        return ((key, value) for key, value in obj.__dict__.items() if not key.startswith('_'))
    else:
        raise TypeError(f'Cannot return an iterator for type {type(obj)}')


def should_wrap(contained):
    if isinstance(contained, DynamicObject):
        return False

    if isinstance(contained, tuple(dynamic_types.keys())):
        return True
    if hasattr(contained, "__dict__"):
        return True
    if hasattr(contained, "__hash__"):
        return False

    raise TypeError(f'Not a trackable or hashable type: {contained}')


def set_value(target, key, old_value, new_value):
    if isinstance(target, (MutableSequence, MutableMapping)):
        target[key] = new_value
    elif isinstance(target, MutableSet):
        target.remove(old_value)
        target.add(new_value)
    elif hasattr(target, "__dict__"):
        object.__setattr__(target, key, new_value)
    else:
        raise TypeError(f'Cannot set value for type {type(target)}')
