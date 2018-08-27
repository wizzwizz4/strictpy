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

from .utils import get_target_name, is_strict_module

__all__ = ['register']

def register():
    builtins.__build_class__ = build_class

def build_class(func, name, *bases, metaclass=None, **kwds):
    if is_strict_module(sys.modules[get_target_name()]):
        bases += PrivateProtectedClass,
    if metaclass is None:
        return __build_class__(func, name, *bases, **kwds)
    else:
        return __build_class__(func, name, *bases, metaclass=metaclass, **kwds)

class PrivateProtectedClass:
    def __getattribute__(self, key):
        if key[0] == '_':
            print("TODO: Special behaviour here.")
            # TODO: Sniff for _XYZ__foo
            # TODO: Climb the super() chain to the original call.
            # TODO: Detect whether private or protected visibility applies.
            # TODO: Do the same for __setattribute__.
        return super().__getattribute__(key)
