# type: ignore
""""Test the Campaign model."""
import pytest
from rich.console import Console

from valentina.models import CampaignService
from valentina.models.db_tables import (
    Campaign,
    CampaignChapter,
    CampaignNote,
    CampaignNPC,
)
from valentina.utils import errors

console = Console()


@pytest.mark.usefixtures("mock_db")
class TestCampaignService:
    """Test the trait service."""

    campaign_svc = CampaignService()

    def test_create_campaign_one(self, caplog, mock_ctx):
        """Test creating a campaign.

        GIVEN a campaign service
        WHEN a campaign is created
        THEN the database is updated
        """
        # Set up the test
        current_count = Campaign.select().count()

        # Create the new campaign
        result = self.campaign_svc.create_campaign(mock_ctx, "new_campaign", "new campaign desc")
        captured = caplog.text

        # Verify the campaign was created
        assert "Purge campaign cache for guild 1" in captured
        assert result.name == "new_campaign"
        assert result.is_active is False
        assert Campaign.select().count() == current_count + 1

    def test_create_campaign_two(self, mock_ctx):
        """Test creating a campaign.

        GIVEN a campaign service
        WHEN a campaign is created with the same name as an existing campaign
        THEN raise a ValidationError
        """
        # Set up the test
        current_count = Campaign.select().count()

        # Create the new campaign
        with pytest.raises(errors.ValidationError, match=r"Campaign '\w+' already exists"):
            self.campaign_svc.create_campaign(mock_ctx, "new_campaign", "new campaign desc")

        assert Campaign.select().count() == current_count

    def test_create_chapter_one(self, mock_ctx):
        """Test creating a chapter.

        GIVEN a campaign service
        WHEN the first chapter is created
        THEN the database is updated and the chapter is created with the correct number
        """
        # set up the test
        campaign = Campaign.get_by_id(1)
        current_count = CampaignChapter.select().count()

        # Create the new chapter
        result = self.campaign_svc.create_chapter(
            mock_ctx, campaign, "new_chapter", "short desc", "new chapter desc"
        )

        # Verify the chapter was created
        assert result.name == "new_chapter"
        assert result.chapter_number == 1
        assert result.campaign == campaign
        assert CampaignChapter().select().count() == current_count + 1
        assert self.campaign_svc.chapter_cache == {}

    def test_create_chapter_two(self, mock_ctx):
        """Test creating a chapter.

        GIVEN a campaign service
        WHEN the second chapter is created
        THEN the database is updated and the chapter is created with the correct number
        """
        # set up the test
        campaign = Campaign.get_by_id(1)
        current_count = CampaignChapter.select().count()

        # Create the new chapter
        result = self.campaign_svc.create_chapter(
            mock_ctx, campaign, "chapter 2", "short desc", "new chapter desc"
        )

        # Verify the chapter was created
        assert result.name == "chapter 2"
        assert result.chapter_number == 2
        assert result.campaign == campaign
        assert CampaignChapter().select().count() == current_count + 1
        assert self.campaign_svc.chapter_cache == {}

    def test_create_npc(self, mock_ctx):
        """Test creating a npc.

        GIVEN a campaign service
        WHEN a npc is created
        THEN the database is updated
        """
        # Setup the test
        campaign = Campaign.get_by_id(1)
        current_count = CampaignNPC.select().count()

        # Create the new npc
        result = self.campaign_svc.create_npc(
            mock_ctx, campaign, "name 1", "npc class", "description 1"
        )

        # Validate the npc is created
        assert result.name == "name 1"
        assert result.campaign == campaign
        assert CampaignNPC.select().count() == current_count + 1

    def test_delete_chapter(self, mock_ctx):
        """Test delete_chapter().

        GIVEN a campaign service
        WHEN a chapter is deleted
        THEN remove it from the database
        """
        # set up the test
        campaign = campaign = Campaign.get_by_id(1)
        chapter1 = CampaignChapter.create(
            campaign=campaign.id,
            chapter_number=100,
            name="to_delete",
            short_description="short_description",
            description="description",
        )
        saved_id = chapter1.id
        current_count = CampaignChapter.select().count()

        # Delete the chapter
        self.campaign_svc.delete_chapter(mock_ctx, chapter1)

        # Confirm the chapter was deleted
        assert CampaignChapter.select().count() == current_count - 1
        assert not CampaignChapter.get_or_none(CampaignChapter.id == saved_id)

    def test_delete_campaign(self, mock_ctx, caplog):
        """Test delete_campaign().

        GIVEN a campaign service
        WHEN a campaign is deleted
        THEN the campaign and all associated data are deleted
        """
        # Set up the test
        campaign = Campaign.create(
            guild_id=mock_ctx.guild.id,
            name="name",
            description="description",
        )
        chapter1 = CampaignChapter.create(
            campaign=campaign.id,
            chapter_number=1,
            name="to_delete",
            short_description="short_description",
            description="description",
        )
        CampaignNPC.create(
            campaign=campaign.id,
            name="name",
            npc_class="npc_class",
            description="description",
        )
        CampaignNote.create(
            campaign=campaign.id,
            name="name",
            description="description",
            user=1,
            chapter=chapter1.id,
        )
        CampaignNote.create(
            campaign=campaign.id,
            name="name",
            description="description",
            user=1,
            chapter=None,
        )
        campaign_count = Campaign.select().count()
        chapter_count = CampaignChapter.select().count()
        note_count = CampaignNote.select().count()
        npc_count = CampaignNPC.select().count()

        # Delete the campaign
        self.campaign_svc.delete_campaign(mock_ctx, campaign)
        captured = caplog.text

        # Verify the campaign and all associated content was deleted
        assert "Purge campaign cache for guild 1" in captured
        assert Campaign.select().count() == campaign_count - 1
        assert CampaignChapter.select().count() == chapter_count - 1
        assert CampaignNote.select().count() == note_count - 2
        assert CampaignNPC.select().count() == npc_count - 1

    def test_delete_note(self, mock_ctx):
        """Test delete_note().

        GIVEN a campaign service
        WHEN a note is deleted
        THEN remove it from the database
        """
        # set up the test
        campaign = campaign = Campaign.get_by_id(1)
        note = CampaignNote.create(
            campaign=campaign.id, name="name", description="description", user=1, chapter=None
        )
        saved_id = note.id
        current_count = CampaignNote.select().count()

        # Delete the chapter
        self.campaign_svc.delete_note(mock_ctx, note)

        # Confirm the chapter was deleted
        assert CampaignNote.select().count() == current_count - 1
        assert not CampaignNote.get_or_none(CampaignNote.id == saved_id)

    def test_delete_npc(self, mock_ctx):
        """Test delete_npc().

        GIVEN a campaign service
        WHEN a npc is deleted
        THEN remove it from the database
        """
        # set up the test
        campaign = campaign = Campaign.get_by_id(1)
        npc = CampaignNPC.create(
            campaign=campaign.id,
            name="name",
            npc_class="npc_class",
            description="description",
        )
        saved_id = npc.id
        current_count = CampaignNPC.select().count()

        # Delete the chapter
        self.campaign_svc.delete_npc(mock_ctx, npc)

        # Confirm the chapter was deleted
        assert CampaignNPC.select().count() == current_count - 1
        assert not CampaignNPC.get_or_none(CampaignNPC.id == saved_id)

    def test_fetch_active_one(self, mock_ctx):
        """Test fetch_active().

        GIVEN a campaign service
        WHEN the active campaign is fetched
        THEN raise NoActiveCampaignError if not active campaign is found
        """
        with pytest.raises(errors.NoActiveCampaignError, match="No active campaign found"):
            self.campaign_svc.fetch_active(mock_ctx)

    def test_fetch_active_two(self, mock_ctx, caplog):
        """Test fetch_active().

        GIVEN a campaign service
        WHEN the active campaign is fetched
        THEN return the active campaign
        """
        # Set up the test
        campaign2 = Campaign.create(
            guild_id=mock_ctx.guild.id, name="name", description="description", is_active=True
        )

        assert self.campaign_svc.active_campaign_cache == {}

        # Pull the active campaign from the database
        result = self.campaign_svc.fetch_active(mock_ctx)
        captured = caplog.text

        # Confirm the active campaign was pulled from the db
        assert "DATABASE: Fetch active campaign for guild 1" in captured
        assert "CACHE: Return active campaign for guild 1" not in captured
        assert result == campaign2
        assert self.campaign_svc.active_campaign_cache == {1: campaign2}

        # pull it again to grab from the cache
        # Pull the active campaign from the database
        result = self.campaign_svc.fetch_active(mock_ctx)
        captured2 = caplog.text

        # Confirm the active campaign was pulled from the db
        assert "CACHE: Return active campaign for guild 1" in captured2
        assert result == campaign2

    def test_fetch_all(self, mock_ctx2, caplog):
        """Test fetch_all().

        GIVEN a campaign service
        WHEN fetch_all() is called
        THEN return a list of all campaigns for the guild
        """
        # Setup the test
        campaign2 = Campaign.create(
            guild_id=mock_ctx2.guild.id, name="fetchAll1", description="description", is_active=True
        )
        campaign3 = Campaign.create(
            guild_id=mock_ctx2.guild.id, name="fetchAll2", description="description", is_active=True
        )
        self.campaign_svc.purge_cache()

        # Fetch from the database
        returned = self.campaign_svc.fetch_all(mock_ctx2)
        captured = caplog.text

        # Confirm the results
        assert "DATABASE: Fetch all campaigns for guild 2" in captured
        assert "CACHE: Return all campaigns for guild 2" not in captured
        assert len(returned) == 2
        assert self.campaign_svc.campaign_cache[2] == [campaign2, campaign3]

        # Fetch from the cache
        # Fetch from the database
        returned = self.campaign_svc.fetch_all(mock_ctx2)
        captured2 = caplog.text

        # Confirm the results
        assert "CACHE: Return all campaigns for guild 2" in captured2
        assert len(returned) == 2
        assert self.campaign_svc.campaign_cache[2] == [
            campaign2,
            campaign3,
        ]

    def test_fetch_chapter_by_id_one(self, caplog):
        """Test fetch_chapter_by_id().

        GIVEN a campaign service
        WHEN fetch_chapter_by_id is called
        THEN return the chapter object
        """
        # set up the test
        campaign = Campaign.get_by_id(1)
        chapter = CampaignChapter.create(
            campaign=campaign.id,
            chapter_number=12345,
            name="fetch_chapter_by_id",
            short_description="short_description",
            description="description",
        )
        self.campaign_svc.purge_cache()

        # fetch the chapter
        result = self.campaign_svc.fetch_chapter_by_id(chapter.id)
        captured = caplog.text

        # Confirm the chapter was returned from the database
        assert f"DATABASE: fetch chapter {chapter.id}" in captured
        assert result == chapter

    def test_fetch_chapter_by_id_two(self):
        """Test fetch_chapter_by_id().

        GIVEN a campaign service
        WHEN fetch_chapter_by_id is called
        THEN raise DatabaseError when chapter not found
        """
        with pytest.raises(errors.DatabaseError, match="No chapter found with ID 2298765432118"):
            self.campaign_svc.fetch_chapter_by_id(2298765432118)

    def test_fetch_chapter_by_name_one(self, caplog):
        """Test fetch_chapter_by_name().

        GIVEN a campaign service
        WHEN fetch_chapter_by_name is called
        THEN return the chapter object
        """
        # set up the test
        campaign = Campaign.get_by_id(1)
        chapter = CampaignChapter.create(
            campaign=campaign.id,
            chapter_number=1234554321,
            name="fetch_chapter_by_name",
            short_description="short_description",
            description="description",
        )
        self.campaign_svc.purge_cache()

        # fetch the chapter
        result = self.campaign_svc.fetch_chapter_by_name(campaign, chapter.name)
        captured = caplog.text

        # Confirm the chapter was returned from the database
        assert f"DATABASE: fetch chapter {chapter.name}" in captured
        assert result == chapter

    def test_fetch_chapter_by_name_two(self):
        """Test fetch_chapter_by_name().

        GIVEN a campaign service
        WHEN fetch_chapter_by_name is called
        THEN raise DatabaseError when chapter not found
        """
        # set up the test
        campaign = Campaign.get_by_id(1)

        # Fetch the chapter
        with pytest.raises(errors.DatabaseError, match="No chapter found"):
            self.campaign_svc.fetch_chapter_by_name(campaign, "quick brown fox")

    def test_fetch_campaign_by_name(self, mock_ctx, caplog):
        """Test fetch_campaign_by_name().

        GIVEN a campaign service
        WHEN fetch_campaign_by_name is called
        THEN return the campaign
        """

    def test_fetch_all_notes_one(self, mock_ctx, caplog):
        """Test fetch_all_notes().

        GIVEN a campaign service
        WHEN fetch_all_notes is called
        THEN return all the notes
        """
        # set up the test
        campaign = Campaign.create(
            guild_id=mock_ctx.guild.id,
            name="fetch_all_notes",
            description="description",
            is_active=True,
        )
        note1 = CampaignNote.create(
            campaign=campaign.id, name="name", description="description", user=1, chapter=None
        )
        note2 = CampaignNote.create(
            campaign=campaign.id,
            name="name",
            description="description",
            user=1,
            chapter=None,
        )
        self.campaign_svc.purge_cache()

        # Fetch all notes from the database
        result = self.campaign_svc.fetch_all_notes(campaign)
        captured = caplog.text

        # Confirm it worked
        assert len(result) == 2
        assert "DATABASE: Fetch all notes for campaign" in captured
        assert len(self.campaign_svc.note_cache[campaign.id]) == 2
        assert note1 in self.campaign_svc.note_cache[campaign.id]
        assert note2 in self.campaign_svc.note_cache[campaign.id]

        # Fetch all notes from the cache
        result = self.campaign_svc.fetch_all_notes(campaign)
        captured2 = caplog.text

        # Confirm it worked
        assert len(result) == 2
        assert "CACHE: Return notes for campaign " in captured2
        assert len(self.campaign_svc.note_cache[campaign.id]) == 2
        assert note1 in self.campaign_svc.note_cache[campaign.id]
        assert note2 in self.campaign_svc.note_cache[campaign.id]

    def test_fetch_all_notes_two(self, mock_ctx):
        """Test fetch_all_notes().

        GIVEN a campaign service
        WHEN fetch_all_notes is called
        THEN return an empty list when no notes found
        """
        campaign = Campaign.create(
            guild_id=mock_ctx.guild.id,
            name="fetch_all_notes2",
            description="description",
            is_active=True,
        )

        # fetch the notes
        returned = self.campaign_svc.fetch_all_notes(campaign)

        # Confirm it worked
        assert returned == []

    def test_fetch_all_chapters_one(self, mock_ctx, caplog):
        """Test fetch_all_chapters()."""
        # GIVEN a campaign with two chapters
        campaign = Campaign.create(
            guild_id=mock_ctx.guild.id,
            name="fetch_all_chapters",
            description="description",
            is_active=True,
        )
        chapter1 = CampaignChapter.create(
            campaign=campaign.id,
            chapter_number=1,
            name="fetch_all_chapters1",
            short_description="short_description",
            description="description",
        )
        chapter2 = CampaignChapter.create(
            campaign=campaign.id,
            chapter_number=1,
            name="fetch_all_chapters2",
            short_description="short_description",
            description="description",
        )
        self.campaign_svc.purge_cache()

        # WHEN fetch_all_chapters is called
        result = self.campaign_svc.fetch_all_chapters(campaign)
        captured = caplog.text

        # THEN the cache is populated and the chapters returned from the database
        assert "DATABASE: Fetch all chapters for campaign " in captured
        assert result == [chapter1, chapter2]

        # WHEN fetch_all_chapters is called again
        result = self.campaign_svc.fetch_all_chapters(campaign)
        captured2 = caplog.text

        # THEN the cache is populated and the chapters returned from the cache
        assert "CACHE: Return all chapters for campaign" in captured2
        assert result == [chapter1, chapter2]

    def test_fetch_note_by_id(self, mock_ctx):
        """Test fetch_note_by_id().

        GIVEN a campaign service
        WHEN fetch_note_by_id is called
        THEN return the requested note
        """
        # Setup the test
        campaign = Campaign.create(
            guild_id=mock_ctx.guild.id,
            name="fetch_note_by_id",
            description="description",
            is_active=True,
        )
        note1 = CampaignNote.create(
            campaign=campaign.id,
            name="name_to_test_fetching",
            description="description",
            user=1,
            chapter=None,
        )
        id_to_test = note1.id

        # WHEN checking for an existing note
        result = self.campaign_svc.fetch_note_by_id(id_to_test)

        # THEN return the requested note
        assert result == note1

        # WHEN checking for a note that doesn't exist
        # THEN raise a DatabaseError
        with pytest.raises(errors.DatabaseError, match="No note found with ID"):
            self.campaign_svc.fetch_note_by_id(98765438820012)

    def test_fetch_all_npcs(self, mock_ctx, caplog):
        """Test fetch_note_by_id()."""
        # GIVEN a campaign and associated NPCs
        campaign = Campaign.create(
            guild_id=mock_ctx.guild.id,
            name="fetch_all_npcs",
            description="description",
            is_active=True,
        )
        npc1 = CampaignNPC.create(
            campaign=campaign.id,
            name="name1",
            npc_class="npc_class",
            description="description",
        )
        npc2 = CampaignNPC.create(
            campaign=campaign.id,
            name="name2",
            npc_class="npc_class",
            description="description",
        )

        # WHEN getching all NPCs without a cache
        result = self.campaign_svc.fetch_all_npcs(campaign)
        captured = caplog.text

        ## THEN confirm all NPCs are returned from the database
        assert result == [npc1, npc2]
        assert "DATABASE: Fetch all NPCs for campaign" in captured

        # WHEN getching all NPCs from the cache
        result = self.campaign_svc.fetch_all_npcs(campaign)
        captured2 = caplog.text

        ## THEN confirm all NPCs are returned from the cache
        assert result == [npc1, npc2]
        assert "CACHE: Return npcs for campaign" in captured2

    def test_set_active(self, mock_ctx):
        """Test set_active()."""
        # GIVEN two campaigns, one that is active and one that is not
        campaign1 = Campaign.create(
            guild_id=mock_ctx.guild.id,
            name="test_set_active1",
            description="description",
            is_active=True,
        )
        campaign2 = Campaign.create(
            guild_id=mock_ctx.guild.id,
            name="test_set_active2",
            description="description",
            is_active=False,
        )

        # WHEN set_active is called
        self.campaign_svc.set_active(mock_ctx, campaign2)

        # THEN update the database and the cache
        assert Campaign.get_by_id(campaign2.id).is_active
        assert not Campaign.get_by_id(campaign1.id).is_active

    def test_set_inactive_one(self, mock_ctx):
        """Test set_inactive()."""
        # GIVEN a single active campaign
        self.campaign_svc.purge_cache()
        for c in Campaign.select().where(Campaign.is_active == True):  # noqa: E712
            c.is_active = False
            c.save()

        campaign = Campaign.create(
            guild_id=mock_ctx.guild.id,
            name="set_inactive",
            description="description",
            is_active=True,
        )

        # WHEN set_inactive is called
        self.campaign_svc.set_inactive(mock_ctx)

        # THEN the database and cache are updated
        assert not self.campaign_svc.active_campaign_cache[mock_ctx.guild.id]
        assert not Campaign.get_by_id(campaign.id).is_active

    def test_purge_cache_one(self, mock_ctx, mock_ctx2):
        """Test purge_cache() with a ctx."""
        # GIVEN a campaign service with a populated cache
        campaign = Campaign.create(
            guild_id=mock_ctx.guild.id,
            name="test_purge_cache_one",
            description="description",
        )
        Campaign.create(
            guild_id=mock_ctx.guild.id,
            name="test_purge_cache_one2",
            description="description",
        )
        chapter1 = CampaignChapter.create(
            campaign=campaign.id,
            chapter_number=1,
            name="to_delete",
            short_description="short_description",
            description="description",
        )
        CampaignNPC.create(
            campaign=campaign.id,
            name="name",
            npc_class="npc_class",
            description="description",
        )
        CampaignNote.create(
            campaign=campaign.id,
            name="name",
            description="description",
            user=1,
            chapter=chapter1.id,
        )
        CampaignNote.create(
            campaign=campaign.id,
            name="name",
            description="description",
            user=1,
            chapter=None,
        )

        self.campaign_svc.set_active(mock_ctx, campaign)
        self.campaign_svc.fetch_all(mock_ctx)
        self.campaign_svc.fetch_all(mock_ctx2)
        self.campaign_svc.fetch_all_chapters(campaign)
        self.campaign_svc.fetch_all_notes(campaign)
        self.campaign_svc.fetch_all_npcs(campaign)

        assert mock_ctx.guild.id in self.campaign_svc.campaign_cache
        assert mock_ctx2.guild.id in self.campaign_svc.campaign_cache
        assert campaign.id in self.campaign_svc.chapter_cache
        assert campaign.id in self.campaign_svc.note_cache
        assert campaign.id in self.campaign_svc.npc_cache

        # WHEN purge_cache is called with a ctx
        self.campaign_svc.purge_cache(mock_ctx)

        # THEN the cache is purged for the guild
        assert mock_ctx.guild.id not in self.campaign_svc.campaign_cache
        assert mock_ctx2.guild.id in self.campaign_svc.campaign_cache
        assert campaign.id not in self.campaign_svc.chapter_cache
        assert campaign.id not in self.campaign_svc.note_cache
        assert campaign.id not in self.campaign_svc.npc_cache

    def test_purge_cache_two(self, mock_ctx, mock_ctx2):
        """Test purge_cache() with a ctx."""
        # GIVEN a campaign service with a populated cache
        campaign = Campaign.get_by_id(1)
        self.campaign_svc.fetch_all(mock_ctx)
        self.campaign_svc.fetch_all(mock_ctx2)
        self.campaign_svc.set_active(mock_ctx, campaign)
        self.campaign_svc.fetch_all_chapters(campaign)
        self.campaign_svc.fetch_all_notes(campaign)
        self.campaign_svc.fetch_all_npcs(campaign)

        # WHEN purge_cache is called with a ctx
        self.campaign_svc.purge_cache()

        # THEN the cache is purged for the guild
        assert self.campaign_svc.campaign_cache == {}
        assert self.campaign_svc.chapter_cache == {}
        assert self.campaign_svc.note_cache == {}
        assert self.campaign_svc.npc_cache == {}
        assert self.campaign_svc.active_campaign_cache == {}

    def test_update_chapter(self, mock_ctx):
        """Test update_chapter()."""
        # GIVEN a chapter
        campaign = Campaign.get_by_id(1)
        chapter1 = CampaignChapter.create(
            campaign=campaign.id,
            chapter_number=1,
            name="update_chapter",
            short_description="short_description",
            description="description",
        )
        self.campaign_svc.fetch_all_chapters(campaign)

        # WHEN update_chapter is called
        updates = {
            "name": "new name",
            "short_description": "new short desc",
            "description": "new desc",
        }
        self.campaign_svc.update_chapter(mock_ctx, chapter1, **updates)

        # THEN the chapter is updated in the database and cache
        updated_chapter = CampaignChapter.get_by_id(chapter1.id)
        assert updated_chapter.name == "new name"
        assert updated_chapter.short_description == "new short desc"
        assert updated_chapter.description == "new desc"
        assert campaign.id not in self.campaign_svc.chapter_cache

    def test_update_campaign(self, mock_ctx):
        """Test update_campaign()."""
        # GIVEN a campaign and a cache
        campaign = Campaign.get_by_id(1)
        self.campaign_svc.fetch_all(mock_ctx)

        # WHEN update_campaign is called
        updates = {"name": "new name", "description": "new desc"}
        self.campaign_svc.update_campaign(mock_ctx, campaign, **updates)

        # THEN the campaign is updated in the database and the cache is purged
        updated_campaign = Campaign.get_by_id(1)
        assert updated_campaign.name == "new name"
        assert updated_campaign.description == "new desc"
        assert mock_ctx.guild.id not in self.campaign_svc.campaign_cache

    def test_update_note(self, mock_ctx):
        """Test update_note()."""
        # GIVEN a note and a cache
        campaign = Campaign.get_by_id(1)
        note1 = CampaignNote.create(
            campaign=campaign.id, name="name", description="description", user=1, chapter=None
        )
        self.campaign_svc.fetch_all_notes(campaign)

        # WHEN update_note is called
        updates = {"name": "new name", "description": "new desc"}
        self.campaign_svc.update_note(mock_ctx, note1, **updates)

        # THEN the note is updated in the database and the cache is purged
        updated_note = CampaignNote.get_by_id(note1.id)
        assert updated_note.name == "new name"
        assert updated_note.description == "new desc"
        assert campaign.id not in self.campaign_svc.note_cache

    def test_update_npc(self, mock_ctx):
        """Test update_npc()."""
        # GIVEN a npc and a cache
        campaign = Campaign.get_by_id(1)
        npc1 = CampaignNPC.create(
            campaign=campaign.id,
            name="name",
            npc_class="npc_class",
            description="description",
        )
        self.campaign_svc.fetch_all_npcs(campaign)

        # WHEN update_npc is called
        updates = {"name": "new name", "npc_class": "new class", "description": "new desc"}
        self.campaign_svc.update_npc(mock_ctx, npc1, **updates)

        # THEN the npc is updated in the database and the cache is purged
        updated_npc = CampaignNPC.get_by_id(npc1.id)
        assert updated_npc.name == "new name"
        assert updated_npc.npc_class == "new class"
        assert updated_npc.description == "new desc"
        assert campaign.id not in self.campaign_svc.npc_cache
