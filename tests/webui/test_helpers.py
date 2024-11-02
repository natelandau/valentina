# type: ignore
"""Tests for the webui helpers."""

from contextlib import asynccontextmanager

import pytest
from quart import session
from werkzeug.exceptions import InternalServerError

from tests.factories import *
from valentina.webui.utils import helpers


async def test_fetch_active_campaign(debug, app_request_context, mock_session, campaign_factory):
    """Test the fetch_active_campaign function."""
    # Create test campaigns
    campaign1 = campaign_factory.build()
    await campaign1.insert()

    campaign2 = campaign_factory.build()
    await campaign2.insert()

    # Set up mock session data
    mock_session_data = mock_session(campaigns=[campaign1, campaign2], active_campaign=campaign1)

    # Convert app_request_context to an async context manager
    request_context = asynccontextmanager(app_request_context)

    async with request_context("/"):
        # Populate the session with mock data
        session.update(mock_session_data)

        # Test fetching the active campaign
        active_campaign = await helpers.fetch_active_campaign()
        assert active_campaign is not None
        assert active_campaign.id == campaign1.id

        # Test fetching a specific campaign
        specific_campaign = await helpers.fetch_active_campaign(campaign_id=str(campaign2.id))
        assert specific_campaign is not None
        assert specific_campaign.id == campaign2.id
        assert session["ACTIVE_CAMPAIGN_ID"] == str(campaign2.id)

        # Test with no active campaign set. Should return None b/c we don't know which campaign to set as active
        session["ACTIVE_CAMPAIGN_ID"] = None
        assert await helpers.fetch_active_campaign() is None

        # Test with only one campaign
        session["GUILD_CAMPAIGNS"] = {campaign1.name: str(campaign1.id)}
        single_campaign = await helpers.fetch_active_campaign()
        assert single_campaign is not None
        assert single_campaign.id == campaign1.id
        assert session["ACTIVE_CAMPAIGN_ID"] == str(campaign1.id)


async def test_fetch_active_character(debug, app_request_context, mock_session, character_factory):
    """Test the fetch_active_character function."""
    # Create test characters
    character1 = character_factory.build()
    await character1.insert()

    character2 = character_factory.build()
    await character2.insert()

    # Set up mock session data
    mock_session_data = mock_session(
        characters=[character1, character2], active_character=character1
    )

    # Convert app_request_context to an async context manager
    request_context = asynccontextmanager(app_request_context)

    async with request_context("/"):
        # Populate the session with mock data
        session.update(mock_session_data)

        # Test fetching the active character
        active_character = await helpers.fetch_active_character()
        assert active_character is not None
        assert active_character.id == character1.id

        # Test fetching a specific character
        specific_character = await helpers.fetch_active_character(character_id=str(character2.id))
        assert specific_character is not None
        assert specific_character.id == character2.id
        assert session["ACTIVE_CHARACTER_ID"] == str(character2.id)

        # Test with no active character set
        session["ACTIVE_CHARACTER_ID"] = None
        session["USER_CHARACTERS"] = []

        with pytest.raises(InternalServerError, match="No active character found") as excinfo:
            await helpers.fetch_active_character()
        assert excinfo.value.code == 500

        # Test with only one character
        session["USER_CHARACTERS"] = [
            helpers.CharacterSessionObject(
                id=str(character1.id),
                name=character1.name,
                campaign_name="Test Campaign",
                campaign_id="test_campaign_id",
                owner_name="Test Owner",
                owner_id=1234,
            ).__dict__
        ]

        single_character = await helpers.fetch_active_character()
        assert single_character.id == character1.id

        # Test with multiple characters and no active character set
        session["ACTIVE_CHARACTER_ID"] = None
        session["USER_CHARACTERS"] = [
            helpers.CharacterSessionObject(
                id=str(character1.id),
                name=character1.name,
                campaign_name="Test Campaign",
                campaign_id="test_campaign_id",
                owner_name="Test Owner",
                owner_id=1234,
            ).__dict__,
            helpers.CharacterSessionObject(
                id=str(character2.id),
                name=character2.name,
                campaign_name="Test Campaign",
                campaign_id="test_campaign_id",
                owner_name="Test Owner",
                owner_id=1234,
            ).__dict__,
        ]

        with pytest.raises(
            InternalServerError, match="Multiple characters found and no active character set"
        ) as excinfo:
            await helpers.fetch_active_character()
        assert excinfo.value.code == 500


