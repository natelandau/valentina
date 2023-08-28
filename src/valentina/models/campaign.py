"""Manage campaign data."""

import discord
from discord import AutocompleteContext
from loguru import logger
from peewee import DoesNotExist, IntegrityError

from valentina.models.db_tables import (
    Campaign,
    CampaignChapter,
    CampaignNote,
    CampaignNPC,
)
from valentina.utils import errors
from valentina.utils.helpers import time_now


class CampaignService:
    """Campaign Manager cache/in-memory database."""

    def __init__(self) -> None:
        """Initialize the CampaignService."""
        # Caches to avoid database queries
        ##################################
        self.active_campaign_cache: dict[int, Campaign] = {}  # guild_id: campaign
        self.campaign_cache: dict[int, list[Campaign]] = {}  # guild_id : campaigns
        self.chapter_cache: dict[int, list[CampaignChapter]] = {}  # ch # campaign_id. chapters
        self.note_cache: dict[int, list[CampaignNote]] = {}  # ch # campaign_id. notes
        self.npc_cache: dict[int, list[CampaignNPC]] = {}  # ch # campaign_id. npcs

    def create_campaign(
        self, ctx: discord.ApplicationContext, name: str, description: str | None = None
    ) -> Campaign:
        """Create and return a new campaign in the database.

        Args:
            ctx (ApplicationContext): The application context.
            name (str): The name of the campaign.
            description (str, optional): The description of the campaign. Defaults to None.

        Returns:
            Campaign: The created Campaign object.

        Raises:
            ValidationError: If a campaign with the same name already exists in the database.
        """
        try:
            campaign = Campaign.create(
                guild_id=ctx.guild.id,
                name=name,
                description=description,
                created=time_now(),
                modified=time_now(),
                is_active=False,
            )
        except IntegrityError as e:
            raise errors.ValidationError(f"Campaign '{name}' already exists.") from e

        # Remove this guild's campaigns from the cache, forcing a refresh next time they're accessed
        self.purge_cache(ctx)

        logger.info(f"CAMPAIGN: Created '{name}' for guild ID: {ctx.guild.id}")

        return campaign

    def create_chapter(
        self,
        ctx: discord.ApplicationContext,
        campaign: Campaign,
        name: str,
        short_description: str,
        description: str,
    ) -> CampaignChapter:
        """Create and return a new chapter in the given campaign.

        Args:
            ctx (ApplicationContext): The application context.
            campaign (Campaign): The campaign object to which the chapter will belong.
            name (str): The name of the chapter.
            short_description (str): The short description of the chapter.
            description (str): The description of the chapter.

        Returns:
            CampaignChapter: The created CampaignChapter object.
        """
        last_chapter = max([x.chapter_number for x in self.fetch_all_chapters(campaign)], default=0)

        new_chapter_number = last_chapter + 1

        chapter = CampaignChapter.create(
            campaign=campaign.id,
            chapter_number=new_chapter_number,
            name=name,
            short_description=short_description,
            description=description,
            created=time_now(),
            modified=time_now(),
        )
        logger.info(
            f"CAMPAIGN: Create Chapter '{name}' (#{new_chapter_number}) for campaign ID: {campaign.name} in guild ID: {ctx.guild.id}"
        )

        # Remove this guild's chapters from the cache, forcing a refresh next time they're accessed
        self.purge_cache(ctx)

        return chapter

    def create_note(
        self,
        ctx: discord.ApplicationContext,
        campaign: Campaign,
        name: str,
        description: str,
        chapter: CampaignChapter | None = None,
    ) -> CampaignNote:
        """Create and return a new note in the given campaign.

        Args:
            ctx (ApplicationContext): The application context.
            campaign (Campaign): The campaign object to which the note will belong.
            name (str): The name of the note.
            description (str): The description of the note.
            chapter (CampaignChapter, optional): The chapter object to which the note will belong. Defaults to None.

        Returns:
            CampaignNote: The created CampaignNote object.

        TODO: Write test for this method that mocks the call to fetch_user
        """
        user = ctx.bot.user_svc.fetch_user(ctx)  # type: ignore [attr-defined] # it really is defined

        note = CampaignNote.create(
            campaign=campaign.id,
            name=name,
            description=description,
            user=user.id,
            created=time_now(),
            modified=time_now(),
            chapter=chapter.id if chapter else None,
        )
        # Remove this guild's notes from the cache, forcing a refresh next time they're accessed
        self.purge_cache(ctx)

        logger.info(f"CAMPAIGN: Create Note '{name}' ({note.id}) for guild: {ctx.guild.name}")

        return note

    def create_npc(
        self,
        ctx: discord.ApplicationContext,
        campaign: Campaign,
        name: str,
        npc_class: str,
        description: str,
    ) -> CampaignNPC:
        """Create and return a new NPC for the given campaign.

        Args:
            ctx (ApplicationContext): The application context.
            campaign (Campaign): The campaign object to which the NPC will belong.
            name (str): The name of the NPC.
            npc_class (str): The class of the NPC.
            description (str): The description of the NPC.

        Returns:
            CampaignNPC: The created CampaignNPC object.
        """
        npc = CampaignNPC.create(
            campaign=campaign.id,
            name=name,
            npc_class=npc_class,
            description=description,
            created=time_now(),
            modified=time_now(),
        )

        # Remove this guild's npcs from the cache, forcing a refresh next time they're accessed
        self.purge_cache(ctx)

        logger.info(f"CAMPAIGN: Create NPC {name} for guild {ctx.guild.id}")

        return npc

    def delete_campaign(self, ctx: discord.ApplicationContext, campaign: Campaign) -> None:
        """Delete a campaign and all its associated contents, also clear associated cache.

        Args:
            ctx (ApplicationContext): The application context.
            campaign (Campaign): The campaign object to be deleted.
        """
        # Remove all the associated caches for the guild
        self.purge_cache(ctx)

        try:
            # Delete the campaign and all its associated content
            campaign.delete_instance(recursive=True, delete_nullable=True)
            self.purge_cache(ctx)
            logger.info(
                f"CAMPAIGN: Delete '{campaign.name}' and all content for guild ID: {ctx.guild.id}"
            )

        except Exception as e:
            # Log the error and re-raise
            logger.error(
                f"CAMPAIGN: Failed to delete '{campaign.name}' for guild ID: {ctx.guild.id}, due to error: {e!s}"
            )
            raise

    def delete_chapter(self, ctx: discord.ApplicationContext, chapter: CampaignChapter) -> None:
        """Delete a specified chapter and clear the chapter cache for the guild.

        Args:
            ctx (ApplicationContext): The application context which includes information about the guild.
            chapter (CampaignChapter): The CampaignChapter instance to be deleted.

        """
        chapter.delete_instance(recursive=True, delete_nullable=True)

        self.purge_cache(ctx)

        logger.info(f"CAMPAIGN: Delete Chapter {chapter.name} for guild {ctx.guild.id}")

    def delete_note(self, ctx: discord.ApplicationContext, note: CampaignNote) -> None:
        """Delete a specified note from the campaign and refresh the note cache for the guild.

        Args:
            ctx (ApplicationContext): The application context, which includes details about the guild.
            note (CampaignNote): The CampaignNote instance to be deleted.
        """
        note.delete_instance(recursive=True, delete_nullable=True)

        # Clear the note cache for this guild, forcing a refresh next time they're accessed
        self.purge_cache(ctx)

        logger.info(f"CAMPAIGN: Deleted Note '{note.name}' from guild ID: {ctx.guild.id}")

    def delete_npc(self, ctx: discord.ApplicationContext, npc: CampaignNPC) -> None:
        """Delete a specific NPC from the campaign and clear the NPC cache for the guild.

        Args:
            ctx (ApplicationContext): The application context containing information about the guild.
            npc (CampaignNPC): The CampaignNPC instance to be deleted.

        """
        npc.delete_instance(recursive=True, delete_nullable=True)

        # Clear the NPC cache for this guild, forcing a refresh next time they're accessed
        self.purge_cache(ctx)

        logger.info(f"CAMPAIGN: Delete NPC '{npc.name}' from guild ID: {ctx.guild.id}")

    def fetch_active(self, ctx: discord.ApplicationContext | AutocompleteContext) -> Campaign:
        """Fetch the active campaign for the guild.

        Args:
            ctx (ApplicationContext | AutocompleteContext): Context which provides information about the guild.

        Returns:
            Campaign: The active campaign for the guild.

        Raises:
            NoActiveCampaignError: If no active campaign is found.
        """
        # Determine the guild ID from the context
        guild_id = (
            ctx.guild.id
            if isinstance(ctx, discord.ApplicationContext)
            else ctx.interaction.guild.id
        )

        # Fetch active campaign from the cache or database
        if guild_id in self.active_campaign_cache and self.active_campaign_cache[guild_id]:
            logger.debug(f"CACHE: Return active campaign for guild {guild_id}")
            return self.active_campaign_cache[guild_id]

        try:
            # Not in cache, fetch from the database
            active_campaign = Campaign.get(guild=guild_id, is_active=True)
            self.active_campaign_cache[guild_id] = active_campaign
            logger.debug(f"DATABASE: Fetch active campaign for guild {guild_id}")
        except DoesNotExist as e:
            raise errors.NoActiveCampaignError from e

        self.active_campaign_cache[guild_id] = active_campaign

        return active_campaign

    def fetch_all(self, ctx: discord.ApplicationContext | AutocompleteContext) -> list[Campaign]:
        """Fetch all campaigns for a guild.

        This method first checks if the guild's campaigns are present in the cache. If not, it fetches all campaigns for the guild from the database and updates the cache.

        Args:
            ctx (ApplicationContext | AutocompleteContext):
                Context providing information about the guild from where to fetch the campaigns.

        Returns:
            list[Campaign]: A list of all campaigns for the guild.

        Raises:
            ValidationError: If no campaigns are found for the guild.
        """
        # Determine the guild ID from the context
        guild_id = (
            ctx.guild.id
            if isinstance(ctx, discord.ApplicationContext)
            else ctx.interaction.guild.id
        )

        # If the guild's campaigns are already in the cache, return them
        if guild_id in self.campaign_cache and self.campaign_cache[guild_id]:
            logger.debug(f"CACHE: Return all campaigns for guild {guild_id}")
            return self.campaign_cache[guild_id]

        # Fetch all campaigns for the guild from the database
        try:
            logger.debug(f"DATABASE: Fetch all campaigns for guild {guild_id}")
            campaigns = [x for x in Campaign.select().where(Campaign.guild == guild_id)]

        except DoesNotExist as e:
            raise errors.ValidationError("No campaigns found") from e

        # Update the cache with the fetched campaigns
        self.campaign_cache[guild_id] = campaigns

        return campaigns

    def fetch_chapter_by_id(self, chapter_id: int) -> CampaignChapter:
        """Fetch a chapter by its ID.

        Args:
            chapter_id (int): The ID of the chapter.

        Returns:
            CampaignChapter: The chapter with the corresponding ID.

        Raises:
            DatabaseError: If no chapter is found with the given ID.
        """
        try:
            # Fetch chapter from database if not in cache.
            chapter = CampaignChapter.get(id=chapter_id)
            # Update cache.

            logger.debug(f"DATABASE: fetch chapter {chapter.id}")
            return chapter
        except DoesNotExist as e:
            raise errors.DatabaseError(f"No chapter found with ID {chapter_id}") from e

    def fetch_chapter_by_name(self, campaign: Campaign, name: str) -> CampaignChapter:
        """Fetch a chapter by its name.

        Args:
            campaign (Campaign): The campaign in which to search for the chapter.
            name (str): The name of the chapter.

        Returns:
            CampaignChapter: The chapter with the corresponding name.

        Raises:
            DatabaseError: If no chapter is found with the given name.
        """
        name = name.strip()

        try:
            # Fetch chapter from database if not in cache.
            chapter = CampaignChapter.get(campaign=campaign.id, name=name)
            # Update cache.

            logger.debug(f"DATABASE: fetch chapter {chapter.name}")
            return chapter
        except DoesNotExist as e:
            raise errors.DatabaseError(f"No chapter found with name {name}") from e

    def fetch_all_chapters(self, campaign: Campaign) -> list[CampaignChapter]:
        """Fetch all chapters for a campaign.

        This method first checks if the chapters for the given campaign are present in the cache.
        If not, it fetches all chapters for the campaign from the database and updates the cache.

        Args:
            campaign (Campaign): The campaign object for which to fetch the chapters.

        Returns:
            list[CampaignChapter]: A list of all chapters for the campaign.

        Raises:
            NoMatchingItemsError: If no chapters are found for the campaign.
        """
        # If the chapters for this campaign are already in the cache, return them

        if campaign.id in self.chapter_cache and self.chapter_cache[campaign.id]:
            logger.debug(f"CACHE: Return all chapters for campaign {campaign.id}")
            return self.chapter_cache[campaign.id]

        # Fetch all chapters for the campaign from the database
        try:
            chapters = [
                x for x in CampaignChapter.select().where(CampaignChapter.campaign == campaign.id)
            ]
            logger.debug(f"DATABASE: Fetch all chapters for campaign {campaign.id}")
        except DoesNotExist as e:
            raise errors.NoMatchingItemsError("No chapters found") from e

        # Update the cache with the fetched chapters
        self.chapter_cache[campaign.id] = chapters

        return chapters

    def fetch_all_notes(self, campaign: Campaign) -> list[CampaignNote]:
        """Fetch all notes for a campaign.

        This method first checks if the notes for the given campaign are present in the cache.
        If not, it fetches all notes for the campaign from the database and updates the cache.

        Args:
            campaign (Campaign): The campaign object for which to fetch the notes.

        Returns:
            list[CampaignNote]: A list of all notes for the campaign.
        """
        if campaign.id in self.note_cache and self.note_cache[campaign.id]:
            logger.debug(f"CACHE: Return notes for campaign {campaign.id}")
            return self.note_cache[campaign.id]

        notes = [
            note for note in CampaignNote.select().where(CampaignNote.campaign_id == campaign.id)
        ]
        logger.debug(f"DATABASE: Fetch all notes for campaign {campaign.id}")

        self.note_cache[campaign.id] = notes

        return notes

    def fetch_note_by_id(self, note_id: int) -> CampaignNote:
        """Fetch a note by its ID.

        This method first checks if the note with the given ID is present in the cache.
        If not, it fetches the note from the database.

        Args:
            note_id (int): The ID of the note to fetch.

        Returns:
            CampaignNote: The note corresponding to the given ID.

        Raises:
            DatabaseError: If no note is found with the given ID.
        """
        try:
            note = CampaignNote.get(id=note_id)
            logger.debug(f"DATABASE: Fetch note id {note_id}")
        except DoesNotExist as e:
            raise errors.DatabaseError(f"No note found with ID {note_id}") from e

        return note

    def fetch_all_npcs(self, campaign: Campaign) -> list[CampaignNPC]:
        """Fetch all NPCs for a campaign.

        This method first checks if the NPCs for the given campaign are present in the cache.
        If not, it fetches all NPCs for the campaign from the database and updates the cache.

        Args:
            campaign (Campaign): The campaign object for which to fetch the NPCs.

        Returns:
            list[CampaignNPC]: A list of all NPCs for the campaign.

        Raises:
            NoMatchingItemsError: If no NPCs are found for the campaign.
        """
        # Return the cache if it exists
        if campaign.id in self.npc_cache and self.npc_cache[campaign.id]:
            logger.debug(f"CACHE: Return npcs for campaign {campaign.id}")
            return self.npc_cache[campaign.id]

        try:
            npcs = [npc for npc in CampaignNPC.select().where(CampaignNPC.campaign == campaign.id)]
            logger.debug(f"DATABASE: Fetch all NPCs for campaign {campaign.name}")
        except DoesNotExist as e:
            raise errors.NoMatchingItemsError("No NPCs found") from e

        self.npc_cache[campaign.id] = npcs

        return self.npc_cache[campaign.id]

    def fetch_npc_by_name(
        self, ctx: discord.ApplicationContext, campaign: Campaign, name: str
    ) -> CampaignNPC:
        """Fetch an NPC by its name.

        # TODO: Refactor into an `option` and a `converter`

        This method first checks if the NPC with the given name is present in the cache.
        If not, it fetches the NPC from the database.

        Args:
            ctx (ApplicationContext): Context providing information about the guild from where to fetch the NPC.
            campaign (Campaign): The campaign object from where to fetch the NPC.
            name (str): The name of the NPC to fetch.

        Returns:
            CampaignNPC: The NPC corresponding to the given name.

        Raises:
            NoMatchingItemsError: If no NPC is found with the given name.
        """
        guild_id = ctx.guild.id

        try:
            npc = CampaignNPC.get(name=name, campaign=campaign.id)
            logger.debug(f"DATABASE: Fetch NPC for guild {guild_id}")
        except DoesNotExist as e:
            raise errors.NoMatchingItemsError(f"No NPC found with name {name}") from e

        return npc

    def set_active(self, ctx: discord.ApplicationContext, campaign: Campaign) -> None:
        """Set a campaign as active.

        This method deactivates all other campaigns and sets the specified one as active.  It first fetches all campaigns for the guild, either from the cache or the database.

        Args:
            ctx (ApplicationContext): Context providing information about the guild.
            campaign (Campaign): The campaign to set active
        """
        # Set any other campaign that is active to inactive
        campaigns = Campaign.select().where(Campaign.guild_id == ctx.guild.id)

        for c in campaigns:
            if c == campaign:
                c.is_active = True
                c.modified = time_now()
                c.save()
            elif c.is_active:
                c.is_active = False
                c.modified = time_now()
                c.save()

        self.purge_cache(ctx)
        logger.info(f"CAMPAIGN: Set {campaign.name} as active")

    def set_inactive(self, ctx: discord.ApplicationContext) -> None:
        """Set the active campaign to inactive.

        This method fetches the active campaign and sets its `is_active` status to `False`.
        It then updates the corresponding campaign in the cache and saves the changes to the database.

        Args:
            ctx (ApplicationContext): Context providing information about the guild.
        """
        # Fetch the active campaign
        campaign = self.fetch_active(ctx)

        # Set the campaign to inactive and save the changes
        campaign.is_active = False
        campaign.modified = time_now()
        campaign.save()

        # Update the cache
        guild_id = ctx.guild.id
        self.active_campaign_cache[guild_id] = None

        logger.debug(f"CAMPAIGN: Set {campaign.name} as inactive")

    def purge_cache(self, ctx: discord.ApplicationContext | None = None) -> None:
        """Purge the cache.

        This method purges the cache by either removing all entries associated with a specific guild or clearing all entries if no specific guild is provided. It uses the guild ID as the key for each cache dictionary.

        Args:
            ctx (ApplicationContext | None, optional): Context which provides information about the guild.
        """
        if ctx:
            logger.debug(f"CACHE: Purge campaign cache for guild {ctx.guild.id}")
            ids = Campaign.select(Campaign.id).where(Campaign.guild == ctx.guild.id)
            for i in ids:
                self.chapter_cache.pop(i.id, None)
                self.note_cache.pop(i.id, None)
                self.npc_cache.pop(i.id, None)
            self.campaign_cache.pop(ctx.guild.id, None)
            self.active_campaign_cache.pop(ctx.guild.id, None)
        else:
            caches: list[dict] = [
                self.campaign_cache,
                self.active_campaign_cache,
                self.chapter_cache,
                self.note_cache,
                self.npc_cache,
            ]
            for cache in caches:
                cache.clear()
            logger.info("CACHE: Purge campaign cache for all guilds")

    def update_chapter(
        self, ctx: discord.ApplicationContext, chapter: CampaignChapter, **kwargs: str
    ) -> None:
        """Update a chapter.

        This method updates the provided chapter with the values supplied through kwargs, then updates the modified timestamp, and removes the chapter's guild from the cache.

        Args:
            ctx (ApplicationContext): The application context carrying metadata for the command invocation.
            chapter (CampaignChapter): The chapter to be updated.
            **kwargs (str): Field-value pairs to update on the chapter.

        Raises:
            DatabaseError: If no chapter is found with the given ID.
        """
        try:
            CampaignChapter.update(modified=time_now(), **kwargs).where(
                CampaignChapter.id == chapter.id
            ).execute()

            self.purge_cache(ctx)

            logger.debug(f"CAMPAIGN: Update chapter {chapter.name} for guild {ctx.guild.id}")

        except DoesNotExist as e:
            raise errors.DatabaseError(f"No chapter found with ID {chapter.id}") from e

        except Exception as e:
            logger.error(
                f"CAMPAIGN: Unexpected error occurred while updating chapter {chapter.name} for guild {ctx.guild.id}"
            )
            raise e

    def update_campaign(
        self, ctx: discord.ApplicationContext, campaign: Campaign, **kwargs: str
    ) -> None:
        """Update a campaign.

        This method updates the provided campaign with the values supplied through kwargs, then updates the modified timestamp, and purges the cache.

        Args:
            ctx (ApplicationContext): The application context carrying metadata for the command invocation.
            campaign (Campaign): The campaign to be updated.
            **kwargs (str): Field-value pairs to update on the campaign.

        Raises:
            DatabaseError: If no campaign is found with the given ID.
        """
        try:
            Campaign.update(modified=time_now(), **kwargs).where(
                Campaign.id == campaign.id
            ).execute()

            self.purge_cache(ctx)

        except DoesNotExist as e:
            raise errors.DatabaseError(f"No campaign found with ID {campaign.id}") from e
        except Exception as e:
            logger.error(
                f"CAMPAIGN: Unexpected error occurred while updating campaign for guild {ctx.guild.id}"
            )
            raise e

    def update_note(
        self, ctx: discord.ApplicationContext, note: CampaignNote, **kwargs: str
    ) -> None:
        """Update a note.

        This method updates the provided note with the values supplied through kwargs, then updates the modified timestamp, and removes the note's guild from the cache.

        Args:
            ctx (ApplicationContext): The application context carrying metadata for the command invocation.
            note (CampaignNote): The note to be updated.
            **kwargs (str): Field-value pairs to update on the note.

        Raises:
            DatabaseError: If no note is found with the given ID.
        """
        try:
            CampaignNote.update(modified=time_now(), **kwargs).where(
                CampaignNote.id == note.id
            ).execute()

            self.purge_cache(ctx)

            logger.debug(f"CAMPAIGN: Update note {note.name} for guild {ctx.guild.id}")
        except DoesNotExist as e:
            raise errors.DatabaseError(f"No note found with ID {note.id}") from e
        except Exception as e:
            logger.error(
                f"CAMPAIGN: Unexpected error occurred while updating note for guild {ctx.guild.id}"
            )
            raise e

    def update_npc(self, ctx: discord.ApplicationContext, npc: CampaignNPC, **kwargs: str) -> None:
        """Update an NPC.

        This method updates the provided NPC with the values supplied through kwargs, then updates the modified timestamp, and removes the NPC's guild from the cache.

        Args:
            ctx (ApplicationContext): The application context carrying metadata for the command invocation.
            npc (CampaignNPC): The NPC to be updated.
            **kwargs (str): Field-value pairs to update on the NPC.

        Raises:
            DatabaseError: If no NPC is found with the given ID.
        """
        try:
            CampaignNPC.update(modified=time_now(), **kwargs).where(
                CampaignNPC.id == npc.id
            ).execute()

            self.purge_cache(ctx)

            logger.debug(f"CAMPAIGN: Update NPC {npc.name} for guild {ctx.guild.id}")
        except DoesNotExist as e:
            raise errors.DatabaseError(f"No NPC found with ID {npc.id}") from e
        except Exception as e:
            logger.error(
                f"CAMPAIGN: Unexpected error occurred while updating NPC for guild {ctx.guild.id}"
            )
            raise e
