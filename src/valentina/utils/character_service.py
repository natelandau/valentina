"""Character Manager cache/in-memory database."""
from loguru import logger
from peewee import ModelSelect

from valentina.models.database import Character, Guild


class CharacterService:
    """A service for managing the Character Manager cache/in-memory database."""

    def __init__(self) -> None:
        """Initialize the CharacterService."""
        # Caches to avoid database queries
        ##################################

        # Cache all guilds and their row numbers (foreign keys)
        self.guild_db_ids: dict[int, int] = {}  # {guild_id: db_id, ...}

    def __guild_db_id_from_cache(self, guild_id: int) -> int:
        """Return the guild database id."""
        if guild_id not in self.guild_db_ids:
            try:
                logger.info(f"DATABASE: Fetch guild {guild_id} from db")
                foreign_key = Guild.get(Guild.guild_id == guild_id).id
                self.guild_db_ids[guild_id] = foreign_key
            except Guild.DoesNotExist as e:
                logger.error(f"DATABASE: Guild {guild_id} does not exist in database.")
                raise ValueError(f"Guild {guild_id} does not exist in database") from e

        return self.guild_db_ids[guild_id]

    def fetch_all(self, guild_id: int) -> ModelSelect:
        """Returns all characters for a specific guild in the database.

        Args:
            guild_id (int): The discord guild id to fetch characters for.
        """
        g = self.__guild_db_id_from_cache(guild_id)

        characters = Character.select().where((Character.guild_id == g) & (Character.archived == 0))
        logger.info(f"DATABASE: Fetched {len(characters)} characters for guild {guild_id}")

        return characters
