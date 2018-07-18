import sys
import itertools
import ctypes
import types
import functools

#####################
# Utility functions #
#####################
def get_target_name():
    for depth in itertools.count(2):
        target_name = sys._getframe(depth).f_globals["__name__"]
        if "importlib" in target_name:
            # Please nobody game this you will only have yourself to blame
            # when your program fails because you decided to call it
            # my_awesome_module_written_in_python_with_loads_of_features_\
            # like_importing_other_modules_with_importlib_and_making_programs_\
            # that_work_properly_but_it_doesnt_really
            continue
        return target_name

def reclass_object(obj, new_class):
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

def magic_set_pointer(address, new_obj):
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
def magic_get_dict_address(o):
    """Safely get the address of the dictionary!
    
    See documentation for PyTypeObject.tp_dictoffset for details."""
    address = ctypes.pythonapi._PyObject_GetDictPtr(ctypes.py_object(o))
    if address == 0:
        raise TypeError("Objects of type {} don't have a dictionary!"
                        .format(type(o)))
    return address

def magic_get_dict(o):
    # find address of dict whose offset is stored in the type
    dict_addr = magic_get_dict_address(o)

    # retrieve the dict object itself
    dict_ptr = ctypes.cast(dict_addr, ctypes.POINTER(ctypes.py_object))
    return dict_ptr.contents.value

def magic_set_dict(o, d):
    # find address of dict whose offset is stored in the type
    dict_addr = magic_get_dict_address(o)

    magic_set_pointer(dict_addr, d)

def magic_flush_mro_cache():
    ctypes.PyDLL(None).PyType_Modified(ctypes.py_object(object))

########################
# Module globals stuff #
########################
class ModuleGlobals(dict):
    __slots__ = ()
    def __new__(cls, *args, **kwargs):
        raise RuntimeError("This is magic; it shouldn't be instantiated!")
    
    def __getitem__(self, key):
        module = sys.modules[super().__getitem__('__name__')]
        item = super().__getitem__(key)
        if hasattr(item, '__get__'):
            return item.__get__(module, module)
        return item

    def __setitem__(self, key, value):
        module = sys.modules[super().__getitem__('__name__')]
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
            item = super().__getitem__(key)  # Don't run __get__
        except KeyError:
            # Run set hooks
            for type_ in type(value).__mro__:
                if type_ in set_hooks:
                    processed = set_hooks[type_](value)
                    if processed is not None:
                        super().__setitem__(key, processed)
                        return
            else:
                # Set new descriptor?
                if hasattr(value, '__set_name__'):
                    super().__setitem__(key, value)
                    value.__set_name__(module, name)
                    return
        else:
            if hasattr(item, '__set__'):
                item.__set__(module, value)
                return
        # Replace the not-descriptor
        # Make sure you check the type against __annotations__!
        super().__setitem__(key, value)

    def __delitem__(self, key):
        module = sys.modules[super().__getitem__('__name__')]
        item = super().__getitem__(key)
        if hasattr(item, 'delete'):
            item.__delete__(module)
        super().__delitem__(key)

set_hooks = {}

############
# Features #
############

class FunctionDescriptor:
    def __init__(self, f):
        self.function = f

    def __get__(self, instance, type_):
        return self.function
set_hooks[types.FunctionType] = FunctionDescriptor

#########
# Setup #
#########
if __name__ == "strict":
    # Get target module
    target_name = get_target_name()
    target = sys.modules[target_name]

    # Rewrite globals to be a ModuleGlobals subclass
    reclass_object(target.__dict__, ModuleGlobals)

    # Retcon import strict
    for key in target.__dict__:
        # Run __setitem__ on everything
        if key != '__name__':
            value = dict.__getitem__(target.__dict__, key)
            dict.__delitem__(target.__dict__, key)
            target.__dict__[key] = value
