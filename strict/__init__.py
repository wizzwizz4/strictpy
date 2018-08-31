"""Strictpy bootstrap module."""

import sys
import warnings
import inspect
import typing

from . import utils, singletons
from .enums import Attribute
from .functions import register as register_functions
from .classes import register as register_classes

########################
# Module globals stuff #
########################
class ModuleGlobals(dict):
    """Uninstantiable drop-in replacement for a module's globals.
    
    Adds a new entry to the dictionary: __strict__. That's documented below:
    __strict__'s keys are the same as the keys for the variables that have been
    processed. That means that assignments will be processed lazily. In Python
    3.5 this isn't necessary because they hadn't done as much optimisation, but
    now they have this is necessary.
    __strict__'s values are OR'd Attributes.
    """
    __slots__ = ()  # Don't create a __dict__ for this dict!
                    # That would be weird. (And cause a segfault.)
    def __new__(cls, *args, **kwargs):
        raise RuntimeError("This is magic; it shouldn't be instantiated!")
    
    def __getitem__(self, key):
        print("__getitem__", key)
        module = sys.modules[super().__getitem__('__name__')]
        __strict__ = super().__getitem__('__strict__')
        item = super().__getitem__(key)

        if key not in __strict__ or __strict__[key] & Attribute.UNOPTIMISABLE:
            # Lazy evaluation!
            warnings.warn(f"strict (type checking etc.) didn't run for {key} "
                          f"when it was first set",
                          category=RuntimeWarning, stacklevel=2)
            value = super().__getitem__(key)
            super().__delitem__(key)
            self[key] = value
            assert key in __strict__
            __strict__[key] |= Attribute.UNOPTIMISABLE
        
        if __strict__[key] & Attribute.DESCRIPTOR:
            return item.__get__(module, module)
        return item

    def __setitem__(self, key, value):
        print("__setitem__", key, value)
        module = sys.modules[super().__getitem__('__name__')]
        __strict__ = super().__getitem__('__strict__')
        # Stop import strict from actually importing strict.
        # This also means that it can be run more than once, so long as the
        # user didn't import strict as something else.
        if key == "strict":
            if "strict" in sys.modules:
                strict = sys.modules["strict"]
                if value is strict:
                    del sys.modules["strict"]
                    return
        try:
            item = super().__getitem__(key)  # Get the actual stored object
        except KeyError:
            pass  # If not defined, or if not descriptor, run below code.
        else:
            if __strict__[key] & Attribute.DESCRIPTOR:
                item.__set__(module, value)
                return
        # Run set hooks, if they exist.
        for type_ in type(value).__mro__:
            if type_ in set_hooks:
                # set hooks can return None, which means that the next set hook
                # in the mro should handle it.
                processed = set_hooks[type_](value)
                if processed is not None:
                    value, attribute = processed
                    super().__setitem__(key, value)
                    __strict__[key] = attribute
                    return
        # Set hooks don't exist, so just set the item.
        # Make sure you check the type against __annotations__!
        super().__setitem__(key, value)
        __strict__[key] = Attribute.NONE

    def __delitem__(self, key):
        print("__delitem__", key)
        module = sys.modules[super().__getitem__('__name__')]
        item = super().__getitem__(key)
        if hasattr(item, 'delete'):
            item.__delete__(module)
        super().__delitem__(key)

singletons.ModuleGlobals = ModuleGlobals

set_hooks = {}
singletons.set_hooks = set_hooks

#####################
# Register features #
#####################
register_functions()
register_classes()

#########
# Setup #
#########
if __name__ == "strict":
    typing.TYPE_CHECKING = True  # Does nothing in and of itself...
                                 # but it's a documented signal.

    # Get target module
    target_name = utils.get_target_name()
    target = sys.modules[target_name]
    warnings.warn(f"You are importing strict from {target_name}!",
                  category=ImportWarning, stacklevel=2)

    # Rewrite globals to be a ModuleGlobals subclass
    utils.reclass_object(target.__dict__, ModuleGlobals)
    dict.__setitem__(target.__dict__, '__strict__',
                     {'__strict__': Attribute.NONE,
                      '__name__': Attribute.NONE})  # Set __strict__.

    # Retcon import strict
    for key in target.__dict__:
        # Run __setitem__ on everything
        if key not in ('__name__', '__strict__'):
            value = dict.__getitem__(target.__dict__, key)
            dict.__delitem__(target.__dict__, key)
            target.__dict__[key] = value
