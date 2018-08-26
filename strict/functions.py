"""Strictpy function handling."""

import sys
import types
import warnings
import inspect
import textwrap
import ast
import typing
import functools

from .enums import Attribute
from . import singletons

__all__ = ['register']

def register() -> None:
    singletons.set_hooks[types.FunctionType] = function_hook

class Prototype:
    __slots__ = ('margs', 'oargs', 'mkwargs', 'okwargs', 'args', 'kwargs')
    margs: typing.Mapping[str, typing.Tuple[type]]
    oargs: typing.Mapping[str, typing.Tuple[type, object]]
    mkwargs: typing.Mapping[str, typing.Tuple[type]]
    okwargs: typing.Mapping[str, typing.Tuple[type, object]]
    args: bool
    kwargs: bool

    def __init__(self, f: types.FunctionType):
        c = f.__code__
        argnames = c.co_varnames[:c.co_argcount]
        kwargnames = c.co_varnames[c.co_argcount :
                                   c.co_argcount + c.co_kwonlyargcount]
        try:
            noargs = len(f.__defaults__)
        except TypeError:
            noargs = 0
        self.margs = {k: (f.__annotations__[k],)
                      for k in argnames[:-noargs]}
        if noargs:
            self.oargs = {k: (f.__annotations__[k], f.__defaults__[k])
                          for k in argnames[-noargs:]}
        else:
            self.oargs = {}

        try:
            nokwargs = len(f.__kwdefaults__)
        except TypeError:
            nokwargs = 0
        self.mkwargs = {k: (f.__annotations__[k],)
                        for k in kwargnames[:-nokwargs]}
        if nokwargs:
            self.okwargs = {k: (f.__annotations__[k], f.__defaults__[k])
                            for k in kwargnames[-nokwargs:]}
        else:
            self.okwargs = {}

        self.args = c.co_flags | 0x0004 > 0
        self.kwargs = c.co_flags | 0x0008 > 0

    def __eq__(self, other):
        return (self.margs == other.margs
                and self.oargs == other.oargs
                and self.mkwargs == other.mkwargs
                and self.okwargs == other.okwargs
                and self.args == other.args
                and self.kwargs == other.kwargs)

class FunctionDescriptor:
    def __init__(self, f):
        if not all(name in f.__annotations__ for name in
                   f.__code__.co_varnames + ("return",)):
            raise ValueError("Your function needs annotations!")

        # Set prototype from f.__code__.co_varnames and __annotations__
        self.prototype = Prototype(f)

        # TODO: Create a copy of the function, preserving variable annotations
        self.function = f
        return

        try:
            source_code = inspect.getsource(f)
        except OSError:
            warnings.warn(f"Couldn't get source for function {f.__qualname__}",
                          category=RuntimeWarning, stacklevel=4)
            self.function = f
        else:
            # TODO: Finish implementing this!
            tree = ast.parse(textwrap.dedent(source_code)).body[0]

            code = compile(self.get_body(f),
                           f.__code__.co_filename,
                           "exec",
                           f.__code__.co_flags,
                           True)

            self.function = f


    def __get__(self, instance, type_):
        @functools.wraps(self.function)
        def f(*args, **kwargs):
            mandatory = True
            for i, arg in enumerate(args):
                if mandatory:
                    pass
        return self.function

    def __set__(self, instance, value):
        if self.prototype != Prototype(value):
            raise ValueError("Conflicting prototype during "
                             "function reassignment.")

    def __set_name__(self, owner, name):
        print("This is called!")
        self.name = name

    @staticmethod
    def get_body(f: types.FunctionType):
        raise ValueError("This is dangerously naive.")
        source_code = inspect.getsource(f)

        index = source_code.index('(')
        depth = 1
        while depth:
            index += 1
            if source_code[index] == '(':
                depth += 1
            elif source_code[index] == ')':
                depth -= 1
        source_code = source_code[index+2:]  # ): is 2 chars.

        return textwrap.dedent(source_code).strip('\n')

def function_hook(f: int) -> (FunctionDescriptor, Attribute):
    try:
        module = sys.modules[f.__module__]
    except KeyError:
        warnings.warn(f"Module {f.__module__} isn't in sys.modules!",
                      category=ImportWarning, stacklevel=3)
    else:
        if not isinstance(module.__dict__, singletons.ModuleGlobals):
            return None
    return FunctionDescriptor(f), Attribute.DESCRIPTOR
