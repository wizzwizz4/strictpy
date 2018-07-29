import sys
import itertools
import ctypes
import types
import functools
import enum
import warnings

#####################
# Utility functions #
#####################
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
    __strict__'s values are some OR'd enums that will have meaning later. For
    now it'll just mean "whether I've stored a descriptor or not".
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

        if key not in __strict__:
            # Lazy evaluation!
            warnings.warn("strict (type checking etc.) didn't run for {key} "
                          "when it was first set",
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

class Attribute(enum.Flag):
    NONE = 0
    DESCRIPTOR = enum.auto()
    UNOPTIMISABLE = enum.auto()

set_hooks = {}

############
# Features #
############

class FunctionDescriptor:
    def __init__(self, f):
        self.function = f
        # TODO: Set prototype from f.__code__.co_varnames and __annotations__

    def __get__(self, instance, type_):
        return self.function

    def __set__(self, instance, value):
        raise NotImplementedError("I'll do this later!")

    def __set_name__(self, owner, name):
        print("This is called!")
        self.name = name

def function_hook(f):
    try:
        module = sys.modules[f.__module__]
    except KeyError:
        warnings.warn(f"Module {f.__module__} isn't in sys.modules!",
                      category=ImportWarning, stacklevel=3)
    else:
        if not isinstance(module.__dict__, ModuleGlobals):
            return None
    if all(name in f.__annotations__ for name in
           f.__code__.co_varnames + ("return",)):
        return FunctionDescriptor(f), Attribute.DESCRIPTOR
    raise ValueError("Your function needs annotations!")

set_hooks[types.FunctionType] = function_hook

#########
# Setup #
#########
if __name__ == "strict":
    # Get target module
    target_name = get_target_name()
    target = sys.modules[target_name]
    warnings.warn(f"You are importing strict from {target_name}!",
                  category=ImportWarning, stacklevel=2)

    # Rewrite globals to be a ModuleGlobals subclass
    reclass_object(target.__dict__, ModuleGlobals)
    dict.__setitem__(target.__dict__, '__strict__',
                     {'__strict__': Attribute.NONE,
                      '__name__': Attribute.NONE})  # Set __strict__.

    # Retcon import strict
    for key in target.__dict__:
        # Run __setitem__ on everything
        if key != '__name__':
            value = dict.__getitem__(target.__dict__, key)
            dict.__delitem__(target.__dict__, key)
            target.__dict__[key] = value
