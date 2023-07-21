"""Models for maintaining in-memory caches of database queries."""

import re
from datetime import datetime, timedelta
from pathlib import Path

import arrow
import discord
from discord import ApplicationContext, AutocompleteContext
from loguru import logger
from peewee import DoesNotExist, IntegrityError, ModelSelect, fn
from playhouse.sqlite_ext import CSqliteExtDatabase

from valentina.models.constants import (
    EmbedColor,
    MaxTraitValue,
    TraitCategoryOrder,
    TraitPermissions,
    XPPermissions,
)
from valentina.models.database import (
    DATABASE,
    Character,
    CharacterClass,
    Chronicle,
    ChronicleChapter,
    ChronicleNote,
    ChronicleNPC,
    CustomSection,
    CustomTrait,
    DatabaseVersion,
    Guild,
    GuildUser,
    Macro,
    MacroTrait,
    RollThumbnail,
    Trait,
    TraitCategory,
    TraitCategoryClass,
    TraitClass,
    TraitValue,
    User,
    VampireClan,
    time_now,
)
from valentina.utils.db_backup import DBBackup
from valentina.utils.db_initialize import MigrateDatabase, PopulateDatabase
from valentina.utils.errors import (
    CharacterClaimedError,
    CharacterNotFoundError,
    DuplicateRollResultThumbError,
    NoClaimError,
    TraitNotFoundError,
)


class TraitService:
    """Traits manager cache/in-memory database."""

    def __init__(self) -> None:
        self.class_traits: dict[str, list[Trait]] = {}  # {class: [traits]}

    def fetch_all_class_traits(self, char_class: str) -> list[Trait]:
        """Fetch all traits for a character class."""
        if char_class in self.class_traits:
            logger.debug(f"CACHE: Return traits for `{char_class}`")
            return self.class_traits[char_class]

        logger.debug(f"DATABASE: Fetch all traits for `{char_class}`")

        traits = (
            Trait.select()
            .join(TraitClass)
            .join(CharacterClass)
            .where(CharacterClass.name == char_class)
        )

        self.class_traits[char_class] = sorted(
            [x for x in traits], key=lambda x: TraitCategoryOrder[x.category.name]
        )

        return self.class_traits[char_class]

    def fetch_trait_id_from_name(self, trait_name: str) -> int:
        """Fetch a trait ID from the trait name."""
        logger.debug(f"DATABASE: Fetch trait ID for `{trait_name}`")

        try:
            trait = Trait.get(fn.lower(Trait.name) == trait_name.lower())
            return trait.id
        except DoesNotExist as e:
            raise TraitNotFoundError(f"Trait `{trait_name}` not found") from e

    def fetch_trait_category(self, query: str | int) -> str:
        """Fetch the category of a trait."""
        try:
            if isinstance(query, int):
                return Trait.get(Trait.id == query).category.name

            if isinstance(query, str):
                return Trait.get(fn.lower(Trait.name) == query.lower()).category.name

        except DoesNotExist as e:
            raise TraitNotFoundError(f"Trait `{query}` not found") from e

    def purge(self) -> None:
        """Purge the cache."""
        logger.info("TRAITS: Purge cache")
        self.class_traits = {}


