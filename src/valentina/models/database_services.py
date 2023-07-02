"""Models for maintaining in-memory caches of database queries."""

import re
from datetime import datetime

import discord
from discord import ApplicationContext, AutocompleteContext
from loguru import logger
from peewee import DoesNotExist, IntegrityError, ModelSelect, SqliteDatabase, fn
from semver import Version

from valentina.models.constants import (
    COMMON_TRAITS,
    HUNTER_TRAITS,
    MAGE_TRAITS,
    VAMPIRE_TRAITS,
    WEREWOLF_TRAITS,
    CharClass,
    EmbedColor,
    VampClanList,
)
from valentina.models.database import (
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
    RollThumbnail,
    User,
    VampireClan,
    time_now,
)
from valentina.utils.errors import (
    CharacterClaimedError,
    CharacterNotFoundError,
    DuplicateRollResultThumbError,
    NoClaimError,
    SectionExistsError,
    SectionNotFoundError,
    TraitNotFoundError,
    UserHasClaimError,
)
from valentina.utils.helpers import (
    extend_common_traits_with_class,
    get_max_trait_value,
    merge_dictionaries,
    normalize_to_db_row,
    num_to_circles,
)


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
        UserService().fetch_user(ctx)

        note = ChronicleNote.create(
            chronicle=chronicle.id,
            name=name,
            description=description,
            user=ctx.author.id,
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

        for chapter in self.fetch_all_chapters(ctx, chronicle):
            if chapter.chronicle == chronicle.id:
                chapter.delete_instance()

        for note in self.fetch_all_notes(ctx, chronicle):
            if note.chronicle == chronicle.id:
                note.delete_instance()

        for npc in self.fetch_all_npcs(ctx, chronicle):
            if npc.chronicle == chronicle.id:
                npc.delete_instance()

        chronicle.delete_instance()

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
            logger.debug(f"DATABASE: Fetching all chapters for guild {guild_id}")
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
            return self.notes[guild_id]

        try:
            notes = ChronicleNote.select().where(ChronicleNote.chronicle == chronicle.id)
            logger.debug(f"DATABASE: Fetching all notes for guild {guild_id}")
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
            return self.npcs[guild_id]

        try:
            npcs = ChronicleNPC.select().where(ChronicleNPC.chronicle == chronicle.id)
            logger.debug(f"DATABASE: Fetching all npcs for guild {guild_id}")
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
        logger.info(f"CHRONICLE: Set {chronicle.name} as inactive")

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

        logger.info(f"CHRONICLE: Update chapter {chapter.name} for guild {ctx.guild.id}")

    def update_note(self, ctx: ApplicationContext, note: ChronicleNote, **kwargs: str) -> None:
        """Update a note."""
        ChronicleNote.update(modified=time_now(), **kwargs).where(
            ChronicleNote.id == note.id
        ).execute()

        self.notes.pop(ctx.guild.id, None)

        logger.info(f"CHRONICLE: Update note {note.name} for guild {ctx.guild.id}")

    def update_npc(self, ctx: ApplicationContext, npc: ChronicleNPC, **kwargs: str) -> None:
        """Update an NPC."""
        ChronicleNPC.update(modified=time_now(), **kwargs).where(
            ChronicleNPC.id == npc.id
        ).execute()

        self.npcs.pop(ctx.guild.id, None)

        logger.info(f"CHRONICLE: Update NPC {npc.name} for guild {ctx.guild.id}")


class CharacterService:
    """A service for managing the Character Manager cache/in-memory database."""

    def __init__(self) -> None:
        """Initialize the CharacterService."""
        # Caches to avoid database queries
        ##################################
        self.characters: dict[str, Character] = {}  # {char_key: Character, ...}
        self.claims: dict[str, str] = {}  # {claim_key: char_key}
        self.custom_traits: dict[str, list[CustomTrait]] = {}  # {char_key: [CustomTrait]}
        self.custom_sections: dict[str, list[CustomSection]] = {}  # {char_key: [CustomSection]}

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

        if claim_key in self.claims:
            if self.claims[claim_key] == char_key:
                return True

            logger.debug(f"CLAIM: User {user_id} already has a claim")
            raise UserHasClaimError

        if any(char_key == claim for claim in self.claims.values()):
            logger.debug(f"CLAIM: Character {char_id} is already claimed")
            raise CharacterClaimedError

        self.claims[claim_key] = char_key
        return True

    def add_custom_section(
        self,
        ctx: ApplicationContext,
        character: Character,
        section_title: str | None = None,
        section_description: str | None = None,
    ) -> bool:
        """Add or update a custom section to a character."""
        key = self.__get_char_key(ctx.guild.id, character.id)

        CustomSection.create(
            title=section_title,
            description=section_description,
            guild=ctx.guild.id,
            character=character.id,
        )

        self.custom_sections.pop(key, None)

        logger.debug(f"DATABASE: Add custom section to character {character.id}")
        return True

    def add_trait(
        self,
        ctx: ApplicationContext,
        character: Character,
        name: str,
        description: str,
        category: str,
        value: int,
        max_value: int = 5,
    ) -> None:
        """Create a custom trait for a character."""
        # TODO: max_value default should pull from MaxTraitValue enum

        key = self.__get_char_key(ctx.guild.id, character.id)

        CustomTrait.create(
            name=name.strip().title(),
            description=description.strip() if description else None,
            category=category,
            value=value,
            character=character.id,
            guild_id=ctx.guild.id,
            max_value=max_value,
        )

        if key in self.custom_traits:
            self.custom_traits.pop(key, None)

        logger.info(f"CHARACTER: Added custom trait {name} to {character.id}")

    def is_cached_char(
        self, guild_id: int | None = None, char_id: int | None = None, key: str | None = None
    ) -> bool:
        """Check if the user is in the cache."""
        key = self.__get_char_key(guild_id, char_id) if key is None else key
        return key in self.characters

    def delete_custom_section(
        self, ctx: ApplicationContext, character: Character, section_title: str
    ) -> bool:
        """Delete a custom section from a character."""
        section_title = section_title.lower()
        key = self.__get_char_key(ctx.guild.id, character.id)
        try:
            custom_section = CustomSection.get(
                CustomSection.character == character,
                CustomSection.guild_id == ctx.guild.id,
                fn.Lower(CustomSection.title) == section_title.lower(),
            )
            custom_section.delete_instance()
            if key in self.custom_sections:
                self.custom_sections.pop(key, None)

            return True
        except SectionExistsError:
            return False

    def delete_custom_trait(self, ctx: ApplicationContext, character: Character, name: str) -> bool:
        """Delete a custom trait from a character."""
        name = name.lower()
        key = self.__get_char_key(ctx.guild.id, character.id)
        try:
            custom_trait = CustomTrait.get(
                CustomTrait.character == character,
                CustomTrait.guild_id == ctx.guild.id,
                fn.Lower(CustomTrait.name) == name,
            )
            custom_trait.delete_instance()
            if key in self.custom_traits:
                self.custom_traits.pop(key, None)

            return True
        except TraitNotFoundError:
            return False

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
            logger.info(f"DATABASE: Fetch {len(characters)} characters")
        else:
            logger.debug("DATABASE: No characters to fetch")

        for character in characters:
            self.characters[self.__get_char_key(guild_id, character.id)] = character
            chars_to_return.append(character)

        return chars_to_return

    def fetch_all_character_traits(
        self, character: Character, flat_list: bool = False
    ) -> dict[str, list[str]] | list[str]:
        """Fetch all traits for a character inclusive of common and custom."""
        all_traits = extend_common_traits_with_class(character.class_name)

        custom_traits = CustomTrait.select().where(CustomTrait.character_id == character.id)
        if len(custom_traits) > 0:
            for custom_trait in custom_traits:
                if custom_trait.category.title() not in all_traits:
                    all_traits[custom_trait.category.title()] = []
                all_traits[custom_trait.category.title()].append(custom_trait.name.title())

        if flat_list:
            return sorted(list({y for x in all_traits.values() for y in x}))

        return all_traits

    def fetch_all_character_trait_values(
        self,
        ctx: ApplicationContext,
        character: Character,
    ) -> dict[str, list[tuple[str, int, int, str]]]:
        """Fetch all trait values for a character inclusive of common and custom for display on a character sheet.

        Returns a tuple of (trait name, trait value, trait max value, trait dots).

        Example:
            {
                "Physical": [("Strength", 3, 5, "●●●○○"), ("Agility", 2, 5, "●●●○○")],
                "Social": [("Persuasion", 1, 5, "●○○○○")]
            }
        """
        key = self.__get_char_key(ctx.guild.id, character.id)
        all_traits: dict[str, list[tuple[str, int, int, str]]] = {}

        for category, traits in extend_common_traits_with_class(character.class_name).items():
            if category.title() not in all_traits:
                all_traits[category.title()] = []
            for trait in traits:
                value = getattr(character, normalize_to_db_row(trait))
                max_value = get_max_trait_value(trait)
                dots = num_to_circles(value, max_value)
                all_traits[category.title()].append((trait.title(), value, max_value, dots))

        if key in self.custom_traits:
            custom_traits = self.custom_traits[key]
        else:
            custom_traits = CustomTrait.select().where(CustomTrait.character_id == character.id)
            # Build cache
            self.custom_traits[key] = []
            for custom_trait in custom_traits:
                self.custom_traits[key].append(custom_trait)

        if len(custom_traits) > 0:
            for custom_trait in custom_traits:
                if custom_trait.category.title() not in all_traits:
                    all_traits[custom_trait.category.title()] = []
                custom_trait_name = custom_trait.name.title()
                custom_trait_value = custom_trait.value

                max_value = get_max_trait_value(trait=custom_trait_name, is_custom_trait=True)
                if not max_value:
                    max_value = custom_trait.max_value

                dots = num_to_circles(custom_trait_value, max_value)
                all_traits[custom_trait.category.title()].append(
                    (custom_trait_name, custom_trait_value, max_value, dots)
                )

        return all_traits

    def fetch_char_custom_sections(
        self, ctx: ApplicationContext | AutocompleteContext, character: Character
    ) -> ModelSelect:
        """Fetch a list of custom sections for a character."""
        if isinstance(ctx, ApplicationContext):
            guild_id = ctx.guild.id
        if isinstance(ctx, AutocompleteContext):  # pragma: no cover
            guild_id = ctx.interaction.guild.id

        key = self.__get_char_key(guild_id, character.id)
        if key in self.custom_sections:
            return self.custom_sections[key]

        sections = CustomSection.select().where(
            (CustomSection.character == character.id) & (CustomSection.guild_id == guild_id)
        )
        self.custom_sections[key] = sections
        return sections

    def fetch_custom_section(
        self, ctx: ApplicationContext, character: Character, title: str
    ) -> CustomSection:
        """Fetch a custom section by title."""
        sections = self.fetch_char_custom_sections(ctx, character)
        for section in sections:
            if section.title.lower() == title.lower():
                return section

        raise SectionNotFoundError(f"{character.first_name} has no section {title}")

    def fetch_char_custom_traits(
        self, ctx: ApplicationContext | AutocompleteContext, character: Character
    ) -> list[CustomTrait]:
        """Fetch all custom traits for a character."""
        if isinstance(ctx, ApplicationContext):
            guild = ctx.guild
        if isinstance(ctx, AutocompleteContext):  # pragma: no cover
            guild = ctx.interaction.guild

        key = self.__get_char_key(guild.id, character.id)

        if key in self.custom_traits:
            logger.debug(f"CACHE: Fetch custom traits for {character.name}")
            return self.custom_traits[key]

        custom_traits = CustomTrait.select().where(CustomTrait.character_id == character.id)
        self.custom_traits[key] = custom_traits
        logger.info(f"DATABASE: Fetch custom traits for {character.name}")
        return custom_traits

    def fetch_by_id(self, guild_id: int, char_id: int) -> Character:
        """Fetch a character by database id.

        Args:
            char_id (int): The database id of the character.
            guild_id (int): The discord guild id to fetch characters for.

        Returns:
            Character: The character object.
        """
        key = self.__get_char_key(guild_id, char_id)
        if self.is_cached_char(key=key):
            logger.debug(f"CACHE: Fetch character {char_id}")
            return self.characters[key]

        character = Character.get_by_id(char_id)

        self.characters[key] = character
        logger.info(f"DATABASE: Fetch character: {character.name}")
        return character

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
                logger.debug(f"CACHE: Fetch character {char_key}")
                return self.characters[char_key]

            char_id = re.sub(r"[a-zA-Z0-9]+_", "", char_key)
            return self.fetch_by_id(guild.id, int(char_id))

        raise NoClaimError

    def fetch_trait_value(self, ctx: ApplicationContext, character: Character, trait: str) -> int:
        """Fetch the value of a trait for a character."""
        if hasattr(character, normalize_to_db_row(trait)):
            return getattr(character, normalize_to_db_row(trait))

        custom_trait = [
            x
            for x in self.fetch_char_custom_traits(ctx, character)
            if x.name.lower() == trait.lower()
        ]

        if len(custom_trait) > 0:
            return custom_trait[0].value

        raise TraitNotFoundError

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
        caches: dict[str, dict] = {
            "characters": self.characters,
            "custom_traits": self.custom_traits,
            "custom_sections": self.custom_sections,
        }
        if with_claims:
            caches["claims"] = self.claims

        if ctx:
            for _cache_name, cache in caches.items():
                for key in cache.copy():
                    if key.startswith(str(ctx.guild.id)):
                        cache.pop(key, None)
            logger.debug(f"CACHE: Purged character caches for guild {ctx.guild}")
        else:
            for cache in caches.values():
                cache.clear()
            logger.debug("CACHE: Purged all character caches")

    def remove_claim(self, ctx: ApplicationContext) -> bool:
        """Remove a claim from a user."""
        claim_key = self.__get_claim_key(ctx.guild.id, ctx.author.id)
        if claim_key in self.claims:
            logger.debug(f"CLAIM: Removing claim for user {ctx.author}")
            del self.claims[claim_key]
            return True
        return False

    def user_has_claim(self, ctx: ApplicationContext) -> bool:
        """Check if a user has a claim."""
        claim_key = self.__get_claim_key(ctx.guild.id, ctx.author.id)
        return claim_key in self.claims

    def update_char(self, ctx: ApplicationContext, char_id: int, **kwargs: str | int) -> Character:
        """Update a character in the cache and database."""
        key = self.__get_char_key(ctx.guild.id, char_id)

        # Normalize kwargs keys to database column names
        kws = {normalize_to_db_row(k): v for k, v in kwargs.items()}

        # Clear character from cache but keep claims cache
        self.characters.pop(key, None)
        self.custom_traits.pop(key, None)
        self.custom_sections.pop(key, None)

        try:
            character = Character.get_by_id(char_id)
        except DoesNotExist as e:
            raise CharacterNotFoundError(e=e) from e

        Character.update(modified=time_now(), **kws).where(Character.id == character.id).execute()

        logger.debug(f"DATABASE: Update character: {char_id}")
        return character

    def update_custom_section(
        self,
        ctx: ApplicationContext,
        custom_section_id: int,
        **kwargs: str | int,
    ) -> CustomSection:
        """Update a custom character section in the cache and database."""
        try:
            custom_section = CustomSection.get_by_id(custom_section_id)
        except DoesNotExist as e:
            raise SectionNotFoundError(f"Custom section {custom_section_id} was not found") from e

        CustomSection.update(modified=time_now(), **kwargs).where(
            CustomSection.id == custom_section.id
        ).execute()

        self.purge_cache(ctx)

        logger.debug(f"DATABASE: Update custom section: {custom_section_id}")
        return custom_section

    def update_trait_value(
        self, ctx: ApplicationContext, character: Character, trait_name: str, new_value: int
    ) -> bool:
        """Update a trait value for a character."""
        # Update traits on the character model
        if hasattr(character, normalize_to_db_row(trait_name)):
            self.update_char(ctx, character.id, **{trait_name: new_value})
            logger.debug(
                f"DATABASE: Update '{trait_name}' for character {character.name} to {new_value}"
            )
            return True

        # Update custom traits

        custom_trait = CustomTrait.get_or_none(
            CustomTrait.character_id == character.id and CustomTrait.name == trait_name.title()
        )

        if custom_trait:
            custom_trait.value = new_value
            custom_trait.save()
            self.update_char(ctx, character.id)
            logger.debug(
                f"DATABASE: Update '{trait_name}' for character {character.name} to {new_value}"
            )

            # Reset custom traits cache for character
            self.purge_cache(ctx)
            return True

        raise TraitNotFoundError


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
            logger.debug(f"CACHE: Return macros for {key}")
            return self.macro_cache[key]

        macros = Macro.select().where((Macro.user == author_id) & (Macro.guild == guild_id))
        self.macro_cache[key] = sorted(macros, key=lambda m: m.name)

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
            logger.info(f"CACHE: Return user {key} from cache")
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
                logger.info(
                    f"DATABASE: Create guild_user lookup for user:{ctx.author.name} guild:{ctx.guild.name}"
                )

            logger.info(f"DATABASE: Create user '{ctx.author.display_name}'")

        else:
            user.last_seen = time_now()
            user.save()

        logger.info(f"CACHE: Add user {user.name}")
        self.user_cache[key] = user
        return user

    def create_macro(
        self,
        ctx: ApplicationContext,
        name: str,
        abbreviation: str,
        description: str,
        trait_one: str,
        trait_two: str,
    ) -> None:
        """Create a new macro for a user."""
        user = self.fetch_user(ctx)
        macro = Macro.create(
            name=name,
            abbreviation=abbreviation,
            description=description,
            guild_id=ctx.guild.id,
            user_id=user.id,
            trait_one=trait_one,
            trait_two=trait_two,
        )
        macro.save()

        self.purge_cache(ctx)
        logger.info(f"DATABASE: Create macro '{name}' for user '{user.name}'")

    def delete_macro(self, ctx: ApplicationContext, macro_name: str) -> None:
        """Delete a macro from the database and purge the user cache."""
        Macro.delete().where(
            (fn.Lower(Macro.name) == macro_name.lower())
            & (Macro.user == ctx.author.id)
            & (Macro.guild == ctx.guild.id)
        ).execute()

        self.purge_cache(ctx)
        logger.info(f"DATABASE: Delete macro '{macro_name}' for user '{ctx.author.name}'")


class GuildService:
    """Manage guilds in the database. Guilds are created on bot connect."""

    def __init__(self) -> None:
        self.log_channel_cache: dict[int, int | None] = {}
        self.settings_cache: dict[int, dict[str, str | int | bool]] = {}
        self.roll_result_thumbs: dict[int, dict[str, list[str]]] = {}

    @staticmethod
    def is_in_db(guild_id: int) -> bool:
        """Check if the guild is in the database."""
        return Guild.select().where(Guild.id == guild_id).exists()

    @staticmethod
    @logger.catch
    def update_or_add(guild: discord.Guild, **kwargs: str | int | datetime) -> None:
        """Add a guild to the database or update it if it already exists."""
        db_id, is_created = Guild.get_or_create(
            id=guild.id,
            defaults={
                "id": guild.id,
                "name": guild.name,
                "created": time_now(),
                "modified": time_now(),
            },
        )
        if is_created:
            logger.info(f"DATABASE: Create guild {db_id.name}")

        if not is_created:
            kwargs["modified"] = time_now()
            Guild.set_by_id(guild.id, kwargs)
            logger.info(f"DATABASE: Update guild '{db_id.name}'")

    @staticmethod
    def fetch_all_traits(
        guild_id: int, flat_list: bool = False
    ) -> dict[str, list[str]] | list[str]:
        """Fetch all traits for a guild inclusive of common and custom.

        Args:
            guild_id (int): The guild to fetch traits for.
            flat_list (bool, optional): Return a flat list of traits. Defaults to False.
        """
        all_constants = [COMMON_TRAITS, MAGE_TRAITS, VAMPIRE_TRAITS, WEREWOLF_TRAITS, HUNTER_TRAITS]
        all_traits = merge_dictionaries(all_constants, flat_list=False)

        if isinstance(all_traits, dict):
            custom_traits = CustomTrait.select().where(CustomTrait.guild == guild_id)
            if len(custom_traits) > 0:
                for custom_trait in custom_traits:
                    if custom_trait.category.title() not in all_traits:
                        all_traits[custom_trait.category.title()] = []
                    all_traits[custom_trait.category.title()].append(custom_trait.name.title())

            if flat_list:
                # Flattens the dictionary to a single list, while removing duplicates
                return sorted(list({item for sublist in all_traits.values() for item in sublist}))

            return all_traits

        return None

    def add_roll_result_thumb(self, ctx: ApplicationContext, roll_type: str, url: str) -> None:
        """Add a roll result thumbnail to the database."""
        UserService().fetch_user(ctx)

        self.roll_result_thumbs.pop(ctx.guild.id, None)

        already_exists = RollThumbnail.get_or_none(guild=ctx.guild.id, url=url)
        if already_exists:
            raise DuplicateRollResultThumbError

        RollThumbnail.create(guild=ctx.guild.id, user=ctx.author.id, url=url, roll_type=roll_type)
        logger.info(f"DATABASE: Add roll result thumbnail for '{ctx.author.display_name}'")

    async def create_bot_log_channel(
        self, guild: discord.Guild, log_channel_name: str
    ) -> discord.TextChannel:
        """Fetch the bot log channel for a guild and create it if it doesn't exist."""
        log_channel = None

        # Use the log channel from the database if it exists
        existing_guild = Guild.get_or_none(id=guild.id)

        for channel in await guild.fetch_channels():
            if existing_guild:
                if channel.id == existing_guild.log_channel_id:
                    log_channel = channel
                    logger.info(f"DATABASE: Fetch bot audit log channel: '{channel.name}'")
                    return channel  # type: ignore [return-value]
            elif channel.name.lower().strip() == log_channel_name.lower().strip():
                print(f"SUCCESS: {channel.name.lower()} == {log_channel_name.lower()}")
                log_channel = channel
                logger.debug(f"BOT: Using '{log_channel_name}' for bot audit logging")
                break

        if not log_channel:
            log_channel = await guild.create_text_channel(
                log_channel_name,
                topic="A channel for Valentina audit logs.",
                position=100,
            )
            logger.info(f"BOT: Created '{log_channel_name}' channel for bot audit logging")

            if existing_guild:
                GuildService.update_or_add(guild, log_channel_id=log_channel.id)

        self.log_channel_cache.pop(guild.id, None)
        return log_channel  # type: ignore [return-value]

    def fetch_log_channel(self, ctx: ApplicationContext) -> int | None:
        """Fetch the log channel for a guild."""
        if ctx.guild.id not in self.log_channel_cache:
            self.log_channel_cache[ctx.guild.id] = Guild.get_by_id(ctx.guild.id).log_channel_id

        return self.log_channel_cache[ctx.guild.id]

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

    def is_audit_logging(self, ctx: ApplicationContext) -> bool:
        """Settings check: audit_log."""
        if ctx.guild.id not in self.settings_cache:
            self.settings_cache[ctx.guild.id] = {}

        if "use_audit_log" not in self.settings_cache[ctx.guild.id]:
            self.settings_cache[ctx.guild.id]["use_audit_log"] = Guild.get_by_id(
                ctx.guild.id
            ).use_audit_log
            logger.debug(f"DATABASE: Fetch audit log setting for '{ctx.guild.name}'")

        return bool(self.settings_cache[ctx.guild.id]["use_audit_log"])

    def purge_cache(self, ctx: ApplicationContext | None = None) -> None:
        """Purge the cache for a guild or all guilds.

        Args:
            ctx (ApplicationContext, optional): The context to purge. Defaults to None.
        """
        if ctx:
            self.log_channel_cache.pop(ctx.guild.id, None)
            self.settings_cache.pop(ctx.guild.id, None)
            self.roll_result_thumbs.pop(ctx.guild.id, None)
            logger.debug(f"DATABASE: Purge guild cache for '{ctx.guild.name}'")
        else:
            self.log_channel_cache = {}
            self.settings_cache = {}
            self.roll_result_thumbs = {}
            logger.debug("DATABASE: Purge all guild caches")

    def set_audit_log(self, ctx: ApplicationContext, value: bool) -> None:
        """Set the value of the audit log setting for a guild."""
        self.settings_cache.pop(ctx.guild.id, None)
        Guild.set_by_id(ctx.guild.id, {"use_audit_log": value})

    async def send_log(self, ctx: ApplicationContext, message: str | discord.Embed) -> None:
        """Send a message to the log channel for a guild."""
        log_channel_id = self.fetch_log_channel(ctx)
        if log_channel_id:
            log_channel = ctx.guild.get_channel(log_channel_id)
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


class DatabaseService:
    """Representation of the database."""

    def __init__(self, database: SqliteDatabase) -> None:
        """Initialize the DatabaseService."""
        self.db = database

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
        """Create all tables in the database and populate default values if they are constants."""
        with self.db:
            self.db.create_tables(
                [
                    Character,
                    CharacterClass,
                    CustomSection,
                    CustomTrait,
                    DatabaseVersion,
                    Guild,
                    GuildUser,
                    Macro,
                    RollThumbnail,
                    User,
                    VampireClan,
                    Chronicle,
                    ChronicleNote,
                    ChronicleChapter,
                    ChronicleNPC,
                ]
            )
        logger.info("DATABASE: Create Tables")
        logger.debug(f"DATABASE: {self.get_tables()}")

    def sync_enums(self) -> None:
        """Ensure that the CharacterClass and VampireCan tables are up to date with their enums."""
        # Populate default values
        for char_class in CharClass:
            CharacterClass.get_or_create(name=char_class.value)

        for clan in VampClanList:
            VampireClan.get_or_create(name=clan.value)

        logger.info("DATABASE: Populate Enums")

    def get_tables(self) -> list[str]:
        """Get all tables in the Database."""
        with self.db:
            cursor = self.db.execute_sql("SELECT name FROM sqlite_master WHERE type='table';")
            return [row[0] for row in cursor.fetchall()]

    def database_version(self) -> str:
        """Get the version of the database."""
        return DatabaseVersion.get_by_id(1).version

    @logger.catch
    def requires_migration(self, bot_version: str) -> bool:
        """Determine if the database requires a migration.

        Args:
            bot_version (str): The version of the bot to compare against the database version.

        Returns:
            bool: True if the database requires a migration, False otherwise.
        """
        current_db, created = DatabaseVersion.get_or_create(
            id=1,
            defaults={"version": bot_version},
        )
        if created:
            logger.info(f"DATABASE: Create version v{bot_version}")
            return False

        if Version.parse(bot_version) > Version.parse(current_db.version):
            logger.info(f"DATABASE: Database v{current_db.version} < bot v{bot_version}")
            return True

        logger.debug(f"DATABASE: Database v{current_db.version} is up to date")
        return False

    @logger.catch
    def migrate_old_database(self, bot_version: str) -> None:
        """Migrate from old database versions to the current one."""
        db_version = DatabaseVersion.get_by_id(1).version

        if Version.parse(db_version) < Version.parse("0.8.2"):
            logger.debug(f"DATABASE: Migrate database v{db_version} to v0.8.2")
            self.db.execute_sql("ALTER TABLE characters ADD COLUMN security INTEGER DEFAULT 0;")

        logger.info(f"DATABASE: Migrate database to v{bot_version}")
        DatabaseVersion.set_by_id(1, {"version": bot_version})
