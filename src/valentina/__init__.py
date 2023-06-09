"""This module is the entry point of the bot. save version."""

from .bot import Valentina
from .main import CONFIG, DATABASE
from .utils.character_service import CharacterService

char_svc = CharacterService()

__all__ = [
    "DATABASE",
    "Valentina",
    "CONFIG",
    "char_svc",
]
