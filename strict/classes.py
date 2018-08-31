"""Strictpy class handling. Introduces private and protected attributes.

private means that it can only be accessed from the defining class (not even
  subclasses)
protected means that it can be accessed from the class, subclasses and anywhere
  in the package

In Python, these are __attribute and _attribute, respectively. Calling this
module's register function will cause builtins.__build_class__ to be rewritten.
"""

import builtins
from builtins import __build_class__
import sys
import re
import typing
import itertools
import types

from .utils import get_target_name, is_strict_module

__all__ = ['register']

def register():
    builtins.__build_class__ = build_class

def build_class(func, name, *bases, metaclass=None, **kwds):
    if is_strict_module(sys.modules[func.__module__]):
        if bases and bases[-1] == object:
            bases = bases[-1:] + (PrivateProtectedClass, object)
        else:
            bases += PrivateProtectedClass,
    if metaclass is None:
        return __build_class__(func, name, *bases, **kwds)
    else:
        return __build_class__(func, name, *bases, metaclass=metaclass, **kwds)

private_regex = re.compile(r'_(?P<class>.*?)__(?P<name>.*)')

class PrivateProtectedClass:
    __slots__ = ()
    def __getattribute__(self, key):
        block_invalid_pripro_access(self, key, '__getattribute__')
        return super().__getattribute__(key)

    def __setattr__(self, key, value):
        block_invalid_pripro_access(self, key, '__setattr__')
        super().__setattr__(key, value)

def block_invalid_pripro_access(self: PrivateProtectedClass,
                                key: str, name: str,
                                depth: int=0) -> None:
    if key[0] == '_':
        mro = type(type(self)).mro(type(self))
        frame = climb_super_chain(
            mro,
            name,
            depth=1 + depth
        )
        match = private_regex.match(key)
        if match is None:
            # TODO: Protected
            print("Protected!")
        else:
            # Private
            for cls in mro:
                if method_defined_on(cls, frame):
                    break
            else:
                raise AttributeError(f"Attempted to access private "
                                     f"attribute {key!r} with a hack. "
                                     f"Specifically, name mangling. "
                                     f"If you really want to do this, use "
                                     f"object.__getattribute__(obj, key) or "
                                     f"unittest.mock.patch('builtins.super'); "
                                     f"the latter's better because it'll still"
                                     f"runs other __[gs]etattribute__s. Also, "
                                     f"press Ctrl+Alt+M and type "
                                     f"strict.classes.")
            if cls.__name__ != match['class']:
                raise AttributeError(f"Attempted to access private "
                                     f"attribute {key!r} from class "
                                     f"{cls!r}")

def climb_super_chain(mro: typing.Sequence[type], name: str,
                      depth: int=0) -> types.FrameType:
    # WARNING: If ctypes code comes between, and actually the lower-down code
    # was called by a C class (most common case being a C class gets an
    # attribute of an instance of PrivateProtectedClass, and a subclass of
    # PrivateProtectedClass' __getattribute__ calls something on the C object
    for depth in itertools.count(1 + depth):
        frame = sys._getframe(depth)
        for cls in mro:
            if method_defined_on(cls, frame):
                old_type = cls
                break
        else:
            break
        if name != frame.f_code.co_name:
            break
    return frame

# Thanks to SO user Aran-Fey for contributing the technique used to detect
# whether a method belongs to a particular class.
# https://stackoverflow.com/a/52076636/5223757
def method_defined_on(cls: type, frame: types.FrameType) -> bool:
    c = frame.f_code
    for thing in vars(cls).values():
        if getattr(thing, '__code__', None) is c:
            return True
    return False
