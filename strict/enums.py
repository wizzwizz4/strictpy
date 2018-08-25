"""Strictpy enums."""

import enum

__all__ = ['Attribute']

class Attribute(enum.Flag):
    NONE = 0
    DESCRIPTOR = enum.auto()
    UNOPTIMISABLE = enum.auto()
