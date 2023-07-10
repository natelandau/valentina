"""This module is the entry point of the bot. save version."""

from .__version__ import __version__
from .bot import Valentina
from .main import CONFIG, DATABASE
from .models.database_services import (
    CharacterService,
    ChronicleService,
    DatabaseService,
    GuildService,
    TraitService,
    UserService,
)

char_svc = CharacterService()
user_svc = UserService()
guild_svc = GuildService()
chron_svc = ChronicleService()
db_svc = DatabaseService(DATABASE)
trait_svc = TraitService()

__all__ = [
    "DATABASE",
    "Valentina",
    "CONFIG",
    "chron_svc",
    "db_svc",
    "guild_svc",
    "char_svc",
    "trait_svc",
    "user_svc",
    "__version__",
]
