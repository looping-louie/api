"""Convenient access to the combined instruction catalog."""

from .instructions import InstructionOrigin
from .loader import load_instruction_catalog


__all__ = [
    "InstructionOrigin",
    "load_instruction_catalog",
]
