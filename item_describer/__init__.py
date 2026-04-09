"""
item_describer/__init__.py
"""

from importlib import metadata
try:
    __version__ = metadata.version("item-describer")
except ModuleNotFoundError:
    __version__ = "local"

# package-level API
from .idescribe import idescribe
__all__ = [ idescribe ]
