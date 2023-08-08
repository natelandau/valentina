"""Models for maintaining in-memory caches of database queries."""

import re

from discord import ApplicationContext, AutocompleteContext
from loguru import logger
from peewee import DoesNotExist, ModelSelect

from valentina.models.constants import MaxTraitValue
from valentina.models.db_tables import (
    Character,
    CustomSection,
    CustomTrait,
    TraitCategory,
    TraitValue,
)
from valentina.utils.errors import (
    CharacterClaimedError,
    CharacterNotFoundError,
    NoClaimError,
)
from valentina.utils.helpers import time_now


class CharacterService:
    """A service for managing the Player characters in the cache/in-memory database."""

    def __init__(self) -> None:
        """Initialize the CharacterService."""
        # Caches to avoid database queries
        ##################################
        self.characters: dict[str, Character] = {}  # {char_key: Character, ...}
        self.storyteller_character_cache: dict[int, list[Character]] = {}  # {guild_id: Character}
        self.claims: dict[str, str] = {}  # {claim_key: char_key}

    @staticmethod
    def __get_char_key(guild_id: int, char_id: int) -> str:
        """Generate a key for the character cache.

        Args:
            guild_id (int): The guild to get the ID for.
            char_id (int): The character database ID

        Returns:
            str: The guild and character IDs joined by an underscore.
        """
        return f"{guild_id}_{char_id}"

    @staticmethod
    def __get_claim_key(guild_id: int, user_id: int) -> str:
        """Generate a key for the claim cache.

        Args:
            guild_id (int): The guild ID
            user_id (int): The user database ID

        Returns:
            str: The guild and user IDs joined by an underscore.
        """
        return f"{guild_id}_{user_id}"

    def add_claim(self, guild_id: int, char_id: int, user_id: int) -> bool:
        """Claim a character for a user."""
        char_key = self.__get_char_key(guild_id, char_id)
        claim_key = self.__get_claim_key(guild_id, user_id)

        if claim_key in self.claims and self.claims[claim_key] == char_key:
            return True

        if any(char_key == claim for claim in self.claims.values()):
            logger.debug(f"CLAIM: Character {char_id} is already claimed")
            raise CharacterClaimedError

        self.claims[claim_key] = char_key
        return True

    def add_custom_section(
        self,
        character: Character,
        section_title: str | None = None,
        section_description: str | None = None,
    ) -> bool:
        """Add or update a custom section to a character."""
        CustomSection.create(
            title=section_title,
            description=section_description,
            character=character.id,
        )

        logger.debug(f"DATABASE: Add custom section to {character}")
        return True

    def add_trait(
        self,
        character: Character,
        name: str,
        description: str,
        category: TraitCategory,
        value: int,
        max_value: int = MaxTraitValue.DEFAULT.value,
    ) -> None:
        """Create a custom trait for a specified character.

        Args:
            character (Character): The character to which the trait is to be added.
            name (str): The name of the trait.
            description (str): The description of the trait.
            category (TraitCategory): The category of the trait.
            value (int): The value of the trait.
            max_value (int, optional): The maximum value that the trait can have. Defaults to MaxTraitValue.DEFAULT.value.

        Returns:
            None
        """
        name = name.strip().title()
        description = description.strip().title() if description else None

        CustomTrait.create(
            name=name,
            description=description,
            category=category,
            value=value,
            character=character.id,
            max_value=max_value,
        )

        logger.debug(f"CHARACTER: Add trait '{name}' to {character}")

    def is_cached_char(
        self, guild_id: int | None = None, char_id: int | None = None, key: str | None = None
    ) -> bool:
        """Check if the user is in the cache."""
        key = self.__get_char_key(guild_id, char_id) if key is None else key
        return key in self.characters

    def create_character(self, ctx: ApplicationContext, **kwargs: str | int) -> Character:
        """Create a character in the cache and database."""
        # Normalize kwargs keys to database column names

        user = ctx.bot.user_svc.fetch_user(ctx)  # type: ignore [attr-defined] # it really is defined

        character = Character.create(
            guild_id=ctx.guild.id,
            created_by=user.id,
            **kwargs,
        )

        # Add storyteller characters to the cache
        if character.storyteller_character:
            self.storyteller_character_cache.setdefault(ctx.guild.id, [])
            self.storyteller_character_cache[ctx.guild.id].append(character)

        logger.info(f"DATABASE: Create character: {character}] for {ctx.author.display_name}")

        return character

    def fetch_all_characters(self, guild_id: int) -> ModelSelect:
        """Returns all characters for a specific guild. Checks the cache first and then the database. If characters are found in the database, they are added to the cache.

        Args:
            guild_id (int): The discord guild id to fetch characters for.

        Returns:
            ModelSelect: A peewee ModelSelect object representing all the characters for the guild.
        """
        cached_ids = []
        chars_to_return = []

        for key, character in self.characters.items():
            if key.startswith(str(guild_id)):
                cached_ids.append(character.id)
                chars_to_return.append(character)
        logger.debug(f"CACHE: Fetch {len(chars_to_return)} characters")

        characters = Character.select().where(
            (Character.guild_id == guild_id)  # grab only characters for the guild
            & (Character.storyteller_character == False)  # grab only player characters # noqa: E712
            & ~(Character.id.in_(cached_ids))  # grab only characters not in cache
        )
        if len(characters) > 0:
            logger.debug(f"DATABASE: Fetch {len(characters)} characters")
        else:
            logger.debug("DATABASE: No characters to fetch")

        for character in characters:
            self.characters[self.__get_char_key(guild_id, character.id)] = character
            chars_to_return.append(character)

        return chars_to_return

    def fetch_all_storyteller_characters(
        self, ctx: ApplicationContext | AutocompleteContext = None, guild_id: int | None = None
    ) -> list[Character]:
        """Fetch all StoryTeller characters for a guild."""
        if guild_id is None and isinstance(ctx, ApplicationContext):
            guild_id = ctx.guild.id
        if guild_id is None and isinstance(ctx, AutocompleteContext):
            guild_id = ctx.interaction.guild.id

        if guild_id in self.storyteller_character_cache:
            logger.debug(
                f"CACHE: Return {len(self.storyteller_character_cache[guild_id])} StoryTeller characters"
            )
            return self.storyteller_character_cache[guild_id]

        self.storyteller_character_cache[guild_id] = []
        characters = Character.select().where(
            (Character.guild_id == guild_id)
            & (Character.storyteller_character == True)  # noqa: E712
        )

        logger.debug(f"DATABASE: Fetch {len(characters)} StoryTeller characters")
        self.storyteller_character_cache[guild_id] = [x for x in characters]
        return self.storyteller_character_cache[guild_id]

    def fetch_claim(self, ctx: ApplicationContext | AutocompleteContext) -> Character:
        """Fetch the character claimed by a user."""
        if isinstance(ctx, ApplicationContext):
            author = ctx.author
            guild = ctx.guild
        if isinstance(ctx, AutocompleteContext):  # pragma: no cover
            author = ctx.interaction.user
            guild = ctx.interaction.guild

        claim_key = self.__get_claim_key(guild.id, author.id)
        if claim_key in self.claims:
            char_key = self.claims[claim_key]

            if self.is_cached_char(key=char_key):
                logger.debug(f"CACHE: Fetch character {self.characters[char_key]}")
                return self.characters[char_key]

            char_id = re.sub(r"[a-zA-Z0-9]+_", "", char_key)
            return Character.get_by_id(int(char_id))

        raise NoClaimError

    def fetch_user_of_character(self, guild_id: int, char_id: int) -> int:
        """Returns the user id of the user who claimed a character."""
        if self.is_char_claimed(guild_id, char_id):
            char_key = self.__get_char_key(guild_id, char_id)
            for claim_key, claim in self.claims.items():
                if claim == char_key:
                    user_id = re.sub(r"[a-zA-Z0-9]+_", "", claim_key)
                    return int(user_id)

        return None

    def is_char_claimed(self, guild_id: int, char_id: int) -> bool:
        """Check if a character is claimed by any user."""
        char_key = self.__get_char_key(guild_id, char_id)
        return any(char_key == claim for claim in self.claims.values())

    def purge_cache(self, ctx: ApplicationContext | None = None, with_claims: bool = False) -> None:
        """Purge all character caches. If ctx is provided, only purge the caches for that guild."""
        caches: dict[str, dict] = {"characters": self.characters}
        if with_claims:
            caches["claims"] = self.claims

        if ctx:
            self.storyteller_character_cache.pop(ctx.guild.id, None)
            for _cache_name, cache in caches.items():
                for key in cache.copy():
                    if key.startswith(str(ctx.guild.id)):
                        cache.pop(key, None)
            logger.debug(f"CACHE: Purge character caches for guild {ctx.guild}")
        else:
            self.storyteller_character_cache = {}
            for cache in caches.values():
                cache.clear()
            logger.debug("CACHE: Purge all character caches")

    def remove_claim(self, ctx: ApplicationContext) -> bool:
        """Remove a claim from a user."""
        claim_key = self.__get_claim_key(ctx.guild.id, ctx.author.id)
        if claim_key in self.claims:
            logger.debug(f"CLAIM: Remove claim for user {ctx.author}")
            del self.claims[claim_key]
            return True
        return False

    def user_has_claim(self, ctx: ApplicationContext) -> bool:
        """Check if a user has a claim."""
        claim_key = self.__get_claim_key(ctx.guild.id, ctx.author.id)
        return claim_key in self.claims

    def update_character(
        self, ctx: ApplicationContext, char_id: int, **kwargs: str | int
    ) -> Character:
        """Update a character in the cache and database."""
        key = self.__get_char_key(ctx.guild.id, char_id)

        try:
            character = Character.get_by_id(char_id)
        except DoesNotExist as e:
            raise CharacterNotFoundError(e=e) from e

        Character.update(modified=time_now(), **kwargs).where(
            Character.id == character.id
        ).execute()

        # Clear caches
        if not character.storyteller_character:
            self.characters.pop(key, None)

        if character.storyteller_character:
            self.storyteller_character_cache.pop(ctx.guild.id, None)

        logger.debug(f"DATABASE: Update character: {character}")
        return character

    def update_traits_by_id(
        self, ctx: ApplicationContext, character: Character, trait_values_dict: dict[int, int]
    ) -> None:
        """Update traits for a character by id.

        Args:
            ctx (ApplicationContext): The context of the command.
            character (Character): The character to update.
            trait_values_dict (dict[int, int]): A dictionary of trait IDs and their new values.
        """
        key = self.__get_char_key(ctx.guild.id, character.id)
        # Clear character from cache but keep claims intact
        self.characters.pop(key, None)

        modified = time_now()

        for trait_id, value in trait_values_dict.items():
            found_trait, created = TraitValue.get_or_create(
                character=character.id,
                trait=trait_id,
                defaults={"value": value, "modified": modified},
            )

            if not created:
                found_trait.value = value
                found_trait.modified = modified
                found_trait.save()

        logger.debug(f"DATABASE: Update traits for character {character}")
