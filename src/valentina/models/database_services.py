"""Models for maintaining in-memory caches of database queries."""

import re
from pathlib import Path

from discord import ApplicationContext, AutocompleteContext
from loguru import logger
from peewee import DoesNotExist, IntegrityError, ModelSelect
from playhouse.sqlite_ext import CSqliteExtDatabase

from valentina.models import Macro, MacroTrait, TraitService
from valentina.models.constants import MaxTraitValue
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
    RollThumbnail,
    Trait,
    TraitCategory,
    TraitCategoryClass,
    TraitClass,
    TraitValue,
    User,
    VampireClan,
)
from valentina.utils.db_backup import DBBackup
from valentina.utils.db_initialize import MigrateDatabase, PopulateDatabase
from valentina.utils.errors import (
    CharacterClaimedError,
    CharacterNotFoundError,
    NoClaimError,
    TraitNotFoundError,
)
from valentina.utils.helpers import time_now


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

    def update_chronicle(
        self, ctx: ApplicationContext, chronicle: Chronicle, **kwargs: str
    ) -> None:
        """Update a chronicle."""
        Chronicle.update(modified=time_now(), **kwargs).where(
            chronicle.id == chronicle.id
        ).execute()
        self.purge_cache(ctx)

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
