# type: ignore
""""Test the Chronicle model."""
import pytest
from rich.console import Console

from valentina.models import ChronicleService
from valentina.models.db_tables import (
    Chronicle,
    ChronicleChapter,
    ChronicleNote,
    ChronicleNPC,
)
from valentina.utils.errors import NoActiveChronicleError

console = Console()


@pytest.mark.usefixtures("mock_db")
class TestChronicleService:
    """Test the trait service."""

    chron_svc = ChronicleService()

    def test_create_chronicle_one(self, caplog, mock_ctx):
        """Test creating a chronicle.

        GIVEN a chronicle service
        WHEN a chronicle is created
        THEN the database is updated
        """
        # Set up the test
        current_count = Chronicle.select().count()

        # Create the new chronicle
        result = self.chron_svc.create_chronicle(mock_ctx, "new_chronicle", "new chronicle desc")
        captured = caplog.text

        # Verify the chronicle was created
        assert "Purge cache for guild 1" in captured
        assert result.name == "new_chronicle"
        assert result.is_active is False
        assert Chronicle.select().count() == current_count + 1

    def test_create_chronicle_two(self, mock_ctx):
        """Test creating a chronicle.

        GIVEN a chronicle service
        WHEN a chronicle is created with the same name as an existing chronicle
        THEN raise a ValueError
        """
        # Set up the test
        current_count = Chronicle.select().count()

        # Create the new chronicle
        with pytest.raises(ValueError, match=r"Chronicle '\w+' already exists"):
            self.chron_svc.create_chronicle(mock_ctx, "new_chronicle", "new chronicle desc")

        assert Chronicle.select().count() == current_count

    def test_create_chapter_one(self, mock_ctx):
        """Test creating a chapter.

        GIVEN a chronicle service
        WHEN the first chapter is created
        THEN the database is updated and the chapter is created with the correct number
        """
        # set up the test
        chronicle = Chronicle.get_by_id(1)
        current_count = ChronicleChapter.select().count()

        # Create the new chapter
        result = self.chron_svc.create_chapter(
            mock_ctx, chronicle, "new_chapter", "short desc", "new chapter desc"
        )

        # Verify the chapter was created
        assert result.name == "new_chapter"
        assert result.chapter == 1
        assert result.chronicle == chronicle
        assert ChronicleChapter().select().count() == current_count + 1
        assert self.chron_svc.chapter_cache == {}

    def test_create_chapter_two(self, mock_ctx):
        """Test creating a chapter.

        GIVEN a chronicle service
        WHEN the second chapter is created
        THEN the database is updated and the chapter is created with the correct number
        """
        # set up the test
        chronicle = Chronicle.get_by_id(1)
        current_count = ChronicleChapter.select().count()

        # Create the new chapter
        result = self.chron_svc.create_chapter(
            mock_ctx, chronicle, "chapter 2", "short desc", "new chapter desc"
        )

        # Verify the chapter was created
        assert result.name == "chapter 2"
        assert result.chapter == 2
        assert result.chronicle == chronicle
        assert ChronicleChapter().select().count() == current_count + 1
        assert self.chron_svc.chapter_cache == {}

    def test_create_npc(self, mock_ctx):
        """Test creating a npc.

        GIVEN a chronicle service
        WHEN a npc is created
        THEN the database is updated
        """
        # Setup the test
        chronicle = Chronicle.get_by_id(1)
        current_count = ChronicleNPC.select().count()

        # Create the new npc
        result = self.chron_svc.create_npc(
            mock_ctx, chronicle, "name 1", "npc class", "description 1"
        )

        # Validate the npc is created
        assert result.name == "name 1"
        assert result.chronicle == chronicle
        assert ChronicleNPC.select().count() == current_count + 1

    def test_delete_chapter(self, mock_ctx):
        """Test delete_chapter().

        GIVEN a chronicle service
        WHEN a chapter is deleted
        THEN remove it from the database
        """
        # set up the test
        chronicle = chronicle = Chronicle.get_by_id(1)
        chapter1 = ChronicleChapter.create(
            chronicle=chronicle.id,
            chapter=100,
            name="to_delete",
            short_description="short_description",
            description="description",
        )
        saved_id = chapter1.id
        current_count = ChronicleChapter.select().count()

        # Delete the chapter
        self.chron_svc.delete_chapter(mock_ctx, chapter1)

        # Confirm the chapter was deleted
        assert ChronicleChapter.select().count() == current_count - 1
        assert not ChronicleChapter.get_or_none(ChronicleChapter.id == saved_id)

    def test_delete_chronicle(self, mock_ctx, caplog):
        """Test delete_chronicle().

        GIVEN a chronicle service
        WHEN a chronicle is deleted
        THEN the chronicle and all associated data are deleted
        """
        # Set up the test
        chronicle = Chronicle.create(
            guild_id=mock_ctx.guild.id,
            name="name",
            description="description",
        )
        chapter1 = ChronicleChapter.create(
            chronicle=chronicle.id,
            chapter=1,
            name="to_delete",
            short_description="short_description",
            description="description",
        )
        ChronicleNPC.create(
            chronicle=chronicle.id,
            name="name",
            npc_class="npc_class",
            description="description",
        )
        ChronicleNote.create(
            chronicle=chronicle.id,
            name="name",
            description="description",
            user=1,
            chapter=chapter1.id,
        )
        ChronicleNote.create(
            chronicle=chronicle.id,
            name="name",
            description="description",
            user=1,
            chapter=None,
        )
        chronicle_count = Chronicle.select().count()
        chapter_count = ChronicleChapter.select().count()
        note_count = ChronicleNote.select().count()
        npc_count = ChronicleNPC.select().count()

        # Delete the chronicle
        self.chron_svc.delete_chronicle(mock_ctx, chronicle)
        captured = caplog.text

        # Verify the chronicle and all associated content was deleted
        assert "Purge cache for guild 1" in captured
        assert Chronicle.select().count() == chronicle_count - 1
        assert ChronicleChapter.select().count() == chapter_count - 1
        assert ChronicleNote.select().count() == note_count - 2
        assert ChronicleNPC.select().count() == npc_count - 1

    def test_delete_note(self, mock_ctx):
        """Test delete_note().

        GIVEN a chronicle service
        WHEN a note is deleted
        THEN remove it from the database
        """
        # set up the test
        chronicle = chronicle = Chronicle.get_by_id(1)
        note = ChronicleNote.create(
            chronicle=chronicle.id, name="name", description="description", user=1, chapter=None
        )
        saved_id = note.id
        current_count = ChronicleNote.select().count()

        # Delete the chapter
        self.chron_svc.delete_note(mock_ctx, note)

        # Confirm the chapter was deleted
        assert ChronicleNote.select().count() == current_count - 1
        assert not ChronicleNote.get_or_none(ChronicleNote.id == saved_id)

    def test_delete_npc(self, mock_ctx):
        """Test delete_npc().

        GIVEN a chronicle service
        WHEN a npc is deleted
        THEN remove it from the database
        """
        # set up the test
        chronicle = chronicle = Chronicle.get_by_id(1)
        npc = ChronicleNPC.create(
            chronicle=chronicle.id,
            name="name",
            npc_class="npc_class",
            description="description",
        )
        saved_id = npc.id
        current_count = ChronicleNPC.select().count()

        # Delete the chapter
        self.chron_svc.delete_npc(mock_ctx, npc)

        # Confirm the chapter was deleted
        assert ChronicleNPC.select().count() == current_count - 1
        assert not ChronicleNPC.get_or_none(ChronicleNPC.id == saved_id)

    def test_fetch_active_one(self, mock_ctx):
        """Test fetch_active().

        GIVEN a chronicle service
        WHEN the active chronicle is fetched
        THEN raise NoActiveChronicleError if not active chronicle is found
        """
        with pytest.raises(NoActiveChronicleError, match="No active chronicle found"):
            self.chron_svc.fetch_active(mock_ctx)

    def test_fetch_active_two(self, mock_ctx, caplog):
        """Test fetch_active().

        GIVEN a chronicle service
        WHEN the active chronicle is fetched
        THEN return the active chronicle
        """
        # Set up the test
        chronicle2 = Chronicle.create(
            guild_id=mock_ctx.guild.id, name="name", description="description", is_active=True
        )

        assert self.chron_svc.active_chronicle_cache == {}

        # Pull the active chronicle from the database
        result = self.chron_svc.fetch_active(mock_ctx)
        captured = caplog.text

        # Confirm the active chronicle was pulled from the db
        assert "DATABASE: Fetch active chronicle for guild 1" in captured
        assert "CACHE: Return active chronicle for guild 1" not in captured
        assert result == chronicle2
        assert self.chron_svc.active_chronicle_cache == {1: chronicle2}

        # pull it again to grab from the cache
        # Pull the active chronicle from the database
        result = self.chron_svc.fetch_active(mock_ctx)
        captured2 = caplog.text

        # Confirm the active chronicle was pulled from the db
        assert "CACHE: Return active chronicle for guild 1" in captured2
        assert result == chronicle2

    def test_fetch_all(self, mock_ctx2, caplog):
        """Test fetch_all().

        GIVEN a chronicle service
        WHEN fetch_all() is called
        THEN return a list of all chronicles for the guild
        """
        # Setup the test
        chronicle2 = Chronicle.create(
            guild_id=mock_ctx2.guild.id, name="fetchAll1", description="description", is_active=True
        )
        chronicle3 = Chronicle.create(
            guild_id=mock_ctx2.guild.id, name="fetchAll2", description="description", is_active=True
        )
        self.chron_svc.purge_cache()

        # Fetch from the database
        returned = self.chron_svc.fetch_all(mock_ctx2)
        captured = caplog.text

        # Confirm the results
        assert "DATABASE: Fetch all chronicles for guild 2" in captured
        assert "CACHE: Return all chronicles for guild 2" not in captured
        assert len(returned) == 2
        assert self.chron_svc.chronicle_cache[2] == [chronicle2, chronicle3]

        # Fetch from the cache
        # Fetch from the database
        returned = self.chron_svc.fetch_all(mock_ctx2)
        captured2 = caplog.text

        # Confirm the results
        assert "CACHE: Return all chronicles for guild 2" in captured2
        assert len(returned) == 2
        assert self.chron_svc.chronicle_cache[2] == [
            chronicle2,
            chronicle3,
        ]

    def test_fetch_chapter_by_id_one(self, caplog):
        """Test fetch_chapter_by_id().

        GIVEN a chronicle service
        WHEN fetch_chapter_by_id is called
        THEN return the chapter object
        """
        # set up the test
        chronicle = Chronicle.get_by_id(1)
        chapter = ChronicleChapter.create(
            chronicle=chronicle.id,
            chapter=12345,
            name="fetch_chapter_by_id",
            short_description="short_description",
            description="description",
        )
        self.chron_svc.purge_cache()

        # fetch the chapter
        result = self.chron_svc.fetch_chapter_by_id(chapter.id)
        captured = caplog.text

        # Confirm the chapter was returned from the database
        assert f"DATABASE: fetch chapter {chapter.id}" in captured
        assert result == chapter

    def test_fetch_chapter_by_id_two(self):
        """Test fetch_chapter_by_id().

        GIVEN a chronicle service
        WHEN fetch_chapter_by_id is called
        THEN raise ValueError when chapter not found
        """
        with pytest.raises(ValueError, match="No chapter found"):
            self.chron_svc.fetch_chapter_by_id(2298765432118)

    def test_fetch_chapter_by_name_one(self, caplog):
        """Test fetch_chapter_by_name().

        GIVEN a chronicle service
        WHEN fetch_chapter_by_name is called
        THEN return the chapter object
        """
        # set up the test
        chronicle = Chronicle.get_by_id(1)
        chapter = ChronicleChapter.create(
            chronicle=chronicle.id,
            chapter=1234554321,
            name="fetch_chapter_by_name",
            short_description="short_description",
            description="description",
        )
        self.chron_svc.purge_cache()

        # fetch the chapter
        result = self.chron_svc.fetch_chapter_by_name(chronicle, chapter.name)
        captured = caplog.text

        # Confirm the chapter was returned from the database
        assert f"DATABASE: fetch chapter {chapter.name}" in captured
        assert result == chapter

    def test_fetch_chapter_by_name_two(self):
        """Test fetch_chapter_by_name().

        GIVEN a chronicle service
        WHEN fetch_chapter_by_name is called
        THEN raise ValueError when chapter not found
        """
        # set up the test
        chronicle = Chronicle.get_by_id(1)

        # Fetch the chapter
        with pytest.raises(ValueError, match="No chapter found"):
            self.chron_svc.fetch_chapter_by_name(chronicle, "quick brown fox")

    def test_fetch_chronicle_by_name(self, mock_ctx, caplog):
        """Test fetch_chronicle_by_name().

        GIVEN a chronicle service
        WHEN fetch_chronicle_by_name is called
        THEN return the chronicle
        """

    def test_fetch_all_notes_one(self, mock_ctx, caplog):
        """Test fetch_all_notes().

        GIVEN a chronicle service
        WHEN fetch_all_notes is called
        THEN return all the notes
        """
        # set up the test
        chronicle = Chronicle.create(
            guild_id=mock_ctx.guild.id,
            name="fetch_all_notes",
            description="description",
            is_active=True,
        )
        note1 = ChronicleNote.create(
            chronicle=chronicle.id, name="name", description="description", user=1, chapter=None
        )
        note2 = ChronicleNote.create(
            chronicle=chronicle.id,
            name="name",
            description="description",
            user=1,
            chapter=None,
        )
        self.chron_svc.purge_cache()

        # Fetch all notes from the database
        result = self.chron_svc.fetch_all_notes(chronicle)
        captured = caplog.text

        # Confirm it worked
        assert len(result) == 2
        assert "DATABASE: Fetch all notes for chronicle" in captured
        assert len(self.chron_svc.note_cache[chronicle.id]) == 2
        assert note1 in self.chron_svc.note_cache[chronicle.id]
        assert note2 in self.chron_svc.note_cache[chronicle.id]

        # Fetch all notes from the cache
        result = self.chron_svc.fetch_all_notes(chronicle)
        captured2 = caplog.text

        # Confirm it worked
        assert len(result) == 2
        assert "CACHE: Return notes for chronicle " in captured2
        assert len(self.chron_svc.note_cache[chronicle.id]) == 2
        assert note1 in self.chron_svc.note_cache[chronicle.id]
        assert note2 in self.chron_svc.note_cache[chronicle.id]

    def test_fetch_all_notes_two(self, mock_ctx):
        """Test fetch_all_notes().

        GIVEN a chronicle service
        WHEN fetch_all_notes is called
        THEN return an empty list when no notes found
        """
        chronicle = Chronicle.create(
            guild_id=mock_ctx.guild.id,
            name="fetch_all_notes2",
            description="description",
            is_active=True,
        )

        # fetch the notes
        returned = self.chron_svc.fetch_all_notes(chronicle)

        # Confirm it worked
        assert returned == []

    def test_fetch_all_chapters_one(self, mock_ctx, caplog):
        """Test fetch_all_chapters()."""
        # GIVEN a chronicle with two chapters
        chronicle = Chronicle.create(
            guild_id=mock_ctx.guild.id,
            name="fetch_all_chapters",
            description="description",
            is_active=True,
        )
        chapter1 = ChronicleChapter.create(
            chronicle=chronicle.id,
            chapter=1,
            name="fetch_all_chapters1",
            short_description="short_description",
            description="description",
        )
        chapter2 = ChronicleChapter.create(
            chronicle=chronicle.id,
            chapter=1,
            name="fetch_all_chapters2",
            short_description="short_description",
            description="description",
        )
        self.chron_svc.purge_cache()

        # WHEN fetch_all_chapters is called
        result = self.chron_svc.fetch_all_chapters(chronicle)
        captured = caplog.text

        # THEN the cache is populated and the chapters returned from the database
        assert "DATABASE: Fetch all chapters for chronicle " in captured
        assert result == [chapter1, chapter2]

        # WHEN fetch_all_chapters is called again
        result = self.chron_svc.fetch_all_chapters(chronicle)
        captured2 = caplog.text

        # THEN the cache is populated and the chapters returned from the cache
        assert "CACHE: Return all chapters for chronicle" in captured2
        assert result == [chapter1, chapter2]

    def test_fetch_note_by_id(self, mock_ctx):
        """Test fetch_note_by_id().

        GIVEN a chronicle service
        WHEN fetch_note_by_id is called
        THEN return the requested note
        """
        # Setup the test
        chronicle = Chronicle.create(
            guild_id=mock_ctx.guild.id,
            name="fetch_note_by_id",
            description="description",
            is_active=True,
        )
        note1 = ChronicleNote.create(
            chronicle=chronicle.id,
            name="name_to_test_fetching",
            description="description",
            user=1,
            chapter=None,
        )
        id_to_test = note1.id

        # WHEN checking for an existing note
        result = self.chron_svc.fetch_note_by_id(id_to_test)

        # THEN return the requested note
        assert result == note1

        # WHEN checking for a note that doesn't exist
        # THEN raise a ValueError
        with pytest.raises(ValueError, match="No note found with ID"):
            self.chron_svc.fetch_note_by_id(98765438820012)

    def test_fetch_all_npcs(self, mock_ctx, caplog):
        """Test fetch_note_by_id()."""
        # GIVEN a chronicle and associated NPCs
        chronicle = Chronicle.create(
            guild_id=mock_ctx.guild.id,
            name="fetch_all_npcs",
            description="description",
            is_active=True,
        )
        npc1 = ChronicleNPC.create(
            chronicle=chronicle.id,
            name="name1",
            npc_class="npc_class",
            description="description",
        )
        npc2 = ChronicleNPC.create(
            chronicle=chronicle.id,
            name="name2",
            npc_class="npc_class",
            description="description",
        )

        # WHEN getching all NPCs without a cache
        result = self.chron_svc.fetch_all_npcs(chronicle)
        captured = caplog.text

        ## THEN confirm all NPCs are returned from the database
        assert result == [npc1, npc2]
        assert "DATABASE: Fetch all NPCs for chronicle" in captured

        # WHEN getching all NPCs from the cache
        result = self.chron_svc.fetch_all_npcs(chronicle)
        captured2 = caplog.text

        ## THEN confirm all NPCs are returned from the cache
        assert result == [npc1, npc2]
        assert "CACHE: Return npcs for chronicle" in captured2

    def test_set_active(self, mock_ctx):
        """Test set_active()."""
        # GIVEN two chronicles, one that is active and one that is not
        chronicle1 = Chronicle.create(
            guild_id=mock_ctx.guild.id,
            name="test_set_active1",
            description="description",
            is_active=True,
        )
        chronicle2 = Chronicle.create(
            guild_id=mock_ctx.guild.id,
            name="test_set_active2",
            description="description",
            is_active=False,
        )

        # WHEN set_active is called
        self.chron_svc.set_active(mock_ctx, chronicle2)

        # THEN update the database and the cache
        assert Chronicle.get_by_id(chronicle2.id).is_active
        assert not Chronicle.get_by_id(chronicle1.id).is_active

    def test_set_inactive_one(self, mock_ctx):
        """Test set_inactive()."""
        # GIVEN a single active chronicle
        self.chron_svc.purge_cache()
        for c in Chronicle.select().where(Chronicle.is_active == True):  # noqa: E712
            c.is_active = False
            c.save()

        chronicle = Chronicle.create(
            guild_id=mock_ctx.guild.id,
            name="set_inactive",
            description="description",
            is_active=True,
        )

        # WHEN set_inactive is called
        self.chron_svc.set_inactive(mock_ctx)

        # THEN the database and cache are updated
        assert not self.chron_svc.active_chronicle_cache[mock_ctx.guild.id]
        assert not Chronicle.get_by_id(chronicle.id).is_active

    def test_purge_cache_one(self, mock_ctx, mock_ctx2):
        """Test purge_cache() with a ctx."""
        # GIVEN a chronicle service with a populated cache
        chronicle = Chronicle.create(
            guild_id=mock_ctx.guild.id,
            name="test_purge_cache_one",
            description="description",
        )
        Chronicle.create(
            guild_id=mock_ctx.guild.id,
            name="test_purge_cache_one2",
            description="description",
        )
        chapter1 = ChronicleChapter.create(
            chronicle=chronicle.id,
            chapter=1,
            name="to_delete",
            short_description="short_description",
            description="description",
        )
        ChronicleNPC.create(
            chronicle=chronicle.id,
            name="name",
            npc_class="npc_class",
            description="description",
        )
        ChronicleNote.create(
            chronicle=chronicle.id,
            name="name",
            description="description",
            user=1,
            chapter=chapter1.id,
        )
        ChronicleNote.create(
            chronicle=chronicle.id,
            name="name",
            description="description",
            user=1,
            chapter=None,
        )

        self.chron_svc.set_active(mock_ctx, chronicle)
        self.chron_svc.fetch_all(mock_ctx)
        self.chron_svc.fetch_all(mock_ctx2)
        self.chron_svc.fetch_all_chapters(chronicle)
        self.chron_svc.fetch_all_notes(chronicle)
        self.chron_svc.fetch_all_npcs(chronicle)

        assert mock_ctx.guild.id in self.chron_svc.chronicle_cache
        assert mock_ctx2.guild.id in self.chron_svc.chronicle_cache
        assert chronicle.id in self.chron_svc.chapter_cache
        assert chronicle.id in self.chron_svc.note_cache
        assert chronicle.id in self.chron_svc.npc_cache

        # WHEN purge_cache is called with a ctx
        self.chron_svc.purge_cache(mock_ctx)

        # THEN the cache is purged for the guild
        assert mock_ctx.guild.id not in self.chron_svc.chronicle_cache
        assert mock_ctx2.guild.id in self.chron_svc.chronicle_cache
        assert chronicle.id not in self.chron_svc.chapter_cache
        assert chronicle.id not in self.chron_svc.note_cache
        assert chronicle.id not in self.chron_svc.npc_cache

    def test_purge_cache_two(self, mock_ctx, mock_ctx2):
        """Test purge_cache() with a ctx."""
        # GIVEN a chronicle service with a populated cache
        chronicle = Chronicle.get_by_id(1)
        self.chron_svc.fetch_all(mock_ctx)
        self.chron_svc.fetch_all(mock_ctx2)
        self.chron_svc.set_active(mock_ctx, chronicle)
        self.chron_svc.fetch_all_chapters(chronicle)
        self.chron_svc.fetch_all_notes(chronicle)
        self.chron_svc.fetch_all_npcs(chronicle)

        # WHEN purge_cache is called with a ctx
        self.chron_svc.purge_cache()

        # THEN the cache is purged for the guild
        assert self.chron_svc.chronicle_cache == {}
        assert self.chron_svc.chapter_cache == {}
        assert self.chron_svc.note_cache == {}
        assert self.chron_svc.npc_cache == {}
        assert self.chron_svc.active_chronicle_cache == {}

    def test_update_chapter(self, mock_ctx):
        """Test update_chapter()."""
        # GIVEN a chapter
        chronicle = Chronicle.get_by_id(1)
        chapter1 = ChronicleChapter.create(
            chronicle=chronicle.id,
            chapter=1,
            name="update_chapter",
            short_description="short_description",
            description="description",
        )
        self.chron_svc.fetch_all_chapters(chronicle)

        # WHEN update_chapter is called
        updates = {
            "name": "new name",
            "short_description": "new short desc",
            "description": "new desc",
        }
        self.chron_svc.update_chapter(mock_ctx, chapter1, **updates)

        # THEN the chapter is updated in the database and cache
        updated_chapter = ChronicleChapter.get_by_id(chapter1.id)
        assert updated_chapter.name == "new name"
        assert updated_chapter.short_description == "new short desc"
        assert updated_chapter.description == "new desc"
        assert chronicle.id not in self.chron_svc.chapter_cache

    def test_update_chronicle(self, mock_ctx):
        """Test update_chronicle()."""
        # GIVEN a chronicle and a cache
        chronicle = Chronicle.get_by_id(1)
        self.chron_svc.fetch_all(mock_ctx)

        # WHEN update_chronicle is called
        updates = {"name": "new name", "description": "new desc"}
        self.chron_svc.update_chronicle(mock_ctx, chronicle, **updates)

        # THEN the chronicle is updated in the database and the cache is purged
        updated_chronicle = Chronicle.get_by_id(1)
        assert updated_chronicle.name == "new name"
        assert updated_chronicle.description == "new desc"
        assert mock_ctx.guild.id not in self.chron_svc.chronicle_cache

    def test_update_note(self, mock_ctx):
        """Test update_note()."""
        # GIVEN a note and a cache
        chronicle = Chronicle.get_by_id(1)
        note1 = ChronicleNote.create(
            chronicle=chronicle.id, name="name", description="description", user=1, chapter=None
        )
        self.chron_svc.fetch_all_notes(chronicle)

        # WHEN update_note is called
        updates = {"name": "new name", "description": "new desc"}
        self.chron_svc.update_note(mock_ctx, note1, **updates)

        # THEN the note is updated in the database and the cache is purged
        updated_note = ChronicleNote.get_by_id(note1.id)
        assert updated_note.name == "new name"
        assert updated_note.description == "new desc"
        assert chronicle.id not in self.chron_svc.note_cache

    def test_update_npc(self, mock_ctx):
        """Test update_npc()."""
        # GIVEN a npc and a cache
        chronicle = Chronicle.get_by_id(1)
        npc1 = ChronicleNPC.create(
            chronicle=chronicle.id,
            name="name",
            npc_class="npc_class",
            description="description",
        )
        self.chron_svc.fetch_all_npcs(chronicle)

        # WHEN update_npc is called
        updates = {"name": "new name", "npc_class": "new class", "description": "new desc"}
        self.chron_svc.update_npc(mock_ctx, npc1, **updates)

        # THEN the npc is updated in the database and the cache is purged
        updated_npc = ChronicleNPC.get_by_id(npc1.id)
        assert updated_npc.name == "new name"
        assert updated_npc.npc_class == "new class"
        assert updated_npc.description == "new desc"
        assert chronicle.id not in self.chron_svc.npc_cache
