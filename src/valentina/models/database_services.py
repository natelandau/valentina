"""Models for maintaining in-memory caches of database queries."""

import discord
from loguru import logger
from peewee import ModelSelect

from valentina.models.database import Character, GuildUser, User, time_now


class CharacterService:
    """A service for managing the Character Manager cache/in-memory database."""

    def __init__(self) -> None:
        """Initialize the CharacterService."""
        # Caches to avoid database queries
        ##################################

        # Cache all guilds and their row numbers (foreign keys)
        self.guild_db_ids: dict[int, int] = {}  # {guild_id: db_id, ...}

    def fetch_all(self, guild_id: int) -> ModelSelect:
        """Returns all characters for a specific guild in the database.

        Args:
            guild_id (int): The discord guild id to fetch characters for.
        """
        try:
            characters = Character.select().where(
                (Character.guild_id == guild_id) & (Character.archived == 0)
            )
            logger.info(f"DATABASE: Fetched {len(characters)} characters for guild {guild_id}")
        except Character.DoesNotExist as e:
            logger.error(f"DATABASE: No characters found for guild {guild_id}")
            raise ValueError(f"No active characters found for guild {guild_id}") from e

        return characters

    def fetch_by_id(self, char_id: int) -> Character:
        """Fetch a character by database id.

        Args:
            char_id (int): The database id of the character.

        Returns:
            Character: The character object.
        """
        # TODO: Cache characters by id on bot startup and query the cache first
        try:
            character = Character.get_by_id(char_id)
            logger.info(
                f"DATABASE: Fetched character {char_id}:{character.first_name} from database"
            )
        except Character.DoesNotExist as e:
            logger.error(f"DATABASE: Character {char_id} does not exist in database.")
            raise ValueError(f"Character {char_id} does not exist in database") from e

        return character


class UserService:
    """User manager and in-memory cache."""

    def __init__(self) -> None:
        """Initialize the UserService."""
        self.users: dict[str, User] = {}  # {user_key: User, ...}

    @staticmethod
    def __get_key(guild_id: int, user_id: int) -> str:
        """Get the guild and user IDs.

        Args:
            guild_id (discord.Guild | int): The guild to get the ID for.
            user_id (discord.User | int): The user to get the ID for.

        Returns:
            str: The guild and user IDs joined by an underscore.
        """
        return f"{guild_id}_{user_id}"

    def purge(self) -> None:
        """Purge cache of all users."""
        self.users = {}

    def is_cached(self, guild_id: int, user_id: int) -> bool:
        """Check if the user is in the cache."""
        key = self.__get_key(guild_id, user_id)

        if key in self.users:
            return True

        return False

    def is_in_db(self, guild_id: int, user_id: int) -> bool:
        """Check if the user is in the database."""
        in_user_table = False
        in_guild_user_table = False

        if User.select().where(User.id == user_id).exists():
            in_user_table = True

        if (
            GuildUser.select()
            .where((GuildUser.guild_id == guild_id) & (GuildUser.user_id == user_id))
            .exists()
        ):
            in_guild_user_table = True

        if in_user_table and in_guild_user_table:
            return True

        return False

    def fetch(self, guild_id: int, user_id: int) -> User:
        """Fetch a user object from the cache or database."""
        key = self.__get_key(guild_id, user_id)

        if self.is_cached(guild_id, user_id):
            logger.info(f"CACHE: Returning user {key} from cache")
            return self.users[key]

        if self.is_in_db(guild_id, user_id):
            user = User.get_by_id(user_id)
            user.last_seen = time_now()
            user.save()
            self.users[key] = user
            logger.info(f"CACHE: Returning user {key} from the database and caching")
            return user

        logger.error(f"DATABASE: User {key} does not exist in database or the cache.")
        raise ValueError(f"User {key} does not exist in database or the cache.")

    def create(self, guild_id: int, user: discord.User | discord.Member) -> User:
        """Create a new user in the database and cache."""
        print(f"Creating user {user.id}-{user.name}")
        existing_user = User.get_or_none(id=user.id)
        if existing_user is None:
            logger.info(f"DATABASE: Created user {user.id} in database")
            new_user = User.create(id=user.id, username=user.name)
        else:
            new_user = User.get_by_id(user.id)

        existing_guild_user = GuildUser.get_or_none(guild_id=guild_id, user_id=user.id)
        if existing_guild_user is None:
            logger.info(f"DATABASE: Create guild_user lookup for user:{user.id} guild:{guild_id}")
            GuildUser.create(guild_id=guild_id, user_id=user.id)

        key = self.__get_key(guild_id, user.id)
        self.users[key] = new_user

        return new_user