async def test_fetch_campaigns(app_request_context, mock_session, campaign_factory, guild_factory):
    """Test the fetch_campaigns function."""
    # Create database objects
    guild = guild_factory.build()
    await guild.insert()
    campaign1 = campaign_factory.build(guild=guild.id, is_deleted=False)
    campaign2 = campaign_factory.build(guild=guild.id, is_deleted=False)
    campaign3 = campaign_factory.build(guild=guild.id, is_deleted=True)
    await campaign1.insert()
    await campaign2.insert()
    await campaign3.insert()

    # Set up mock session data
    mock_session_data = mock_session(guild_id=guild.id)

    # Convert app_request_context to an async context manager
    request_context = asynccontextmanager(app_request_context)

    async with request_context("/"):
        # Populate the session with mock data
        session.update(mock_session_data)

        campaigns = await helpers.fetch_campaigns()
        assert len(campaigns) == 2
        assert all(campaign.id in [campaign1.id, campaign2.id] for campaign in campaigns)
        assert session["GUILD_CAMPAIGNS"] == {
            campaign1.name: str(campaign1.id),
            campaign2.name: str(campaign2.id),
        }


async def test_fetch_guild(app_request_context, mock_session, guild_factory):
    """Test the fetch_campaigns function."""
    # Create database objects
    guild = guild_factory.build()
    await guild.insert()

    # Set up mock session data
    mock_session_data = mock_session(guild_id=guild.id)

    # Convert app_request_context to an async context manager
    request_context = asynccontextmanager(app_request_context)

    async with request_context("/"):
        # Populate the session with mock data
        session.update(mock_session_data)

        fetched_guild = await helpers.fetch_guild()
        assert fetched_guild.id == guild.id
        assert fetched_guild.name == guild.name
        assert session["GUILD_NAME"] == guild.name


async def test_fetch_user_characters(
    debug,
    app_request_context,
    campaign_factory,
    mock_session,
    character_factory,
    user_factory,
    guild_factory,
):
    """Test the fetch_user_characters function."""
    # Create database objects
    guild = guild_factory.build()
    await guild.insert()

    campaign = campaign_factory.build(guild=guild.id)
    await campaign.insert()

    user1 = user_factory.build()
    await user1.insert()
    user2 = user_factory.build()
    await user2.insert()

    # Create test characters
    character1 = character_factory.build(
        user_owner=user1.id, guild=guild.id, type_player=True, campaign=str(campaign.id)
    )
    await character1.insert()
    character2 = character_factory.build(
        user_owner=user1.id, guild=guild.id, type_player=True, campaign=str(campaign.id)
    )
    await character2.insert()
    character3 = character_factory.build(
        user_owner=user2.id, guild=guild.id, type_player=True, campaign=str(campaign.id)
    )
    await character3.insert()
    character4 = character_factory.build(
        user_owner=user1.id,
        guild=guild.id,
        type_player=False,
        type_storyteller=True,
        campaign=str(campaign.id),
    )
    await character4.insert()

    # Set up mock session data
    mock_session_data = mock_session(guild_id=str(guild.id), user_id=str(user1.id))

    # Convert app_request_context to an async context manager
    request_context = asynccontextmanager(app_request_context)

    async with request_context("/"):
        # Populate the session with mock data
        session.update(mock_session_data)

        characters = await helpers.fetch_user_characters()
        assert len(characters) == 2
        for character in characters:
            assert str(character.id) in [str(character1.id), str(character2.id)]

        session_characters = session["USER_CHARACTERS"]
        assert len(session_characters) == 2
        for session_character in session_characters:
            assert session_character["id"] in [str(character1.id), str(character2.id)]


