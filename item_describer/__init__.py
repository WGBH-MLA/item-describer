from importlib import metadata
try:
    __version__ = metadata.version("item-describer")
except ModuleNotFoundError:
    __version__ = "local"
