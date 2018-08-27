"""Strictpy utility functions."""

import sys
import itertools
import ctypes
import types

from . import singletons

__all__ = ['get_target_name', 'reclass_object', 'magic_set_pointer',
           'magic_get_dict_address', 'magic_get_dict', 'magic_set_dict',
           'magic_flush_mro_cache', 'is_strict_module']

def get_target_name(depth: int=0) -> str:
    for depth in itertools.count(2 + depth):
        target_name = sys._getframe(depth).f_globals["__name__"]
        if "importlib" in target_name:
            # Please nobody game this you will only have yourself to blame
            # when your program fails because you decided to call it
            # my_awesome_module_written_in_python_with_loads_of_features_\
            # like_importing_other_modules_with_importlib_and_making_programs_\
            # that_work_properly_but_it_doesnt_really
            continue
        return target_name

def reclass_object(obj: object, new_class: type) -> None:
    old_class = obj.__class__
    for offset in range(0, obj.__sizeof__(),
                        ctypes.sizeof(ctypes.c_void_p)):
        # This assumes alignment of the pointers.
        # WARNING: May cause segfault. If it doesn't,
        # you're really lucky!
        address = id(obj) + offset
        if ctypes.c_void_p.from_address(address).value == id(old_class):
            magic_set_pointer(address, new_class)
            # Don't break; I don't know how many references there might be!
            # This will probably not cause too many problems.
    assert obj.__class__ is new_class

def magic_set_pointer(address: int, new_obj: object) -> None:
    # retrieve the original object
    old_pyobj = ctypes.cast(address, ctypes.POINTER(ctypes.py_object)).contents
    
    # decrement refcount of original object
    ctypes.pythonapi.Py_DecRef(old_pyobj)
    # and increment refcount of new object
    ctypes.pythonapi.Py_IncRef(ctypes.py_object(new_obj))

    # overwrite pointer value
    ctypes.c_void_p.from_address(address).value = id(new_obj)

# The awesome hack from https://stackoverflow.com/a/24498525/5223757,
# modified slightly to include magic_set_dict and to make more safe
def magic_get_dict_address(o: object) -> int:
    """Safely get the address of the dictionary!
    
    See documentation for PyTypeObject.tp_dictoffset for details."""
    address = ctypes.pythonapi._PyObject_GetDictPtr(ctypes.py_object(o))
    if address == 0:
        raise TypeError(f"Objects of type {type(o)} don't have a dictionary!")
    return address

def magic_get_dict(o: object) -> dict:
    # find address of dict whose offset is stored in the type
    dict_addr = magic_get_dict_address(o)

    # retrieve the dict object itself
    dict_ptr = ctypes.cast(dict_addr, ctypes.POINTER(ctypes.py_object))
    return dict_ptr.contents.value

def magic_set_dict(o: object, d: dict) -> None:
    # find address of dict whose offset is stored in the type
    dict_addr = magic_get_dict_address(o)

    magic_set_pointer(dict_addr, d)

def magic_flush_mro_cache() -> None:
    ctypes.PyDLL(None).PyType_Modified(ctypes.py_object(object))

def is_strict_module(module: types.ModuleType) -> bool:
    return isinstance(module.__dict__, singletons.ModuleGlobals)