class ChronicleService:
    """Chronicle Manager cache/in-memory database."""

    # TODO: Ability renumber chapters

    def __init__(self) -> None:
        """Initialize the ChronicleService."""
        # Caches to avoid database queries
        ##################################
        self.actives: dict[int, Chronicle] = {}
        self.chapters: dict[int, list[ChronicleChapter]] = {}
        self.notes: dict[int, list[ChronicleNote]] = {}
        self.npcs: dict[int, list[ChronicleNPC]] = {}

    def create_chronicle(
        self, ctx: ApplicationContext, name: str, description: str | None = None
    ) -> Chronicle:
        """Create a new chronicle."""
        try:
            chronicle = Chronicle.create(
                guild_id=ctx.guild.id,
                name=name,
                description=description,
                guild=ctx.guild.id,
                created=time_now(),
                modified=time_now(),
                is_active=False,
            )
            logger.info(f"CHRONICLE: Create {name} for guild {ctx.guild.id}")
            return chronicle

        except IntegrityError as e:
            raise ValueError(f"Chronicle {name} already exists.") from e

    def create_chapter(
        self,
        ctx: ApplicationContext,
        chronicle: Chronicle,
        name: str,
        short_description: str,
        description: str,
    ) -> ChronicleChapter:
        """Create a new chapter."""
        try:
            last_chapter = max([x.chapter for x in self.fetch_all_chapters(ctx, chronicle)])
            chapter = last_chapter + 1
        except ValueError:
            chapter = 1

        chapter = ChronicleChapter.create(
            chronicle=chronicle.id,
            chapter=chapter,
            name=name,
            short_description=short_description,
            description=description,
            created=time_now(),
            modified=time_now(),
        )
        logger.info(f"CHRONICLE: Create Chapter {name} for guild {ctx.guild.id}")
        self.chapters.pop(ctx.guild.id, None)
        return chapter

    def create_note(
        self,
        ctx: ApplicationContext,
        chronicle: Chronicle,
        name: str,
        description: str,
        chapter: ChronicleChapter | None = None,
    ) -> ChronicleNote:
        """Create a new note."""
        user = ctx.bot.user_svc.fetch_user(ctx)  # type: ignore [attr-defined] # it really is defined

        note = ChronicleNote.create(
            chronicle=chronicle.id,
            name=name,
            description=description,
            user=user.id,
            created=time_now(),
            modified=time_now(),
            chapter=chapter.id if chapter else None,
        )
        self.notes.pop(ctx.guild.id, None)
        logger.info(f"CHRONICLE: Create Note {name} for guild {ctx.guild.id}")
        return note

    def create_npc(
        self,
        ctx: ApplicationContext,
        chronicle: Chronicle,
        name: str,
        npc_class: str,
        description: str,
    ) -> ChronicleNPC:
        """Create a new NPC."""
        npc = ChronicleNPC.create(
            chronicle=chronicle.id,
            name=name,
            npc_class=npc_class,
            description=description,
            created=time_now(),
            modified=time_now(),
        )
        self.npcs.pop(ctx.guild.id, None)
        logger.info(f"CHRONICLE: Create NPC {name} for guild {ctx.guild.id}")
        return npc

    def delete_chronicle(self, ctx: ApplicationContext, chronicle: Chronicle) -> None:
        """Delete a chronicle."""
        self.actives.pop(ctx.guild.id, None)
        self.chapters.pop(ctx.guild.id, None)
        self.notes.pop(ctx.guild.id, None)
        self.npcs.pop(ctx.guild.id, None)

        chronicle.remove()

        logger.info(f"CHRONICLE: Delete {chronicle.name} and all associated content")

    def delete_chapter(self, ctx: ApplicationContext, chapter: ChronicleChapter) -> None:
        """Delete a chapter."""
        chapter.delete_instance()
        self.chapters.pop(ctx.guild.id, None)
        logger.info(f"CHRONICLE: Delete Chapter {chapter.name} for guild {ctx.guild.id}")

    def delete_note(self, ctx: ApplicationContext, note: ChronicleNote) -> None:
        """Delete a note."""
        note.delete_instance()
        self.notes.pop(ctx.guild.id, None)
        logger.info(f"CHRONICLE: Delete Note {note.name} for guild {ctx.guild.id}")

    def delete_npc(self, ctx: ApplicationContext, npc: ChronicleNPC) -> None:
        """Delete an NPC."""
        npc.delete_instance()
        self.npcs.pop(ctx.guild.id, None)
        logger.info(f"CHRONICLE: Delete NPC {npc.name} for guild {ctx.guild.id}")

    def fetch_active(self, ctx: ApplicationContext | AutocompleteContext) -> Chronicle:
        """Fetch the active chronicle for the guild."""
        if isinstance(ctx, ApplicationContext):
            guild_id = ctx.guild.id
        if isinstance(ctx, AutocompleteContext):  # pragma: no cover
            guild_id = ctx.interaction.guild.id

        if guild_id in self.actives:
            return self.actives[guild_id]

        try:
            chronicle = Chronicle.get(guild=guild_id, is_active=True)
            self.actives[guild_id] = chronicle
            return chronicle
        except DoesNotExist as e:
            raise ValueError("No active chronicle found\nUse `/chronicle set_active`") from e

    def fetch_all(self, ctx: ApplicationContext | AutocompleteContext) -> ModelSelect:
        """Fetch all chronicles for a guild."""
        if isinstance(ctx, ApplicationContext):
            guild_id = ctx.guild.id
        if isinstance(ctx, AutocompleteContext):  # pragma: no cover
            guild_id = ctx.interaction.guild.id

        try:
            return Chronicle.select().where(Chronicle.guild == guild_id)
        except DoesNotExist as e:
            raise ValueError("No chronicles found") from e

    def fetch_chapter_by_id(self, ctx: ApplicationContext, chapter_id: int) -> ChronicleChapter:
        """Fetch a chapter by ID."""
        if ctx.guild.id in self.chapters:
            for chapter in self.chapters[ctx.guild.id]:
                if chapter.id == chapter_id:
                    return chapter

        try:
            return ChronicleChapter.get(id=chapter_id)
        except DoesNotExist as e:
            raise ValueError(f"No chapter found with ID {chapter_id}") from e

    def fetch_chapter_by_name(
        self, ctx: ApplicationContext, chronicle: Chronicle, name: str
    ) -> ChronicleChapter:
        """Fetch a chapter by name."""
        if ctx.guild.id in self.chapters:
            for chapter in self.chapters[ctx.guild.id]:
                if chapter.name == name.strip() and chapter.chronicle == chronicle.id:
                    return chapter

        try:
            return ChronicleChapter.get(chronicle=chronicle.id, name=name.strip())
        except DoesNotExist as e:
            raise ValueError(f"No chapter found with name {name}") from e

    def fetch_chronicle_by_name(self, ctx: ApplicationContext, name: str) -> Chronicle:
        """Fetch a chronicle by name."""
        try:
            return Chronicle.get(guild=ctx.guild.id, name=name)
        except DoesNotExist as e:
            raise ValueError(f"No chronicle found with name {name}") from e

    def fetch_all_chapters(
        self, ctx: ApplicationContext | AutocompleteContext, chronicle: Chronicle
    ) -> ModelSelect:
        """Fetch all chapters for a chronicle."""
        if isinstance(ctx, ApplicationContext):
            guild_id = ctx.guild.id
        if isinstance(ctx, AutocompleteContext):  # pragma: no cover
            guild_id = ctx.interaction.guild.id

        if guild_id in self.chapters:
            return self.chapters[guild_id]

        try:
            chapters = ChronicleChapter.select().where(ChronicleChapter.chronicle == chronicle.id)
            logger.debug(f"DATABASE: Fetch all chapters for guild {guild_id}")
            self.chapters[guild_id] = chapters
            return chapters
        except DoesNotExist as e:
            raise ValueError("No chapters found") from e

    def fetch_all_notes(
        self, ctx: ApplicationContext | AutocompleteContext, chronicle: Chronicle
    ) -> ModelSelect:
        """Fetch all notes for a chronicle."""
        if isinstance(ctx, ApplicationContext):
            guild_id = ctx.guild.id
        if isinstance(ctx, AutocompleteContext):
            guild_id = ctx.interaction.guild.id

        if guild_id in self.notes:
            logger.debug(f"CACHE: Return notes for guild {guild_id}")
            return self.notes[guild_id]

        try:
            notes = ChronicleNote.select().where(ChronicleNote.chronicle == chronicle.id)
            logger.debug(f"DATABASE: Fetch all notes for guild {guild_id}")
            self.notes[guild_id] = notes
            return notes
        except DoesNotExist as e:
            raise ValueError("No notes found") from e

    def fetch_all_npcs(
        self, ctx: ApplicationContext | AutocompleteContext, chronicle: Chronicle
    ) -> ModelSelect:
        """Fetch all NPCs for a chronicle."""
        if isinstance(ctx, ApplicationContext):
            guild_id = ctx.guild.id
        if isinstance(ctx, AutocompleteContext):  # pragma: no cover
            guild_id = ctx.interaction.guild.id

        if guild_id in self.npcs:
            logger.debug(f"CACHE: Return npcs for guild {guild_id}")
            return self.npcs[guild_id]

        try:
            npcs = ChronicleNPC.select().where(ChronicleNPC.chronicle == chronicle.id)
            logger.debug(f"DATABASE: Fetch all npcs for guild {guild_id}")
            self.npcs[guild_id] = npcs
            return npcs
        except DoesNotExist as e:
            raise ValueError("No NPCs found") from e

    def fetch_note_by_id(self, ctx: ApplicationContext, note_id: int) -> ChronicleNote:
        """Fetch a note by ID."""
        if ctx.guild.id in self.notes:
            for note in self.notes[ctx.guild.id]:
                if note.id == note_id:
                    return note

        try:
            return ChronicleNote.get(id=note_id)
        except DoesNotExist as e:
            raise ValueError(f"No note found with ID {note_id}") from e

    def fetch_npc_by_name(self, chronicle: Chronicle, name: str) -> ChronicleNPC:
        """Fetch an NPC by name."""
        try:
            return ChronicleNPC.get(name=name, chronicle=chronicle.id)
        except DoesNotExist as e:
            raise ValueError(f"No NPC found with name {name}") from e

    def set_active(self, ctx: ApplicationContext, name: str) -> None:
        """Set the chronicle as active."""
        chronicle = self.fetch_chronicle_by_name(ctx, name)

        for c in self.fetch_all(ctx):
            if c.id == chronicle.id:
                chronicle.is_active = True
                chronicle.modified = time_now()
                chronicle.save()
            elif c.is_active:
                c.is_active = False
                c.modified = time_now()
                c.save()

        self.purge_cache(ctx)
        self.actives[ctx.guild.id] = chronicle
        logger.info(f"CHRONICLE: Set {chronicle.name} as active")

    def set_inactive(self, ctx: ApplicationContext) -> None:
        """Set the active chronicle to inactive."""
        try:
            chronicle = self.fetch_active(ctx)
        except ValueError as e:
            raise ValueError("No active chronicle found") from e

        chronicle.is_active = False
        chronicle.modified = time_now()
        chronicle.save()
        self.purge_cache(ctx)
        logger.debug(f"CHRONICLE: Set {chronicle.name} as inactive")

    def purge_cache(self, ctx: ApplicationContext | None = None) -> None:
        """Purge the cache."""
        if ctx:
            self.actives.pop(ctx.guild.id, None)
            self.chapters.pop(ctx.guild.id, None)
            self.npcs.pop(ctx.guild.id, None)
            self.notes.pop(ctx.guild.id, None)
            logger.info(f"CHRONICLE: Purge cache for guild {ctx.guild.id}")
        else:
            self.actives = {}
            self.chapters = {}
            self.notes = {}
            self.npcs = {}
            logger.info("CHRONICLE: Purge cache")

    def update_chapter(
        self, ctx: ApplicationContext, chapter: ChronicleChapter, **kwargs: str
    ) -> None:
        """Update a chapter."""
        ChronicleChapter.update(modified=time_now(), **kwargs).where(
            ChronicleChapter.id == chapter.id
        ).execute()

        self.chapters.pop(ctx.guild.id, None)

        logger.debug(f"CHRONICLE: Update chapter {chapter.name} for guild {ctx.guild.id}")

    def update_note(self, ctx: ApplicationContext, note: ChronicleNote, **kwargs: str) -> None:
        """Update a note."""
        ChronicleNote.update(modified=time_now(), **kwargs).where(
            ChronicleNote.id == note.id
        ).execute()

        self.notes.pop(ctx.guild.id, None)

        logger.debug(f"CHRONICLE: Update note {note.name} for guild {ctx.guild.id}")

    def update_npc(self, ctx: ApplicationContext, npc: ChronicleNPC, **kwargs: str) -> None:
        """Update an NPC."""
        ChronicleNPC.update(modified=time_now(), **kwargs).where(
            ChronicleNPC.id == npc.id
        ).execute()

        self.npcs.pop(ctx.guild.id, None)

        logger.debug(f"CHRONICLE: Update NPC {npc.name} for guild {ctx.guild.id}")