async def test_fetch_all_characters(
    debug,
    app_request_context,
    campaign_factory,
    mock_session,
    character_factory,
    user_factory,
    guild_factory,
):
    """Test the fetch_all_characters function."""
    # Create database objects
    guild = guild_factory.build()
    await guild.insert()

    campaign = campaign_factory.build(guild=guild.id)
    await campaign.insert()

    user1 = user_factory.build()
    await user1.insert()
    user2 = user_factory.build()
    await user2.insert()

    # Create test characters
    character1 = character_factory.build(
        user_owner=user1.id, guild=guild.id, type_player=True, campaign=str(campaign.id)
    )
    await character1.insert()
    character2 = character_factory.build(
        user_owner=user1.id, guild=guild.id, type_player=True, campaign=str(campaign.id)
    )
    await character2.insert()
    character3 = character_factory.build(
        user_owner=user2.id, guild=guild.id, type_player=True, campaign=str(campaign.id)
    )
    await character3.insert()
    character4 = character_factory.build(
        user_owner=user1.id,
        guild=guild.id,
        type_player=False,
        type_storyteller=True,
        campaign=str(campaign.id),
    )
    await character4.insert()

    # Set up mock session data
    mock_session_data = mock_session(guild_id=str(guild.id), user_id=str(user1.id))

    # Convert app_request_context to an async context manager
    request_context = asynccontextmanager(app_request_context)

    async with request_context("/"):
        # Populate the session with mock data
        session.update(mock_session_data)

        characters = await helpers.fetch_all_characters()
        assert len(characters) == 3
        for character in characters:
            assert str(character.id) in [str(character1.id), str(character2.id), str(character3.id)]

        session_characters = session["ALL_CHARACTERS"]
        assert len(session_characters) == 3
        for session_character in session_characters:
            assert session_character["id"] in [
                str(character1.id),
                str(character2.id),
                str(character3.id),
            ]


async def test_fetch_storyteller_characters(
    debug,
    app_request_context,
    campaign_factory,
    mock_session,
    character_factory,
    user_factory,
    guild_factory,
):
    """Test the fetch_storyteller_characters function."""
    # Create database objects
    guild = guild_factory.build()
    await guild.insert()

    campaign = campaign_factory.build(guild=guild.id)
    await campaign.insert()

    user1 = user_factory.build()
    await user1.insert()
    user2 = user_factory.build()
    await user2.insert()

    # Create test characters
    character1 = character_factory.build(
        user_owner=user1.id,
        guild=guild.id,
        type_player=True,
        type_storyteller=False,
        campaign=str(campaign.id),
    )
    await character1.insert()
    character2 = character_factory.build(
        user_owner=user1.id,
        guild=guild.id,
        type_player=True,
        type_storyteller=False,
        campaign=str(campaign.id),
    )
    await character2.insert()
    character3 = character_factory.build(
        user_owner=user2.id,
        guild=guild.id,
        type_player=True,
        type_storyteller=False,
        campaign=str(campaign.id),
    )
    await character3.insert()
    character4 = character_factory.build(
        user_owner=user1.id,
        guild=guild.id,
        type_player=False,
        type_storyteller=True,
        campaign=str(campaign.id),
    )
    await character4.insert()

    # Set up mock session data
    mock_session_data = mock_session(guild_id=str(guild.id), user_id=str(user1.id))

    # Convert app_request_context to an async context manager
    request_context = asynccontextmanager(app_request_context)

    async with request_context("/"):
        # Populate the session with mock data
        session.update(mock_session_data)

        characters = await helpers.fetch_storyteller_characters()
        assert len(characters) == 1
        for character in characters:
            assert str(character.id) in [str(character4.id)]

        session_characters = session["STORYTELLER_CHARACTERS"]
        assert len(session_characters) == 1
        for session_character in session_characters:
            assert session_character["id"] in [str(character4.id)]


async def test_is_storyteller(app_request_context, mock_session, user_factory, guild_factory):
    """Test the is_storyteller function."""
    # Create database objects
    guild = guild_factory.build()
    await guild.insert()

    user1 = user_factory.build()
    await user1.insert()

    user2 = user_factory.build()
    await user2.insert()

    guild.storytellers = [user1.id]
    await guild.save()

    # Set up mock session data
    mock_session_data = mock_session(guild_id=str(guild.id), user_id=str(user1.id))

    # Convert app_request_context to an async context manager
    request_context = asynccontextmanager(app_request_context)

    async with request_context("/"):
        # Populate the session with mock data
        session.update(mock_session_data)

        assert await helpers.is_storyteller() is True

    # Set up mock session data for a user that is not a storyteller
    mock_session_data = mock_session(guild_id=str(guild.id), user_id=str(user2.id))

    # Convert app_request_context to an async context manager
    request_context = asynccontextmanager(app_request_context)

    async with request_context("/"):
        # Populate the session with mock data
        session.update(mock_session_data)

        assert await helpers.is_storyteller() is False
