from pydantic.dataclasses import dataclass

from cntxt import ContextMixin
from cntxt import DataclassMixinMeta
from cntxt import Stack


class PydanticStack(Stack):

    def __init__(self, stack_class=None):
        super().__init__(stack_class=stack_class, dataclass_converter=dataclass)


class PydanticDataclassMixinMeta(DataclassMixinMeta):
    def __new__(cls, *args, **kwargs):
        return super().__new__(cls, *args, use_dataclass=dataclass, **kwargs)


class Context(ContextMixin, metaclass=PydanticDataclassMixinMeta):
    """
    Pydantic Context class.

    Is also a pydantic dataclass, with all the associated behavior and support for validation and
    nested context updates.
    """
    pass
