# type: ignore
"""Tests for the webui helpers."""

from contextlib import asynccontextmanager

import pytest
from quart import session
from werkzeug.exceptions import InternalServerError

from tests.factories import *
from valentina.webui.utils import helpers


@pytest.mark.drop_db
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

        # Test with no active campaign set
        session["ACTIVE_CAMPAIGN_ID"] = None
        with pytest.raises(InternalServerError) as excinfo:
            await helpers.fetch_active_campaign()
        assert excinfo.value.code == 500
        assert str(excinfo.value) == "500 Internal Server Error: Session active campaign not found"

        # Test with only one campaign
        session["GUILD_CAMPAIGNS"] = {campaign1.name: str(campaign1.id)}
        single_campaign = await helpers.fetch_active_campaign()
        assert single_campaign is not None
        assert single_campaign.id == campaign1.id
        assert session["ACTIVE_CAMPAIGN_ID"] == str(campaign1.id)


@pytest.mark.drop_db
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


@pytest.mark.asyncio
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


@pytest.mark.asyncio
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
