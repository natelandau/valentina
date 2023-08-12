"""Manage chronicle data."""

from discord import ApplicationContext, AutocompleteContext
from loguru import logger
from peewee import DoesNotExist, IntegrityError

from valentina.models.db_tables import (
    Chronicle,
    ChronicleChapter,
    ChronicleNote,
    ChronicleNPC,
)
from valentina.utils.errors import NoActiveChronicleError
from valentina.utils.helpers import time_now


class ChronicleService:
    """Chronicle Manager cache/in-memory database."""

    # TODO: Ability renumber chapters

    def __init__(self) -> None:
        """Initialize the ChronicleService."""
        # Caches to avoid database queries
        ##################################
        self.active_chronicle_cache: dict[int, Chronicle] = {}  # guild_id: chronicle
        self.chronicle_cache: dict[int, list[Chronicle]] = {}  # guild_id : chronicles
        self.chapter_cache: dict[int, list[ChronicleChapter]] = {}  # ch # chronicle_id. chapters
        self.note_cache: dict[int, list[ChronicleNote]] = {}  # ch # chronicle_id. notes
        self.npc_cache: dict[int, list[ChronicleNPC]] = {}  # ch # chronicle_id. npcs

    def create_chronicle(
        self, ctx: ApplicationContext, name: str, description: str | None = None
    ) -> Chronicle:
        """Create and return a new chronicle in the database.

        Args:
            ctx (ApplicationContext): The application context.
            name (str): The name of the chronicle.
            description (str, optional): The description of the chronicle. Defaults to None.

        Returns:
            Chronicle: The created Chronicle object.

        Raises:
            ValueError: If a chronicle with the same name already exists in the database.
        """
        try:
            chronicle = Chronicle.create(
                guild_id=ctx.guild.id,
                name=name,
                description=description,
                created=time_now(),
                modified=time_now(),
                is_active=False,
            )
        except IntegrityError as e:
            raise ValueError(f"Chronicle '{name}' already exists.") from e

        # Remove this guild's chronicles from the cache, forcing a refresh next time they're accessed
        self.purge_cache(ctx)

        logger.info(f"CHRONICLE: Created '{name}' for guild ID: {ctx.guild.id}")

        return chronicle

    def create_chapter(
        self,
        ctx: ApplicationContext,
        chronicle: Chronicle,
        name: str,
        short_description: str,
        description: str,
    ) -> ChronicleChapter:
        """Create and return a new chapter in the given chronicle.

        Args:
            ctx (ApplicationContext): The application context.
            chronicle (Chronicle): The chronicle object to which the chapter will belong.
            name (str): The name of the chapter.
            short_description (str): The short description of the chapter.
            description (str): The description of the chapter.

        Returns:
            ChronicleChapter: The created ChronicleChapter object.
        """
        last_chapter = max([x.chapter for x in self.fetch_all_chapters(chronicle)], default=0)

        new_chapter_number = last_chapter + 1

        chapter = ChronicleChapter.create(
            chronicle=chronicle.id,
            chapter=new_chapter_number,
            name=name,
            short_description=short_description,
            description=description,
            created=time_now(),
            modified=time_now(),
        )
        logger.info(
            f"CHRONICLE: Create Chapter '{name}' (#{new_chapter_number}) for chronicle ID: {chronicle.name} in guild ID: {ctx.guild.id}"
        )

        # Remove this guild's chapters from the cache, forcing a refresh next time they're accessed
        self.purge_cache(ctx)

        return chapter

    def create_note(
        self,
        ctx: ApplicationContext,
        chronicle: Chronicle,
        name: str,
        description: str,
        chapter: ChronicleChapter | None = None,
    ) -> ChronicleNote:
        """Create and return a new note in the given chronicle.

        Args:
            ctx (ApplicationContext): The application context.
            chronicle (Chronicle): The chronicle object to which the note will belong.
            name (str): The name of the note.
            description (str): The description of the note.
            chapter (ChronicleChapter, optional): The chapter object to which the note will belong. Defaults to None.

        Returns:
            ChronicleNote: The created ChronicleNote object.

        TODO: Write test for this method that mocks the call to fetch_user
        """
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
        # Remove this guild's notes from the cache, forcing a refresh next time they're accessed
        self.purge_cache(ctx)

        logger.info(f"CHRONICLE: Create Note '{name}' ({note.id}) for guild: {ctx.guild.name}")

        return note

    def create_npc(
        self,
        ctx: ApplicationContext,
        chronicle: Chronicle,
        name: str,
        npc_class: str,
        description: str,
    ) -> ChronicleNPC:
        """Create and return a new NPC for the given chronicle.

        Args:
            ctx (ApplicationContext): The application context.
            chronicle (Chronicle): The chronicle object to which the NPC will belong.
            name (str): The name of the NPC.
            npc_class (str): The class of the NPC.
            description (str): The description of the NPC.

        Returns:
            ChronicleNPC: The created ChronicleNPC object.
        """
        npc = ChronicleNPC.create(
            chronicle=chronicle.id,
            name=name,
            npc_class=npc_class,
            description=description,
            created=time_now(),
            modified=time_now(),
        )
        # Remove this guild's npcs from the cache, forcing a refresh next time they're accessed
        self.npc_cache.pop(ctx.guild.id, None)

        logger.info(f"CHRONICLE: Create NPC {name} for guild {ctx.guild.id}")

        return npc

    def delete_chronicle(self, ctx: ApplicationContext, chronicle: Chronicle) -> None:
        """Delete a chronicle and all its associated contents, also clear associated cache.

        Args:
            ctx (ApplicationContext): The application context.
            chronicle (Chronicle): The chronicle object to be deleted.
        """
        # Remove all the associated caches for the guild
        self.purge_cache(ctx)

        try:
            # Delete the chronicle and all its associated content
            chronicle.delete_instance(recursive=True, delete_nullable=True)
            logger.info(
                f"CHRONICLE: Successfully deleted '{chronicle.name}' and all associated content for guild ID: {ctx.guild.id}"
            )

        except Exception as e:
            # Log the error and re-raise
            logger.error(
                f"CHRONICLE: Failed to delete '{chronicle.name}' for guild ID: {ctx.guild.id}, due to error: {e!s}"
            )
            raise

    def delete_chapter(self, ctx: ApplicationContext, chapter: ChronicleChapter) -> None:
        """Delete a specified chapter and clear the chapter cache for the guild.

        Args:
            ctx (ApplicationContext): The application context which includes information about the guild.
            chapter (ChronicleChapter): The ChronicleChapter instance to be deleted.

        """
        chapter.delete_instance(recursive=True, delete_nullable=True)

        self.purge_cache(ctx)

        logger.info(f"CHRONICLE: Delete Chapter {chapter.name} for guild {ctx.guild.id}")

    def delete_note(self, ctx: ApplicationContext, note: ChronicleNote) -> None:
        """Delete a specified note from the chronicle and refresh the note cache for the guild.

        Args:
            ctx (ApplicationContext): The application context, which includes details about the guild.
            note (ChronicleNote): The ChronicleNote instance to be deleted.
        """
        note.delete_instance(recursive=True, delete_nullable=True)

        # Clear the note cache for this guild, forcing a refresh next time they're accessed
        self.purge_cache(ctx)

        logger.info(f"CHRONICLE: Deleted Note '{note.name}' from guild ID: {ctx.guild.id}")

    def delete_npc(self, ctx: ApplicationContext, npc: ChronicleNPC) -> None:
        """Delete a specific NPC from the chronicle and clear the NPC cache for the guild.

        Args:
            ctx (ApplicationContext): The application context containing information about the guild.
            npc (ChronicleNPC): The ChronicleNPC instance to be deleted.

        """
        npc.delete_instance(recursive=True, delete_nullable=True)

        # Clear the NPC cache for this guild, forcing a refresh next time they're accessed
        self.purge_cache(ctx)

        logger.info(f"CHRONICLE: Delete NPC '{npc.name}' from guild ID: {ctx.guild.id}")

    def fetch_active(self, ctx: ApplicationContext | AutocompleteContext) -> Chronicle:
        """Fetch the active chronicle for the guild.

        Args:
            ctx (ApplicationContext | AutocompleteContext): Context which provides information about the guild.

        Returns:
            Chronicle: The active chronicle for the guild.

        Raises:
            ValueError: If no active chronicle is found.
        """
        # Determine the guild ID from the context
        guild_id = ctx.guild.id if isinstance(ctx, ApplicationContext) else ctx.interaction.guild.id

        # Fetch active chronicle from the cache or database
        if guild_id in self.active_chronicle_cache and self.active_chronicle_cache[guild_id]:
            logger.debug(f"CACHE: Return active chronicle for guild {guild_id}")
            return self.active_chronicle_cache[guild_id]

        try:
            # Not in cache, fetch from the database
            active_chronicle = Chronicle.get(guild=guild_id, is_active=True)
            self.active_chronicle_cache[guild_id] = active_chronicle
            logger.debug(f"DATABASE: Fetch active chronicle for guild {guild_id}")
        except DoesNotExist as e:
            raise NoActiveChronicleError from e

        self.active_chronicle_cache[guild_id] = active_chronicle

        return active_chronicle

    def fetch_all(self, ctx: ApplicationContext | AutocompleteContext) -> list[Chronicle]:
        """Fetch all chronicles for a guild.

        This method first checks if the guild's chronicles are present in the cache. If not, it fetches all chronicles for the guild from the database and updates the cache.

        Args:
            ctx (ApplicationContext | AutocompleteContext):
                Context providing information about the guild from where to fetch the chronicles.

        Returns:
            list[Chronicle]: A list of all chronicles for the guild.

        Raises:
            ValueError: If no chronicles are found for the guild.
        """
        # Determine the guild ID from the context
        guild_id = ctx.guild.id if isinstance(ctx, ApplicationContext) else ctx.interaction.guild.id

        # If the guild's chronicles are already in the cache, return them
        if guild_id in self.chronicle_cache and self.chronicle_cache[guild_id]:
            logger.debug(f"CACHE: Return all chronicles for guild {guild_id}")
            return self.chronicle_cache[guild_id]

        # Fetch all chronicles for the guild from the database
        try:
            logger.debug(f"DATABASE: Fetch all chronicles for guild {guild_id}")
            chronicles = [x for x in Chronicle.select().where(Chronicle.guild == guild_id)]

        except DoesNotExist as e:
            raise ValueError("No chronicles found") from e

        # Update the cache with the fetched chronicles
        self.chronicle_cache[guild_id] = chronicles

        return chronicles

    def fetch_chapter_by_id(self, chapter_id: int) -> ChronicleChapter:
        """Fetch a chapter by its ID.

        Args:
            chapter_id (int): The ID of the chapter.

        Returns:
            ChronicleChapter: The chapter with the corresponding ID.

        Raises:
            ValueError: If no chapter is found with the given ID.
        """
        try:
            # Fetch chapter from database if not in cache.
            chapter = ChronicleChapter.get(id=chapter_id)
            # Update cache.

            logger.debug(f"DATABASE: fetch chapter {chapter.id}")
            return chapter
        except DoesNotExist as e:
            raise ValueError(f"No chapter found with ID {chapter_id}") from e

    def fetch_chapter_by_name(self, chronicle: Chronicle, name: str) -> ChronicleChapter:
        """Fetch a chapter by its name.

        Args:
            chronicle (Chronicle): The chronicle in which to search for the chapter.
            name (str): The name of the chapter.

        Returns:
            ChronicleChapter: The chapter with the corresponding name.

        Raises:
            ValueError: If no chapter is found with the given name.
        """
        name = name.strip()

        try:
            # Fetch chapter from database if not in cache.
            chapter = ChronicleChapter.get(chronicle=chronicle.id, name=name)
            # Update cache.

            logger.debug(f"DATABASE: fetch chapter {chapter.name}")
            return chapter
        except DoesNotExist as e:
            raise ValueError(f"No chapter found with name {name}") from e

    def fetch_all_chapters(self, chronicle: Chronicle) -> list[ChronicleChapter]:
        """Fetch all chapters for a chronicle.

        This method first checks if the chapters for the given chronicle are present in the cache.
        If not, it fetches all chapters for the chronicle from the database and updates the cache.

        Args:
            chronicle (Chronicle): The chronicle object for which to fetch the chapters.

        Returns:
            list[ChronicleChapter]: A list of all chapters for the chronicle.

        Raises:
            ValueError: If no chapters are found for the chronicle.
        """
        # If the chapters for this chronicle are already in the cache, return them

        if chronicle.id in self.chapter_cache and self.chapter_cache[chronicle.id]:
            logger.debug(f"CACHE: Return all chapters for chronicle {chronicle.id}")
            return self.chapter_cache[chronicle.id]

        # Fetch all chapters for the chronicle from the database
        try:
            chapters = [
                x
                for x in ChronicleChapter.select().where(ChronicleChapter.chronicle == chronicle.id)
            ]
            logger.debug(f"DATABASE: Fetch all chapters for chronicle {chronicle.id}")
        except DoesNotExist as e:
            raise ValueError("No chapters found") from e

        # Update the cache with the fetched chapters
        self.chapter_cache[chronicle.id] = chapters

        return chapters

    def fetch_all_notes(self, chronicle: Chronicle) -> list[ChronicleNote]:
        """Fetch all notes for a chronicle.

        This method first checks if the notes for the given chronicle are present in the cache.
        If not, it fetches all notes for the chronicle from the database and updates the cache.

        Args:
            chronicle (Chronicle): The chronicle object for which to fetch the notes.

        Returns:
            list[ChronicleNote]: A list of all notes for the chronicle.

        Raises:
            ValueError: If no notes are found for the chronicle.
        """
        if chronicle.id in self.note_cache and self.note_cache[chronicle.id]:
            logger.debug(f"CACHE: Return notes for chronicle {chronicle.id}")
            return self.note_cache[chronicle.id]

        notes = [
            note
            for note in ChronicleNote.select().where(ChronicleNote.chronicle_id == chronicle.id)
        ]
        logger.debug(f"DATABASE: Fetch all notes for chronicle {chronicle.id}")

        self.note_cache[chronicle.id] = notes

        return notes

    def fetch_note_by_id(self, note_id: int) -> ChronicleNote:
        """Fetch a note by its ID.

        This method first checks if the note with the given ID is present in the cache.
        If not, it fetches the note from the database.

        Args:
            note_id (int): The ID of the note to fetch.

        Returns:
            ChronicleNote: The note corresponding to the given ID.

        Raises:
            ValueError: If no note is found with the given ID.
        """
        try:
            note = ChronicleNote.get(id=note_id)
            logger.debug(f"DATABASE: Fetch note id {note_id}")
        except DoesNotExist as e:
            raise ValueError(f"No note found with ID {note_id}") from e

        return note

    def fetch_all_npcs(self, chronicle: Chronicle) -> list[ChronicleNPC]:
        """Fetch all NPCs for a chronicle.

        This method first checks if the NPCs for the given chronicle are present in the cache.
        If not, it fetches all NPCs for the chronicle from the database and updates the cache.

        Args:
            chronicle (Chronicle): The chronicle object for which to fetch the NPCs.

        Returns:
            list[ChronicleNPC]: A list of all NPCs for the chronicle.

        Raises:
            ValueError: If no NPCs are found for the chronicle.
        """
        # Return the cache if it exists
        if chronicle.id in self.npc_cache and self.npc_cache[chronicle.id]:
            logger.debug(f"CACHE: Return npcs for chronicle {chronicle.id}")
            return self.npc_cache[chronicle.id]

        try:
            npcs = [
                npc for npc in ChronicleNPC.select().where(ChronicleNPC.chronicle == chronicle.id)
            ]
            logger.debug(f"DATABASE: Fetch all NPCs for chronicle {chronicle.name}")
        except DoesNotExist as e:
            raise ValueError("No NPCs found") from e

        self.npc_cache[chronicle.id] = npcs

        return self.npc_cache[chronicle.id]

    def fetch_npc_by_name(
        self, ctx: ApplicationContext, chronicle: Chronicle, name: str
    ) -> ChronicleNPC:
        """Fetch an NPC by its name.

        # TODO: Refactor into an `option` and a `converter`

        This method first checks if the NPC with the given name is present in the cache.
        If not, it fetches the NPC from the database.

        Args:
            ctx (ApplicationContext): Context providing information about the guild from where to fetch the NPC.
            chronicle (Chronicle): The chronicle object from where to fetch the NPC.
            name (str): The name of the NPC to fetch.

        Returns:
            ChronicleNPC: The NPC corresponding to the given name.

        Raises:
            ValueError: If no NPC is found with the given name.
        """
        guild_id = ctx.guild.id

        try:
            npc = ChronicleNPC.get(name=name, chronicle=chronicle.id)
            logger.debug(f"DATABASE: Fetch NPC for guild {guild_id}")
        except DoesNotExist as e:
            raise ValueError(f"No NPC found with name {name}") from e

        return npc

    def set_active(self, ctx: ApplicationContext, chronicle: Chronicle) -> None:
        """Set a chronicle as active.

        This method deactivates all other chronicles and sets the specified one as active.  It first fetches all chronicles for the guild, either from the cache or the database.

        Args:
            ctx (ApplicationContext): Context providing information about the guild.
            chronicle (Chronicle): The chronicle to set active

        Raises:
            ValueError: If no chronicle is found with the given name.
        """
        # Set any other chronicle that is active to inactive
        chronicles = Chronicle.select().where(Chronicle.guild_id == ctx.guild.id)

        for c in chronicles:
            if c == chronicle:
                c.is_active = True
                c.modified = time_now()
                c.save()
            elif c.is_active:
                c.is_active = False
                c.modified = time_now()
                c.save()

        self.purge_cache(ctx)
        logger.info(f"CHRONICLE: Set {chronicle.name} as active")

    def set_inactive(self, ctx: ApplicationContext) -> None:
        """Set the active chronicle to inactive.

        This method fetches the active chronicle and sets its `is_active` status to `False`.
        It then updates the corresponding chronicle in the cache and saves the changes to the database.

        Args:
            ctx (ApplicationContext): Context providing information about the guild.

        Raises:
            ValueError: If no active chronicle is found.
        """
        # Fetch the active chronicle
        chronicle = self.fetch_active(ctx)

        # Set the chronicle to inactive and save the changes
        chronicle.is_active = False
        chronicle.modified = time_now()
        chronicle.save()

        # Update the cache
        guild_id = ctx.guild.id
        self.active_chronicle_cache[guild_id] = None

        logger.debug(f"CHRONICLE: Set {chronicle.name} as inactive")

    def purge_cache(self, ctx: ApplicationContext | None = None) -> None:
        """Purge the cache.

        This method purges the cache by either removing all entries associated with a specific guild or clearing all entries if no specific guild is provided. It uses the guild ID as the key for each cache dictionary.

        Args:
            ctx (ApplicationContext | None, optional): Context which provides information about the guild.
        """
        if ctx:
            logger.info(f"CHRONICLE: Purge cache for guild {ctx.guild.id}")
            ids = Chronicle.select(Chronicle.id).where(Chronicle.guild == ctx.guild.id)
            for i in ids:
                self.chapter_cache.pop(i.id, None)
                self.note_cache.pop(i.id, None)
                self.npc_cache.pop(i.id, None)
            self.chronicle_cache.pop(ctx.guild.id, None)
            self.active_chronicle_cache.pop(ctx.guild.id, None)
        else:
            caches: list[dict] = [
                self.chronicle_cache,
                self.active_chronicle_cache,
                self.chapter_cache,
                self.note_cache,
                self.npc_cache,
            ]
            for cache in caches:
                cache.clear()
            logger.info("CHRONICLE: Purge cache")

    def update_chapter(
        self, ctx: ApplicationContext, chapter: ChronicleChapter, **kwargs: str
    ) -> None:
        """Update a chapter.

        This method updates the provided chapter with the values supplied through kwargs, then updates the modified timestamp, and removes the chapter's guild from the cache.

        Args:
            ctx (ApplicationContext): The application context carrying metadata for the command invocation.
            chapter (ChronicleChapter): The chapter to be updated.
            **kwargs (str): Field-value pairs to update on the chapter.
        """
        try:
            ChronicleChapter.update(modified=time_now(), **kwargs).where(
                ChronicleChapter.id == chapter.id
            ).execute()

            self.purge_cache(ctx)

            logger.debug(f"CHRONICLE: Update chapter {chapter.name} for guild {ctx.guild.id}")

        except DoesNotExist as e:
            logger.error(
                f"CHRONICLE: Chapter {chapter.name} does not exist for guild {ctx.guild.id}"
            )
            raise ValueError(f"No chapter found with ID {chapter.id}") from e

        except Exception as e:
            logger.error(
                f"CHRONICLE: Unexpected error occurred while updating chapter {chapter.name} for guild {ctx.guild.id}"
            )
            raise e

    def update_chronicle(
        self, ctx: ApplicationContext, chronicle: Chronicle, **kwargs: str
    ) -> None:
        """Update a chronicle.

        This method updates the provided chronicle with the values supplied through kwargs, then updates the modified timestamp, and purges the cache.

        Args:
            ctx (ApplicationContext): The application context carrying metadata for the command invocation.
            chronicle (Chronicle): The chronicle to be updated.
            **kwargs (str): Field-value pairs to update on the chronicle.
        """
        try:
            Chronicle.update(modified=time_now(), **kwargs).where(
                Chronicle.id == chronicle.id
            ).execute()

            self.purge_cache(ctx)

        except DoesNotExist as e:
            logger.error(f"CHRONICLE: Chronicle does not exist for guild {ctx.guild.id}")
            raise ValueError(f"No chronicle found with ID {chronicle.id}") from e
        except Exception as e:
            logger.error(
                f"CHRONICLE: Unexpected error occurred while updating chronicle for guild {ctx.guild.id}"
            )
            raise e

    def update_note(self, ctx: ApplicationContext, note: ChronicleNote, **kwargs: str) -> None:
        """Update a note.

        This method updates the provided note with the values supplied through kwargs, then updates the modified timestamp, and removes the note's guild from the cache.

        Args:
            ctx (ApplicationContext): The application context carrying metadata for the command invocation.
            note (ChronicleNote): The note to be updated.
            **kwargs (str): Field-value pairs to update on the note.
        """
        try:
            ChronicleNote.update(modified=time_now(), **kwargs).where(
                ChronicleNote.id == note.id
            ).execute()

            self.purge_cache(ctx)

            logger.debug(f"CHRONICLE: Update note {note.name} for guild {ctx.guild.id}")
        except DoesNotExist as e:
            logger.error(f"CHRONICLE: Note does not exist for guild {ctx.guild.id}")
            raise ValueError(f"No note found with ID {note.id}") from e
        except Exception as e:
            logger.error(
                f"CHRONICLE: Unexpected error occurred while updating note for guild {ctx.guild.id}"
            )
            raise e

    def update_npc(self, ctx: ApplicationContext, npc: ChronicleNPC, **kwargs: str) -> None:
        """Update an NPC.

        This method updates the provided NPC with the values supplied through kwargs, then updates the modified timestamp, and removes the NPC's guild from the cache.

        Args:
            ctx (ApplicationContext): The application context carrying metadata for the command invocation.
            npc (ChronicleNPC): The NPC to be updated.
            **kwargs (str): Field-value pairs to update on the NPC.
        """
        try:
            ChronicleNPC.update(modified=time_now(), **kwargs).where(
                ChronicleNPC.id == npc.id
            ).execute()

            self.purge_cache(ctx)

            logger.debug(f"CHRONICLE: Update NPC {npc.name} for guild {ctx.guild.id}")
        except DoesNotExist as e:
            logger.error(f"CHRONICLE: NPC does not exist for guild {ctx.guild.id}")
            raise ValueError(f"No NPC found with ID {npc.id}") from e
        except Exception as e:
            logger.error(
                f"CHRONICLE: Unexpected error occurred while updating NPC for guild {ctx.guild.id}"
            )
            raise e
