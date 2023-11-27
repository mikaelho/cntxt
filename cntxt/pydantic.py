from pydantic.dataclasses import dataclass

from cntxt import ContextMixin
from cntxt import DataclassMixinMeta


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