class CharacterService:
    """A service for managing the Character Manager cache/in-memory database."""

    def __init__(self) -> None:
        """Initialize the CharacterService."""
        # Caches to avoid database queries
        ##################################
        self.characters: dict[str, Character] = {}  # {char_key: Character, ...}
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
        """Create a custom trait for a character."""
        CustomTrait.create(
            name=name.strip().title(),
            description=description.strip() if description else None,
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

        logger.info(f"DATABASE: Create character: {character}] for {ctx.author.display_name}")

        return character

    @logger.catch
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

    def fetch_trait_value(self, character: Character, trait: str) -> int:
        """Fetch the value of a trait for a character."""
        # First grab the trait from the database
        tv_value = (
            TraitValue.select()
            .where(TraitValue.character == character)
            .join(Trait)
            .where(fn.lower(Trait.name) == trait.lower())
        )

        if len(tv_value) != 0:
            return tv_value[0].value

        custom_trait = [x for x in character.custom_traits if x.name.lower() == trait.lower()]

        if len(custom_trait) > 0:
            return custom_trait[0].value

        raise TraitNotFoundError(trait.title())

    def fetch_trait_category(self, character: Character, trait: str) -> str:
        """Fetch the category of a trait for a character."""
        try:
            return TraitService().fetch_trait_category(trait)

        except TraitNotFoundError as e:
            custom_trait = [x for x in character.custom_traits if x.name.lower() == trait.lower()]

            if len(custom_trait) > 0:
                return custom_trait[0].category

            raise TraitNotFoundError from e

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
            for _cache_name, cache in caches.items():
                for key in cache.copy():
                    if key.startswith(str(ctx.guild.id)):
                        cache.pop(key, None)
            logger.debug(f"CACHE: Purge character caches for guild {ctx.guild}")
        else:
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

        # Clear character from cache but keep claims intact
        self.characters.pop(key, None)

        try:
            character = Character.get_by_id(char_id)
        except DoesNotExist as e:
            raise CharacterNotFoundError(e=e) from e

        Character.update(modified=time_now(), **kwargs).where(
            Character.id == character.id
        ).execute()

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

    def update_trait_value_by_name(
        self, ctx: ApplicationContext, character: Character, trait_name: str, new_value: int
    ) -> bool:
        """Update a trait value for a character."""
        try:
            trait_id = TraitService().fetch_trait_id_from_name(trait_name)
            self.update_traits_by_id(ctx, character, {trait_id: new_value})
            logger.debug(f"DATABASE: Update '{trait_name}' for [{character} to {new_value}")
            return True
        except TraitNotFoundError as e:
            # Update custom traits

            custom_trait = CustomTrait.get_or_none(
                CustomTrait.character_id == character.id and CustomTrait.name == trait_name.title()
            )

            if custom_trait:
                custom_trait.value = new_value
                custom_trait.save()
                self.update_character(ctx, character.id)
                logger.debug(f"DATABASE: Update '{trait_name}' for {character} to {new_value}")

                # Reset custom traits cache for character
                self.purge_cache(ctx)
                return True

            raise TraitNotFoundError from e


class UserService:
    """User manager and in-memory cache."""

    def __init__(self) -> None:
        """Initialize the UserService."""
        self.user_cache: dict[str, User] = {}  # {user_key: User, ...}
        self.macro_cache: dict[str, list[Macro]] = {}  # {user_key: [Macro, ...]}

    @staticmethod
    def __get_user_key(guild_id: int, user_id: int) -> str:
        """Get the guild and user IDs.

        Args:
            guild_id (discord.Guild | int): The guild to get the ID for.
            user_id (discord.User | int): The user to get the ID for.

        Returns:
            str: The guild and user IDs joined by an underscore.
        """
        return f"{guild_id}_{user_id}"

    def purge_cache(self, ctx: ApplicationContext | None = None) -> None:
        """Purge user service cache. If ctx is None, purge all caches."""
        if ctx:
            key = self.__get_user_key(ctx.guild.id, ctx.author.id)
            self.user_cache.pop(key, None)
            self.macro_cache.pop(key, None)
            logger.debug(f"CACHE: Purge user cache: {key}")
        else:
            self.user_cache = {}
            self.macro_cache = {}
            logger.debug("CACHE: Purge all user caches")

    def fetch_macros(self, ctx: ApplicationContext | AutocompleteContext) -> list[Macro]:
        """Fetch a list of macros for a user."""
        if isinstance(ctx, ApplicationContext):
            author_id = ctx.author.id
            guild_id = ctx.guild.id
        if isinstance(ctx, AutocompleteContext):
            author_id = ctx.interaction.user.id
            guild_id = ctx.interaction.guild.id

        key = self.__get_user_key(guild_id, author_id)

        if key in self.macro_cache:
            logger.debug(f"CACHE: Return macros for user: {author_id}")
            return self.macro_cache[key]

        logger.debug(f"DATABASE: Fetch macros for user: {author_id}")
        macros = (
            Macro.select()
            .where((Macro.user == author_id) & (Macro.guild == guild_id))
            .order_by(Macro.name.asc())
        )
        self.macro_cache[key] = [x for x in macros]

        logger.debug(f"DATABASE: Fetch macros for {key}")
        return self.macro_cache[key]

    def fetch_macro(self, ctx: ApplicationContext, macro_name: str) -> Macro:
        """Fetch a macro by name."""
        macros = self.fetch_macros(ctx)

        for macro in macros:
            if macro.name.lower() == macro_name.lower():
                return macro

        return None

    def fetch_user(self, ctx: ApplicationContext) -> User:
        """Fetch a user object from the cache or database. If user doesn't exist, create in the database and the cache."""
        key = self.__get_user_key(ctx.guild.id, ctx.author.id)

        if key in self.user_cache:
            logger.debug(f"CACHE: Return user {key} from cache")
            return self.user_cache[key]

        user, created = User.get_or_create(
            id=ctx.author.id,
            defaults={
                "id": ctx.author.id,
                "name": ctx.author.display_name,
                "username": ctx.author.name,
                "mention": ctx.author.mention,
                "first_seen": time_now(),
                "last_seen": time_now(),
            },
        )
        if created:
            # Add user to guild_user lookup table
            existing_guild_user, lookup_created = GuildUser.get_or_create(
                user=ctx.author.id,
                guild=ctx.guild.id,
                defaults={"guild_id": ctx.guild.id, "user_id": ctx.author.id},
            )
            if lookup_created:
                logger.debug(
                    f"DATABASE: Create guild_user lookup for user:{ctx.author.name} guild:{ctx.guild.name}"
                )

            logger.info(f"DATABASE: Create user '{ctx.author.display_name}'")

        else:
            user.last_seen = time_now()
            user.save()

        logger.debug(f"CACHE: Add user {user.name}")
        self.user_cache[key] = user
        return user

    def has_xp_permissions(self, ctx: ApplicationContext, character: Character = None) -> bool:
        """Determine if the user has permissions to add xp."""
        if ctx.author.guild_permissions.administrator:
            return True

        settings = ctx.bot.guild_svc.fetch_guild_settings(ctx)  # type: ignore [attr-defined]

        if settings["xp_permissions"] == XPPermissions.UNRESTRICTED.value:
            return True

        if settings["xp_permissions"] == XPPermissions.CHARACTER_OWNER_ONLY.value and character:
            return character.created_by.id == ctx.author.id

        if settings["xp_permissions"] == XPPermissions.WITHIN_24_HOURS.value and character:
            return (character.created_by.id == ctx.author.id) and (
                arrow.utcnow() - arrow.get(character.created) <= timedelta(hours=24)
            )

        return False

    def has_trait_permissions(self, ctx: ApplicationContext, character: Character = None) -> bool:
        """Determines if the user have permissions to update trait values."""
        if ctx.author.guild_permissions.administrator:
            return True

        settings = ctx.bot.guild_svc.fetch_guild_settings(ctx)  # type: ignore [attr-defined]

        if settings["trait_permissions"] == TraitPermissions.UNRESTRICTED.value:
            return True

        if (
            settings["trait_permissions"] == TraitPermissions.CHARACTER_OWNER_ONLY.value
            and character
        ):
            return character.created_by.id == ctx.author.id

        if settings["trait_permissions"] == TraitPermissions.WITHIN_24_HOURS.value and character:
            return (character.created_by.id == ctx.author.id) and (
                arrow.utcnow() - arrow.get(character.created) <= timedelta(hours=24)
            )

        return False


class GuildService:
    """Manage guilds in the database. Guilds are created on bot connect."""

    def __init__(self) -> None:
        self.settings_cache: dict[int, dict[str, str | int | bool]] = {}
        self.roll_result_thumbs: dict[int, dict[str, list[str]]] = {}

    @staticmethod
    def is_in_db(guild_id: int) -> bool:
        """Check if the guild is in the database."""
        return Guild.select().where(Guild.id == guild_id).exists()

    @staticmethod
    def fetch_all_traits(
        guild_id: int, flat_list: bool = False
    ) -> dict[str, list[str]] | list[str]:
        """Fetch all traits for a guild inclusive of common and custom.

        Args:
            guild_id (int): The guild to fetch traits for.
            flat_list (bool, optional): Return a flat list of traits. Defaults to False.
        """
        all_traits: dict[str, list[str]] = {}
        for category in TraitCategory.select().order_by(TraitCategory.name.asc()):
            if category not in all_traits:
                all_traits[category.name] = []

            for trait in sorted(category.traits, key=lambda x: x.name):
                all_traits[category.name].append(trait.name)

        custom_traits = CustomTrait.select().join(Character).where(Character.guild_id == guild_id)
        if len(custom_traits) > 0:
            for custom_trait in custom_traits:
                category = custom_trait.category.name.title()
                if category not in all_traits:
                    all_traits[category] = []
                all_traits[category].append(custom_trait.name.title())

        if flat_list:
            # Flattens the dictionary to a single list, while removing duplicates
            return sorted(list({item for sublist in all_traits.values() for item in sublist}))

        return all_traits

    def fetch_guild_settings(self, ctx: ApplicationContext) -> dict[str, str | int | bool]:
        """Fetch all guild settings."""
        if ctx.guild.id in self.settings_cache:
            return self.settings_cache[ctx.guild.id]

        self.settings_cache[ctx.guild.id] = {}

        guild = Guild.get_by_id(ctx.guild.id)
        self.settings_cache[ctx.guild.id]["xp_permissions"] = guild.xp_permissions
        self.settings_cache[ctx.guild.id]["trait_permissions"] = guild.trait_permissions
        self.settings_cache[ctx.guild.id]["log_channel_id"] = guild.log_channel_id
        self.settings_cache[ctx.guild.id]["use_audit_log"] = guild.use_audit_log

        logger.debug(f"DATABASE: Fetch guild settings for '{ctx.guild.name}'")
        return self.settings_cache[ctx.guild.id]

    def add_roll_result_thumb(self, ctx: ApplicationContext, roll_type: str, url: str) -> None:
        """Add a roll result thumbnail to the database."""
        ctx.bot.user_svc.fetch_user(ctx)  # type: ignore [attr-defined] # it really is defined

        self.roll_result_thumbs.pop(ctx.guild.id, None)

        already_exists = RollThumbnail.get_or_none(guild=ctx.guild.id, url=url)
        if already_exists:
            raise DuplicateRollResultThumbError

        RollThumbnail.create(guild=ctx.guild.id, user=ctx.author.id, url=url, roll_type=roll_type)
        logger.info(f"DATABASE: Add roll result thumbnail for '{ctx.author.display_name}'")

    async def create_bot_log_channel(
        self, ctx: ApplicationContext, log_channel_name: str
    ) -> discord.TextChannel:
        """Fetch the bot log channel for a guild and create it if it doesn't exist."""
        log_channel = None
        self.settings_cache.pop(ctx.guild.id, None)

        guild_object = Guild.get_or_none(id=ctx.guild.id)

        # Set channel permissions
        member_overwrite = discord.PermissionOverwrite()
        member_overwrite.send_messages = False  # type: ignore [misc]
        member_overwrite.read_messages = True  # type: ignore [misc]
        member_overwrite.manage_messages = False  # type: ignore [misc]
        member_overwrite.add_reactions = True  # type: ignore [misc]
        bot_overwrite = discord.PermissionOverwrite()
        bot_overwrite.send_messages = True  # type: ignore [misc]
        bot_overwrite.read_messages = True  # type: ignore [misc]
        bot_overwrite.manage_messages = True  # type: ignore [misc]

        # If the guild has a log channel set which matches the name, use it and create nothing
        if guild_object.log_channel_id:
            existing_channel = discord.utils.get(
                ctx.guild.text_channels, id=guild_object.log_channel_id
            )
            if (
                existing_channel
                and existing_channel.name.lower().strip() == log_channel_name.lower().strip()
            ):
                logger.debug(f"DATABASE: Fetch bot audit log channel for '{ctx.guild.name}'")

                await existing_channel.set_permissions(
                    ctx.guild.default_role, overwrite=member_overwrite
                )
                for user in ctx.guild.members:
                    if user.bot:
                        await existing_channel.set_permissions(user, overwrite=bot_overwrite)
                return existing_channel

        # If the channel already exists, use it and update the database
        existing_channel = discord.utils.get(
            ctx.guild.text_channels, name=log_channel_name.lower().strip()
        )

        if existing_channel:
            await existing_channel.set_permissions(
                ctx.guild.default_role, overwrite=member_overwrite
            )
            for user in ctx.guild.members:
                if user.bot:
                    await existing_channel.set_permissions(user, overwrite=bot_overwrite)

            self.update_or_add(ctx=ctx, log_channel_id=existing_channel.id)
            logger.debug(f"DATABASE: Set bot audit log channel for '{ctx.guild.name}'")
            return existing_channel

        # If the channel doesn't exist, create it and update the database
        log_channel = await ctx.guild.create_text_channel(
            log_channel_name,
            topic="A channel for Valentina audit logs.",
            position=100,
        )
        await log_channel.set_permissions(ctx.guild.default_role, overwrite=member_overwrite)
        for user in ctx.guild.members:
            if user.bot:
                await log_channel.set_permissions(user, overwrite=bot_overwrite)

        self.update_or_add(ctx=ctx, log_channel_id=log_channel.id)
        logger.debug(f"DATABASE: Set bot audit log channel for '{ctx.guild.name}'")
        return log_channel

    def fetch_roll_result_thumbs(self, ctx: ApplicationContext) -> dict[str, list[str]]:
        """Get all roll result thumbnails for a guild."""
        if ctx.guild.id not in self.roll_result_thumbs:
            self.roll_result_thumbs[ctx.guild.id] = {}

            logger.debug(f"DATABASE: Fetch roll result thumbnails for '{ctx.guild.name}'")
            for thumb in RollThumbnail.select().where(RollThumbnail.guild == ctx.guild.id):
                if thumb.roll_type not in self.roll_result_thumbs[ctx.guild.id]:
                    self.roll_result_thumbs[ctx.guild.id][thumb.roll_type] = [thumb.url]
                else:
                    self.roll_result_thumbs[ctx.guild.id][thumb.roll_type].append(thumb.url)

        return self.roll_result_thumbs[ctx.guild.id]

    def purge_cache(self, ctx: ApplicationContext | None = None) -> None:
        """Purge the cache for a guild or all guilds.

        Args:
            ctx (ApplicationContext, optional): The context to purge. Defaults to None.
        """
        if ctx:
            self.settings_cache.pop(ctx.guild.id, None)
            self.roll_result_thumbs.pop(ctx.guild.id, None)
            logger.debug(f"CACHE: Purge guild cache for '{ctx.guild.name}'")
        else:
            self.settings_cache = {}
            self.roll_result_thumbs = {}
            logger.debug("CACHE: Purge all guild caches")

    async def send_to_log(self, ctx: ApplicationContext, message: str | discord.Embed) -> None:
        """Send a message to the log channel for a guild."""
        settings = self.fetch_guild_settings(ctx)
        if settings["use_audit_log"] and settings["log_channel_id"] is not None:
            log_channel = ctx.guild.get_channel(settings["log_channel_id"])
            if log_channel:
                if isinstance(message, discord.Embed):
                    await log_channel.send(embed=message)
                else:
                    embed = discord.Embed(title=message, color=EmbedColor.INFO.value)
                    embed.timestamp = datetime.now()
                    embed.set_footer(
                        text=f"Command invoked by {ctx.author.display_name} in #{ctx.channel.name}"
                    )
                    await log_channel.send(embed=embed)

    def update_or_add(
        self,
        guild: discord.Guild = None,
        ctx: ApplicationContext = None,
        **kwargs: str | int | datetime,
    ) -> None:
        """Add a guild to the database or update it if it already exists."""
        if guild and ctx:
            raise ValueError("Cannot provide both guild and ctx")

        if guild:
            guild_id = guild.id
            guild_name = guild.name

        if ctx:
            guild_id = ctx.guild.id
            guild_name = ctx.guild.name
            self.purge_cache(ctx)

        db_id, is_created = Guild.get_or_create(
            id=guild_id,
            defaults={
                "id": guild_id,
                "name": guild_name,
                "created": time_now(),
                "modified": time_now(),
            },
        )
        if is_created:
            logger.info(f"DATABASE: Create guild {db_id.name}")

        if not is_created:
            kwargs["modified"] = time_now()
            Guild.set_by_id(guild_id, kwargs)
            logger.debug(f"DATABASE: Update guild '{db_id.name}'")


class DatabaseService:
    """Representation of the database."""

    def __init__(self, database: CSqliteExtDatabase) -> None:
        """Initialize the DatabaseService."""
        self.db = database

    @staticmethod
    async def backup_database(config: dict) -> Path:
        """Create a backup of the database."""
        backup_file = await DBBackup(config, DATABASE).create_backup()
        await DBBackup(config, DATABASE).clean_old_backups()
        return backup_file

    def column_exists(self, table: str, column: str) -> bool:
        """Check if a column exists in a table.

        Args:
            table (str): The table to check.
            column (str): The column to check.

        Returns:
            bool: Whether the column exists in the table.
        """
        db = self.db
        cursor = db.execute_sql(f"PRAGMA table_info({table})")
        columns = [row[1] for row in cursor.fetchall()]
        return column in columns

    def create_tables(self) -> None:
        """Create all tables in the database if they don't exist."""
        with self.db:
            self.db.create_tables(
                [
                    Character,
                    CharacterClass,
                    CustomSection,
                    TraitCategory,
                    CustomTrait,
                    DatabaseVersion,
                    Guild,
                    Macro,
                    RollThumbnail,
                    User,
                    VampireClan,
                    Chronicle,
                    ChronicleNote,
                    ChronicleChapter,
                    ChronicleNPC,
                    Trait,
                    TraitClass,
                    TraitValue,
                    GuildUser,
                    TraitCategoryClass,
                    MacroTrait,
                ]
            )
        logger.info("DATABASE: Create Tables")

    def get_tables(self) -> list[str]:
        """Get all tables in the Database."""
        with self.db:
            cursor = self.db.execute_sql("SELECT name FROM sqlite_master WHERE type='table';")
            return [row[0] for row in cursor.fetchall()]

    def database_version(self) -> str:
        """Get the version of the database."""
        return DatabaseVersion.get_by_id(1).version

    @logger.catch
    def initialize_database(self, bot_version: str) -> None:
        """Migrate from old database versions to the current one."""
        PopulateDatabase(self.db).populate()

        existing_data, new_db_created = DatabaseVersion.get_or_create(
            id=1,
            defaults={"version": bot_version},
        )

        # If we are creating a new database, populate the necessary tables with data
        if new_db_created:
            logger.info(f"DATABASE: Create version v{bot_version}")
            return

        # If database exists, perform migrations if necessary
        MigrateDatabase(
            self.db,
            bot_version=bot_version,
            db_version=existing_data.version,
        ).migrate()

        # Bump the database version to the latest bot version
        DatabaseVersion.set_by_id(1, {"version": bot_version})
        logger.info(f"DATABASE: Database running v{bot_version}")
