"""Strictpy function handling."""

import sys
import types
import warnings
import inspect
import textwrap
import ast
import typing

from .enums import Attribute
from . import singletons

__all__ = ['register']

def register() -> None:
    singletons.set_hooks[types.FunctionType] = function_hook

class Prototype:
    __slots__ = ('margs', 'oargs', 'mkwargs', 'okwargs', 'args', 'kwargs')
    margs: typing.Sequence[str]
    oargs: typing.Mapping[str, object]
    mkwargs: typing.Sequence[str]
    okwargs: typing.Mapping[str, object]
    args: bool
    kwargs: bool

    def __init__(self, f: types.FunctionType):
        pass

class FunctionDescriptor:
    def __init__(self, f):
        if not all(name in f.__annotations__ for name in
                   f.__code__.co_varnames + ("return",)):
            raise ValueError("Your function needs annotations!")

        # Create a copy of the function, preserving variable annotations
        try:
            source_code = inspect.getsource(f)
        except OSError:
            warnings.warn(f"Couldn't get source for function {f.__qualname__}",
                          category=RuntimeWarning, stacklevel=4)
            self.function = f
        else:
            tree = ast.parse(textwrap.dedent(source_code)).body[0]

            code = compile(self.get_body(f),
                           f.__code__.co_filename,
                           "exec",
                           f.__code__.co_flags,
                           True)

            self.function = f

        # Set prototype from f.__code__.co_varnames and __annotations__
        self.prototype = Prototype(f)

    def __get__(self, instance, type_):
        return self.function

    def __set__(self, instance, value):
        raise NotImplementedError("I'll do this later!")

    def __set_name__(self, owner, name):
        print("This is called!")
        self.name = name

    @staticmethod
    def get_body(f: types.FunctionType):
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
