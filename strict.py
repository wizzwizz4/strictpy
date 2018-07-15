import sys
import itertools
import ctypes
import types

#####################
# Utility functions #
#####################
def get_target_name():
    for depth in itertools.count(2):
        target_name = sys._getframe(depth).f_globals["__name__"]
        if target_name[:20] == "importlib._bootstrap":
            continue
        return target_name

def replace_globals_in_frames(old, new):
    for depth in itertools.count():
        try:
            frame = sys._getframe(depth)
        except ValueError:
            return
        if frame.f_globals is old:
            magic_get_dict(frame)['f_globals'] = new

# The awesome hack from https://stackoverflow.com/a/24498525/5223757,
# modified slightly to include magic_set_dict
def magic_get_dict(o):
    # find address of dict whose offset is stored in the type
    dict_addr = id(o) + type(o).__dictoffset__

    # retrieve the dict object itself
    dict_ptr = ctypes.cast(dict_addr, ctypes.POINTER(ctypes.py_object))
    return dict_ptr.contents.value

def magic_set_dict(o, d):
    # find address of dict whose offset is stored in the type
    dict_addr = id(o) + type(o).__dictoffset__

    # retrieve the dict object itself
    old_dict_ptr = ctypes.cast(dict_addr, ctypes.POINTER(ctypes.py_object))

    # decrement refcount of original dict object
    ctypes.pythonapi.Py_DecRef(old_dict_ptr.contents)
    # and increment refcount of new dict object
    ctypes.pythonapi.Py_IncRef(ctypes.py_object(d))

    # overwrite pointer value
    ctypes.c_void_p.from_address(dict_addr).value = id(d)

def magic_flush_mro_cache():
    ctypes.PyDLL(None).PyType_Modified(ctypes.py_object(object))

########################
# Module globals stuff #
########################
class DescriptorGlobals(dict):
    __slots__ = ('module',)
    def __init__(self, *args, module, **kwargs):
        self.module = module
    
    def __getitem__(self, key):
        item = super().__getitem__(key)
        if hasattr(item, '__get__'):
            return item.__get__(self.module, self.module)
        return item

    def __setitem__(self, key, value):
        try:
            item = super().__getitem__(key)  # Don't run __get__
        except KeyError:
            # Set new descriptor?
            if hasattr(value, '__set_name__'):
                super().__setitem__(key, value)
                value.__set_name__(self.module, name)
                return
        if hasattr(item, '__set__'):
            item.__set__(self.module, value)
            return
        # Replace the not-descriptor
        # Make sure you check the type against __annotations__!
        super().__setitem__(key, value)

    def __delitem__(self, key):
        item = super().__getitem__(key)
        if hasattr(item, 'delete'):
            item.__delete__(self.module)
        super().__delitem__(key)

class FunctionGlobals(DescriptorGlobals):
    def __setitem__(self, key, value):
        if isinstance(value, types.FunctionType):
            # Check for __annotations__ etc., and error if not found.
            value = FunctionDescriptor(value)
        super().__setitem__(key, value)

class ModuleGlobals(FunctionGlobals,):
    pass  # Does nothing except be a subclass of all the features.

###############
# Descriptors #
###############

class FunctionDescriptor:
    pass

#########
# Setup #
#########
if __name__ == "strict":
    # Get target module
    target_name = get_target_name()
    target = sys.modules[target_name]

    # Create new globals
    old_vars = vars(target)
    new_vars = ModuleGlobals(module=target)
    new_vars.update(old_vars)

    # Set new globals in modules object
    magic_set_dict(target, new_vars)

    # Set new globals in frames
    replace_globals_in_frames(old_vars, new_vars)
