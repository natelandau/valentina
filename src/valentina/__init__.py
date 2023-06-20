"""This module is the entry point of the bot. save version."""

from .__version__ import __version__
from .bot import Valentina
from .main import CONFIG, DATABASE
from .models.database_services import CharacterService, GuildService, UserService

char_svc = CharacterService()
user_svc = UserService()
guild_svc = GuildService()

__all__ = ["DATABASE", "Valentina", "CONFIG", "guild_svc", "char_svc", "user_svc", "__version__"]
