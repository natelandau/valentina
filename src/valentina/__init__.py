"""This module is the entry point of the bot."""

from .__version__ import __version__
from .bot import Valentina
from .main import DATABASE

__all__ = [
    "__version__",
    "DATABASE",
    "Valentina",
]
