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

class Any(_Immutable):
    """Subclass and superclass of all types, instance and type of all objects.
    """
    # TODO: Override isinstance and issubclass
    __slots__ = ()

    def __instancecheck__(self, obj):
        return True

    def __subclasscheck__(self, cls):
        return True

class Callable(type, _Immutable):
    # TODO: Add Callable[] support.
    __slots__ = ()

    def __instancecheck__(self, obj):
        return callable(obj)

    def __subclasscheck__(self, cls):
        return (hasattr(cls, '__call__')
                and not hasattr(type(cls), '__call__')
                or cls.__call__ != type(cls).__call__(cls))

class ClassVar(_Immutable):
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

    def __subclasscheck__(self, cls):
        return issubclass(cls, self.type)

class Optional:
    __slots__ = ()

    @_tp_cache
    def __class_getitem__(cls, type_):
        return Union(type_, None)

class Tuple(tuple):
    __slots__ = ()

    def __new__(cls, iterable=()):
        if not hasattr(cls, '_types'):
            return tuple.__new__(tuple, iterable)
        self = super().__new__(cls, iterable)
        if not isinstance(self, cls):
            raise ValueError("The iterable doesn't have the right types. "
                             "Tuple[A, B] means a tuple of form (A(), B()). "
                             "You probably meant to use Sequence, if this is "
                             "an unexpected error.")
        return self

    def __class_getitem__(cls, types_):
        return _DifferentiatedTuple(types_)

class _DifferentiatedTuple(type):
    # Subclasses of type can't have __slots__.

    _types: 'Sequence[type]'

    def __new__(cls, types_):
        return super().__new__(
            cls,
            f"Tuple[{types_!r}]",
            (Tuple,),
            {}
        )

    def __init__(self, types_):
        self._types = types_

    def __instancecheck__(cls, obj):
        if not hasattr(cls, '_types'):
            # TODO: Make generic.
            return isinstance(obj, tuple)
        try:
            if len(obj) != len(cls._types):
                return False
            return all(map(isinstance, obj, cls._types))
        except TypeError:
            return False

    def __subclasscheck__(self, cls):
        # TODO: Make generic.
        return issubclass(cls, tuple)

class Union:
    __slots__ = ('_types')
    
    @_tp_cache
    def __class_getitem__(cls, types_):
        return cls(*types_)

    def __init__(self, *types_):
        if types_ == (Any,):
            types_ == [Any]
        else:
            types_ = [type(None) if cls is None else cls
                      for cls in types_
                      if cls is not Any]

        # Flatten
        i = 0
        while i < len(types_):
            if isinstance(types_[i], Union):
                types_[i:i+1] = types_[i]._types
                continue
            # TODO: Implement Sequence[type] so that this works.
##            if isinstance(types_[i], Sequence[type]):
##                types_[i:i+1] = types_[i]
##                continue
            if not isinstance(types_[i], type):
                raise ValueError(f"Union arguments must be type, not "
                                 f"{type(types_[i])!r}")
            i += 1

        # Remove superclasses.
        i = 0
        while i < len(types_):
            if any(
                types_[i] in type(cls).mro(cls)
                for cls in types_
                if cls is not types_[i]
            ):
                del types_[i]
                continue
            i += 1

        # Deduplicate
        i = 0
        while i < len(types_):
            if types_[i] in types_[:i]:
                del types_[i]
                continue
            i += 1

        self._types = tuple(types_)

    def __repr__(self):
        return f"{self.__class__.__qualname__}[{repr(self._types)[1:-1]}]"

    def __instancecheck__(self, obj):
        return isinstance(obj, self._types)

    def __subclasscheck__(self, cls):
        return issubclass(cls, self._types)
