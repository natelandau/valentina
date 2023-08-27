"""Models for maintaining in-memory caches of database queries."""

import discord
from loguru import logger

from valentina.models.db_tables import Character, CustomSection
from valentina.utils.helpers import time_now


class CharacterService:
    """A service for managing the Player characters in the cache/in-memory database."""

    def __init__(self) -> None:
        """Initialize the CharacterService.

        This method sets up three dictionaries that serve as caches to avoid unnecessary database queries.

        Attributes:
            characters (dict[str, Character]): A dictionary mapping character keys to Character instances.
            storyteller_character_cache (dict[int, list[Character]]): A dictionary mapping guild IDs to lists of Character instances.

        """
        # Initialize a dictionary to store characters, using character keys as keys and Character instances as values
        self.character_cache: dict[str, Character] = {}

        # Initialize a dictionary to store storyteller characters, using guild IDs as keys and lists of Character instances as values
        self.storyteller_character_cache: dict[int, list[Character]] = {}

    @staticmethod
    def __get_char_key(guild_id: int, char_id: int) -> str:
        """Generate a key for the character cache.

        Args:
            guild_id (int): The guild to get the ID for.
            char_id (int): The character database ID

        Returns:
            str: The guild and character IDs joined by an underscore.
        """
        # Generate a unique key for the character by joining the guild ID and character ID with an underscore
        return f"{guild_id}_{char_id}"

    def custom_section_update_or_add(
        self,
        ctx: discord.ApplicationContext,
        character: Character,
        section_title: str | None = None,
        section_description: str | None = None,
    ) -> CustomSection:
        """Update or add a custom section to a character.

        Args:
            ctx (ApplicationContext): The application context.
            character (Character): The character object to which the custom section will be added.
            section_title (str | None): The title of the custom section. Defaults to None.
            section_description (str | None): The description of the custom section. Defaults to None.

        Returns:
            CustomSection: The updated or created custom section.
        """
        # Purge the cache to ensure that stale data is not being used.
        self.purge_cache(ctx)

        section, created = CustomSection.get_or_create(
            title=section_title,
            description=section_description,
            character=character,
        )

        if not created:
            section.title = section_title
            section.description = section_description
            section.save()

            logger.debug(f"DATABASE: Update custom section for {character}")
        else:
            logger.debug(f"DATABASE: Add custom section to {character}")

        return section

    def set_character_default_values(self) -> None:
        """Set default values for all characters in the database."""
        characters = Character.select()
        for character in characters:
            character.set_default_data_values()

    def fetch_all_player_characters(self, guild_id: int) -> list[Character]:
        """Fetch all characters for a specific guild, checking the cache first and then the database.

        Args:
            guild_id (int): The Discord guild ID to fetch characters for.

        Returns:
            list[Character]: List of characters for the guild.
        """
        # Fetch characters from cache
        cached_chars = [
            character
            for key, character in self.character_cache.items()
            if key.startswith(f"{guild_id!s}_")
        ]
        cached_ids = [character.id for character in cached_chars]
        logger.debug(f"CACHE: Fetch {len(cached_chars)} characters")

        # Fetch characters from database not in cache
        characters = Character.select().where(
            (Character.guild_id == guild_id)
            & (Character.data["player_character"] == True)  # noqa: E712
            & (Character.id.not_in(cached_ids))
        )
        logger.debug(
            f"DATABASE: Fetch {len(characters)} characters"
            if characters
            else "DATABASE: No characters to fetch"
        )

        # Verify default values and add characters from database to cache
        for c in characters:
            character = c.set_default_data_values()
            key = self.__get_char_key(guild_id, character.id)
            self.character_cache[key] = character

        return cached_chars + list(characters)

    def fetch_all_storyteller_characters(
        self,
        ctx: discord.ApplicationContext | discord.AutocompleteContext = None,
        guild_id: int | None = None,
    ) -> list[Character]:
        """Fetch all StoryTeller characters for a guild, checking the cache first and then the database.

        Args:
            ctx (ApplicationContext | discord.AutocompleteContext, optional): Context object containing guild information.
            guild_id (int, optional): The Discord guild ID to fetch characters for. If not provided, it will be extracted from ctx.

        Returns:
            list[Character]: List of StoryTeller characters for the guild.
        """
        # Determine guild_id from the context if not provided
        if guild_id is None:
            if isinstance(ctx, discord.ApplicationContext):
                guild_id = ctx.guild.id
            elif isinstance(ctx, discord.AutocompleteContext):
                guild_id = ctx.interaction.guild.id

        # Initialize cache for guild_id if not present
        if guild_id not in self.storyteller_character_cache:
            self.storyteller_character_cache[guild_id] = []

        # Fetch cached characters' IDs
        cached_ids = [character.id for character in self.storyteller_character_cache[guild_id]]
        logger.debug(f"CACHE: Fetch {len(cached_ids)} StoryTeller characters")

        # Query the database for StoryTeller characters not in cache
        characters = Character.select().where(
            (Character.guild_id == guild_id)
            & (Character.data["storyteller_character"] == True)  # noqa: E712
            & (Character.id.not_in(cached_ids))
        )

        # Log the number of characters fetched from the database
        logger.debug(f"DATABASE: Fetch {len(characters)} StoryTeller characters")

        # Verify default values and add characters from database to cache
        for c in characters:
            character = c.set_default_data_values()
            self.storyteller_character_cache[guild_id].append(character)

        return self.storyteller_character_cache[guild_id]

    def is_cached_character(
        self, guild_id: int | None = None, char_id: int | None = None, key: str | None = None
    ) -> bool:
        """Check if the character is in the cache using either a guild ID and character ID or a specified key.

        Args:
            guild_id (int, optional): The guild ID of the character. Defaults to None.
            char_id (int, optional): The character ID. Defaults to None.
            key (str, optional): The key representing the character in the cache. If not provided, it will be generated using guild_id and char_id. Defaults to None.

        Returns:
            bool: True if the character is in the cache, False otherwise.
        """
        key = key or self.__get_char_key(guild_id, char_id)
        return key in self.character_cache

    def purge_cache(self, ctx: discord.ApplicationContext | None = None) -> None:
        """Purge all character caches. If ctx is provided, only purge the caches for that guild.

        Args:
            ctx (ApplicationContext | None, optional): Context object containing guild information. If provided, only caches for that guild are purged.

        Returns:
            None
        """
        # Initialize caches to purge
        caches: dict[str, dict] = {"characters": self.character_cache}

        if ctx:
            # Purge caches for the specific guild
            self.storyteller_character_cache.pop(ctx.guild.id, None)
            for cache in caches.values():
                keys_to_remove = [key for key in cache if key.startswith(f"{ctx.guild.id!s}_")]
                for key in keys_to_remove:
                    cache.pop(key, None)
            logger.debug(f"CACHE: Purge character caches for guild {ctx.guild}")
        else:
            # Purge all character caches
            self.storyteller_character_cache = {}
            for cache in caches.values():
                cache.clear()
            logger.debug("CACHE: Purge all character caches")

    def update_or_add(
        self,
        ctx: discord.ApplicationContext,
        data: dict[str, str | int | bool] | None = None,
        character: Character | None = None,
        **kwargs: str | int,
    ) -> Character:
        """Update or add a character.

        Args:
            ctx (ApplicationContext): The application context.
            data (dict[str, str | int | bool] | None): The character data.
            character (Character | None): The character to update, or None to create.
            **kwargs: Additional fields for the character.

        Returns:
            Character: The updated or created character.
        """
        # Purge the cache to ensure that stale data is not being used.
        self.purge_cache(ctx)

        # Always add the modified timestamp if data is provided.
        if data:
            data["modified"] = str(time_now())

        if not character:
            user = ctx.bot.user_svc.fetch_user(ctx)  # type: ignore [attr-defined] # it really is defined

            new_character = Character.create(
                guild_id=ctx.guild.id,
                created_by=user,
                data=data or {},
                **kwargs,
            )
            character = new_character.set_default_data_values()

            logger.info(f"DATABASE: Create {character} for {ctx.author.display_name}")

            return character

        if data:
            # FIXME: Log each key and value being updated.
            for key, value in data.items():
                logger.debug(f"DATABASE: Update {character} `{key}:{value}`")

            Character.update(data=Character.data.update(data)).where(
                Character.id == character.id
            ).execute()

        if kwargs:
            Character.update(**kwargs).where(Character.id == character.id).execute()

        logger.debug(f"DATABASE: Updated Character '{character}'")

        return Character.get_by_id(character.id)  # Have to query db again to get updated data ???
