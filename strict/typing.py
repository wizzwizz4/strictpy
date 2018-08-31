"""Strictpy extra types and ABCs."""

import types
from typing import _tp_cache

__all__ = [
    # Super-special typing primitives.
    'Any',
    'Callable',
    'ClassVar',
    'Optional',
    'Tuple',
    'Type',
    'TypeVar',
    'Union'
]

class _Immutable:
    """Typing's implementation of this was perfect, except that it didn't
    define __slots__..."""
    __slots__ = ()

    def __copy__(self):
        return self

    def __deepcopy__(self, memo):
        return self

class Any:
    """Subclass and superclass of all types, instance and type of all objects.
    """
    # TODO: Override isinstance and issubclass
    __slots__ = ()

    def __instancecheck__(self, obj):
        return True

    def __subclasscheck__(self, cls):
        return True

class Callable(type):
    # TODO: Add Callable[] support.
    __slots__ = ()

    def __instancecheck__(self, obj):
        return callable(obj)

    def __subclasscheck__(self, cls):
        return (hasattr(cls, '__call__')
                and not hasattr(type(cls), '__call__')
                or cls.__call__ != type(cls).__call__(cls))

class ClassVar:
    """Indicates a class, rather than an instance, variable."""
    # TODO: Update .classes to check this too!
    __slots__ = ('type')

    @_tp_cache
    def __class_getitem__(cls, type_):
        return cls(type_)

    def __init__(self, type_):
        self.type = type_

    def __instancecheck__(self, obj):
        return isinstance(obj, self.type)

    def __subclasscheck__(self, obj):
        return issubclass(obj, self.type)

class Union:
    __slots__ = ('types')
    
    @_tp_cache
    def __class_getitem__(cls, *types_):
        return cls(*types_)

    def __init__(self, *types_):
        types_ = list(types_)
        # Deduplicate and mro thingy and stuff.
