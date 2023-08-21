"""Models for maintaining in-memory caches of database queries."""

import re

import discord
from loguru import logger

from valentina.models.db_tables import Character, CustomSection
from valentina.utils import errors
from valentina.utils.helpers import time_now


class CharacterService:
    """A service for managing the Player characters in the cache/in-memory database."""

    def __init__(self) -> None:
        """Initialize the CharacterService.

        This method sets up three dictionaries that serve as caches to avoid unnecessary database queries.

        Attributes:
            characters (dict[str, Character]): A dictionary mapping character keys to Character instances.
            storyteller_character_cache (dict[int, list[Character]]): A dictionary mapping guild IDs to lists of Character instances.
            claims (dict[str, str]): A dictionary mapping claim keys to character keys.
        """
        # Initialize a dictionary to store characters, using character keys as keys and Character instances as values
        self.character_cache: dict[str, Character] = {}

        # Initialize a dictionary to store storyteller characters, using guild IDs as keys and lists of Character instances as values
        self.storyteller_character_cache: dict[int, list[Character]] = {}

        # Initialize a dictionary to store claims, using claim keys as keys and character keys as values
        self.claim_cache: dict[str, str] = {}

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

    @staticmethod
    def __get_claim_key(guild_id: int, user_id: int) -> str:
        """Generate a key for the claim cache.

        This method generates a unique key for each claim by joining the guild ID and user ID with an underscore.
        This key is used to store and retrieve claims from the cache.

        Args:
            guild_id (int): The ID of the guild.
            user_id (int): The ID of the user in the database.

        Returns:
            str: The generated key, consisting of the guild ID and user ID joined by an underscore.
        """
        # Generate a unique key for the claim by joining the guild ID and user ID with an underscore
        return f"{guild_id}_{user_id}"

    def add_claim(self, guild_id: int, char_id: int, user_id: int) -> bool:
        """Claim a character for a user.

        This method allows a user to claim a character. It first generates the character key and claim key. If the claim already exists for the user and character, it returns True. If the character is already claimed by another user, it raises a CharacterClaimedError. Otherwise, it adds the claim to the claims dictionary and returns True.

        Args:
            guild_id (int): The ID of the guild.
            char_id (int): The ID of the character in the database.
            user_id (int): The ID of the user in the database.

        Returns:
            bool: True if the claim is successfully added or already exists, False otherwise.

        Raises:
            CharacterClaimedError: If the character is already claimed by another user.
        """
        # Generate the character key and claim key
        char_key = self.__get_char_key(guild_id, char_id)
        claim_key = self.__get_claim_key(guild_id, user_id)

        # If the claim already exists for the user and character, return True
        if claim_key in self.claim_cache and self.claim_cache[claim_key] == char_key:
            return True

        # If the character is already claimed by another user, raise a CharacterClaimedError
        if any(char_key == claim for claim in self.claim_cache.values()):
            logger.debug(f"CLAIM: Character {char_id} is already claimed")
            raise errors.CharacterClaimedError

        # Add the claim to the claims dictionary
        self.claim_cache[claim_key] = char_key
        return True

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

    def fetch_claim(
        self, ctx: discord.ApplicationContext | discord.AutocompleteContext
    ) -> Character:
        """Fetch the character claimed by a user based on the context provided.

        This method tries to fetch the character claimed by a user from cache if available,
        otherwise, it fetches the character from the database using the character ID.

        Args:
            ctx (ApplicationContext | discord.AutocompleteContext): The context which contains the author and guild information.

        Returns:
            Character: The claimed character.

        Raises:
            NoClaimError: If no claim is found for the given context.
        """
        if isinstance(ctx, discord.ApplicationContext):
            author, guild = ctx.author, ctx.guild
        else:
            author, guild = ctx.interaction.user, ctx.interaction.guild

        claim_key = self.__get_claim_key(guild.id, author.id)

        try:
            char_key = self.claim_cache[claim_key]
        except KeyError as e:
            raise errors.NoClaimError from e

        if self.is_cached_character(key=char_key):
            character = self.character_cache[char_key]
            logger.debug(f"CACHE: Fetch character {character} for author {author} in guild {guild}")
            return character

        char_id = re.sub(r"[a-zA-Z0-9]+_", "", char_key)
        return Character.get_by_id(int(char_id))

    def fetch_user_of_character(self, guild_id: int, char_id: int) -> int | None:
        """Returns the user ID of the user who claimed a character.

        Args:
            guild_id (int): The Discord guild ID to fetch the user for.
            char_id (int): The character ID to fetch the user for.

        Returns:
            int | None: The user ID of the user who claimed the character, or None if the character is not claimed.
        """
        # Check if the character is claimed
        if self.is_char_claimed(guild_id, char_id):
            char_key = self.__get_char_key(guild_id, char_id)

            # Find the claim key that matches the character key
            return next(
                (
                    int(re.sub(r"[a-zA-Z0-9]+_", "", claim_key))
                    for claim_key, claim in self.claim_cache.items()
                    if claim == char_key
                ),
                None,
            )

        return None

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

    def is_char_claimed(self, guild_id: int, char_id: int) -> bool:
        """Check if a character is claimed by any user.

        Args:
            guild_id (int): The Discord guild ID to check the claim for.
            char_id (int): The character ID to check the claim for.

        Returns:
            bool: True if the character is claimed, False otherwise.
        """
        char_key = self.__get_char_key(guild_id, char_id)
        return any(char_key == claim for claim in self.claim_cache.values())

    def purge_cache(
        self, ctx: discord.ApplicationContext | None = None, with_claims: bool = False
    ) -> None:
        """Purge all character caches. If ctx is provided, only purge the caches for that guild.

        Args:
            ctx (ApplicationContext | None, optional): Context object containing guild information. If provided, only caches for that guild are purged.
            with_claims (bool, optional): If True, also purge the claims cache. Defaults to False.

        Returns:
            None
        """
        # Initialize caches to purge
        caches: dict[str, dict] = {"characters": self.character_cache}
        if with_claims:
            caches["claims"] = self.claim_cache

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

    def remove_claim(self, guild_id: int, user_id: int) -> bool:
        """Remove a user's claim.

        This method removes a user's claim from the claims dictionary. If the claim exists, it deletes the claim and returns True.
        If the claim doesn't exist, it returns False.

        Args:
            guild_id (int): The ID of the guild.
            user_id (int): The ID of the user in the database.

        Returns:
            bool: True if the claim is successfully removed, False otherwise.
        """
        # Generate the claim key
        claim_key = self.__get_claim_key(guild_id, user_id)

        # If the claim exists, delete it from the claims dictionary and return True
        if claim_key in self.claim_cache:
            del self.claim_cache[claim_key]
            return True

        # If the claim doesn't exist, return False
        return False

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
            # DEBUG: Log each key and value being updated.
            for key, value in data.items():
                logger.debug(f"DATABASE: Update {character} `{key}:{value}`")

            Character.update(data=Character.data.update(data)).where(
                Character.id == character.id
            ).execute()

        if kwargs:
            Character.update(**kwargs).where(Character.id == character.id).execute()

        logger.debug(f"DATABASE: Updated Character '{character}'")

        return Character.get_by_id(character.id)  # Have to query db again to get updated data ???

    def user_has_claim(self, ctx: discord.ApplicationContext) -> bool:
        """Check if a user has a claim.

        Args:
            ctx (ApplicationContext): Context object containing guild and author information.

        Returns:
            bool: True if the user has a claim, False otherwise.
        """
        claim_key = self.__get_claim_key(ctx.guild.id, ctx.author.id)
        return claim_key in self.claim_cache
