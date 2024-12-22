# type: ignore
"""Tests for the webui helpers."""

from contextlib import asynccontextmanager

import pytest
from quart import session
from werkzeug.exceptions import InternalServerError

from tests.factories import *
from valentina.models import DictionaryTerm
from valentina.webui.utils import helpers


async def test_fetch_active_campaign(debug, app_request_context, mock_session, campaign_factory):
    """Test the fetch_active_campaign function."""
    # Given: Two test campaigns exist in the database
    campaign1 = campaign_factory.build()
    await campaign1.insert()

    campaign2 = campaign_factory.build()
    await campaign2.insert()

    # And: The session data includes both campaigns with campaign1 as active
    mock_session_data = mock_session(campaigns=[campaign1, campaign2], active_campaign=campaign1)

    # When: Setting up the request context
    request_context = asynccontextmanager(app_request_context)

    async with request_context("/"):
        # And: The session is populated with mock data
        session.update(mock_session_data)

        # Then: The active campaign can be fetched
        active_campaign = await helpers.fetch_active_campaign()
        assert active_campaign is not None
        assert active_campaign.id == campaign1.id

        # When: Fetching a specific campaign
        specific_campaign = await helpers.fetch_active_campaign(campaign_id=str(campaign2.id))
        # Then: That campaign is returned and set as active
        assert specific_campaign is not None
        assert specific_campaign.id == campaign2.id
        assert session["ACTIVE_CAMPAIGN_ID"] == str(campaign2.id)

        # Given: No active campaign is set
        session["ACTIVE_CAMPAIGN_ID"] = None
        # Then: None is returned since we don't know which campaign to set as active
        assert await helpers.fetch_active_campaign() is None

        # Given: Only one campaign exists in the session
        session["GUILD_CAMPAIGNS"] = {campaign1.name: str(campaign1.id)}
        # When: Fetching the active campaign
        single_campaign = await helpers.fetch_active_campaign()
        # Then: That campaign is returned and set as active
        assert single_campaign is not None
        assert single_campaign.id == campaign1.id
        assert session["ACTIVE_CAMPAIGN_ID"] == str(campaign1.id)


async def test_fetch_active_character(debug, app_request_context, mock_session, character_factory):
    """Test the fetch_active_character function."""
    # Given: Two test characters exist in the database
    character1 = character_factory.build()
    await character1.insert()

    character2 = character_factory.build()
    await character2.insert()

    # And: The session data includes both characters with character1 as active
    mock_session_data = mock_session(
        characters=[character1, character2], active_character=character1
    )

    # When: Setting up the request context
    request_context = asynccontextmanager(app_request_context)

    async with request_context("/"):
        # And: The session is populated with mock data
        session.update(mock_session_data)

        # Then: The active character can be fetched
        active_character = await helpers.fetch_active_character()
        assert active_character is not None
        assert active_character.id == character1.id

        # When: Fetching a specific character
        specific_character = await helpers.fetch_active_character(character_id=str(character2.id))
        # Then: That character is returned and set as active
        assert specific_character is not None
        assert specific_character.id == character2.id
        assert session["ACTIVE_CHARACTER_ID"] == str(character2.id)

        # Given: No active character is set and no characters exist in session
        session["ACTIVE_CHARACTER_ID"] = None
        session["USER_CHARACTERS"] = []

        # Then: An error is raised when trying to fetch active character
        with pytest.raises(InternalServerError, match="No active character found") as excinfo:
            await helpers.fetch_active_character()
        assert excinfo.value.code == 500

        # Given: Only one character exists in the session
        session["USER_CHARACTERS"] = [
            helpers.CharacterSessionObject(
                id=str(character1.id),
                name=character1.name,
                campaign_name="Test Campaign",
                campaign_id="test_campaign_id",
                owner_name="Test Owner",
                owner_id=1234,
                type_storyteller=False,
            ).__dict__
        ]

        # Then: That character is returned as active
        single_character = await helpers.fetch_active_character()
        assert single_character.id == character1.id

        # Given: Multiple characters exist but no active character is set
        session["ACTIVE_CHARACTER_ID"] = None
        session["USER_CHARACTERS"] = [
            helpers.CharacterSessionObject(
                id=str(character1.id),
                name=character1.name,
                campaign_name="Test Campaign",
                campaign_id="test_campaign_id",
                owner_name="Test Owner",
                owner_id=1234,
                type_storyteller=False,
            ).__dict__,
            helpers.CharacterSessionObject(
                id=str(character2.id),
                name=character2.name,
                campaign_name="Test Campaign",
                campaign_id="test_campaign_id",
                owner_name="Test Owner",
                owner_id=1234,
                type_storyteller=False,
            ).__dict__,
        ]

        # Then: An error is raised since we don't know which character to make active
        with pytest.raises(
            InternalServerError, match="Multiple characters found and no active character set"
        ) as excinfo:
            await helpers.fetch_active_character()
        assert excinfo.value.code == 500


async def test_fetch_campaigns(app_request_context, mock_session, campaign_factory, guild_factory):
    """Test the fetch_campaigns function."""
    # Given: A guild exists with three campaigns, two active and one deleted
    guild = guild_factory.build()
    await guild.insert()
    campaign1 = campaign_factory.build(guild=guild.id, is_deleted=False)
    campaign2 = campaign_factory.build(guild=guild.id, is_deleted=False)
    campaign3 = campaign_factory.build(guild=guild.id, is_deleted=True)
    await campaign1.insert()
    await campaign2.insert()
    await campaign3.insert()

    # And: The session contains the guild ID
    mock_session_data = mock_session(guild_id=guild.id)

    # When: Setting up the request context
    request_context = asynccontextmanager(app_request_context)

    async with request_context("/"):
        # And: The session is populated with mock data
        session.update(mock_session_data)

        # Then: Only the two active campaigns are returned
        campaigns = await helpers.fetch_campaigns()
        assert len(campaigns) == 2
        assert all(campaign.id in [campaign1.id, campaign2.id] for campaign in campaigns)

        # And: The session is updated with the campaign mapping
        assert session["GUILD_CAMPAIGNS"] == {
            campaign1.name: str(campaign1.id),
            campaign2.name: str(campaign2.id),
        }


async def test_fetch_guild(app_request_context, mock_session, guild_factory):
    """Test the fetch_campaigns function."""
    # Given: A guild exists in the database
    guild = guild_factory.build()
    await guild.insert()

    # And: The session contains the guild ID
    mock_session_data = mock_session(guild_id=guild.id)

    # When: Setting up the request context
    request_context = asynccontextmanager(app_request_context)

    async with request_context("/"):
        # And: The session is populated with mock data
        session.update(mock_session_data)

        # Then: The guild is fetched successfully
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
    # Given: A guild exists with a campaign
    guild = guild_factory.build()
    await guild.insert()

    campaign = campaign_factory.build(guild=guild.id)
    await campaign.insert()

    # And: Two users exist in the guild
    user1 = user_factory.build()
    await user1.insert()
    user2 = user_factory.build()
    await user2.insert()

    # And: User1 has two player characters
    character1 = character_factory.build(
        user_owner=user1.id, guild=guild.id, type_player=True, campaign=str(campaign.id)
    )
    await character1.insert()
    character2 = character_factory.build(
        user_owner=user1.id, guild=guild.id, type_player=True, campaign=str(campaign.id)
    )
    await character2.insert()

    # And: User2 has one player character
    character3 = character_factory.build(
        user_owner=user2.id, guild=guild.id, type_player=True, campaign=str(campaign.id)
    )
    await character3.insert()

    # And: User1 has one storyteller character
    character4 = character_factory.build(
        user_owner=user1.id,
        guild=guild.id,
        type_player=False,
        type_storyteller=True,
        campaign=str(campaign.id),
    )
    await character4.insert()

    # And: The session is set up for user1
    mock_session_data = mock_session(guild_id=str(guild.id), user_id=str(user1.id))
    request_context = asynccontextmanager(app_request_context)

    async with request_context("/"):
        # When: The session is populated with mock data
        session.update(mock_session_data)

        # And: We fetch the user's characters
        characters = await helpers.fetch_user_characters()

        # Then: Only user1's player characters are returned
        assert len(characters) == 2
        for character in characters:
            assert str(character.id) in [str(character1.id), str(character2.id)]

        # And: The session is updated with the correct character data
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
    # Given: A guild exists with a campaign and two users
    guild = guild_factory.build()
    await guild.insert()

    campaign = campaign_factory.build(guild=guild.id)
    await campaign.insert()

    user1 = user_factory.build()
    await user1.insert()
    user2 = user_factory.build()
    await user2.insert()

    # And: There are 3 player characters and 1 storyteller character
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

    # And: The session is set up for user1
    mock_session_data = mock_session(guild_id=str(guild.id), user_id=str(user1.id))
    request_context = asynccontextmanager(app_request_context)

    async with request_context("/"):
        # When: The session is populated and fetch_all_characters is called
        session.update(mock_session_data)
        characters = await helpers.fetch_all_characters()

        # Then: Only the 3 player characters are returned
        assert len(characters) == 3
        for character in characters:
            assert str(character.id) in [str(character1.id), str(character2.id), str(character3.id)]

        # And: The session is updated with the player characters
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
    # Given: A guild exists with a campaign and two users
    guild = guild_factory.build()
    await guild.insert()

    campaign = campaign_factory.build(guild=guild.id)
    await campaign.insert()

    user1 = user_factory.build()
    await user1.insert()
    user2 = user_factory.build()
    await user2.insert()

    # And: There are 3 player characters and 1 storyteller character
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

    # And: The session is set up for user1
    mock_session_data = mock_session(guild_id=str(guild.id), user_id=str(user1.id))
    request_context = asynccontextmanager(app_request_context)

    async with request_context("/"):
        session.update(mock_session_data)

        # When: Fetching storyteller characters
        characters = await helpers.fetch_storyteller_characters()

        # Then: Only the storyteller character is returned
        assert len(characters) == 1
        for character in characters:
            assert str(character.id) in [str(character4.id)]

        # And: The session is updated with the storyteller characters
        session_characters = session["STORYTELLER_CHARACTERS"]
        assert len(session_characters) == 1
        for session_character in session_characters:
            assert session_character["id"] in [str(character4.id)]


async def test_is_storyteller(app_request_context, mock_session, user_factory, guild_factory):
    """Test the is_storyteller function."""
    # Given: A guild exists with one storyteller
    guild = guild_factory.build()
    await guild.insert()

    user1 = user_factory.build()
    await user1.insert()

    user2 = user_factory.build()
    await user2.insert()

    guild.storytellers = [user1.id]
    await guild.save()

    # When: The session contains the storyteller user
    mock_session_data = mock_session(guild_id=str(guild.id), user_id=str(user1.id))
    request_context = asynccontextmanager(app_request_context)

    async with request_context("/"):
        session.update(mock_session_data)

        # Then: The user is identified as a storyteller
        assert await helpers.is_storyteller() is True

    # When: The session contains a non-storyteller user
    mock_session_data = mock_session(guild_id=str(guild.id), user_id=str(user2.id))
    request_context = asynccontextmanager(app_request_context)

    async with request_context("/"):
        session.update(mock_session_data)

        # Then: The user is not identified as a storyteller
        assert await helpers.is_storyteller() is False


@pytest.mark.drop_db
async def test_term_linker(app_request_context, mock_session):
    """Test the term linker function."""
    # Given: Two dictionary terms exist in the database
    dict_term1 = DictionaryTerm(
        term="aaaaa",
        synonyms=["bbbbb"],
        definition="abcdefg",
        guild_id=1,
    )
    dict_term2 = DictionaryTerm(
        term="ccccc",
        synonyms=[],
        link="http://google.com",
        guild_id=1,
    )
    await dict_term1.insert()
    await dict_term2.insert()

    # And: A test string containing terms that should be linked
    test_string = "Curaaaaabitur blandit aaaaa tempus ardua bbbbb ridiculous sed ccccc magna."

    # And: A mock session is set up
    mock_session_data = mock_session()

    # And: The app request context is converted to async
    request_context = asynccontextmanager(app_request_context)

    async with request_context("/"):
        # And: The session is populated with mock data
        session.update(mock_session_data)

        # When/Then: Terms are converted to HTML links
        assert (
            await helpers.link_terms(test_string, link_type="html")
            == "Curaaaaabitur blandit <a href='/dictionary/term/aaaaa'>aaaaa</a> tempus ardua <a href='/dictionary/term/aaaaa'>bbbbb</a> ridiculous sed <a href='http://google.com'>ccccc</a> magna."
        )

        # When/Then: Terms are converted to markdown links
        assert (
            await helpers.link_terms(test_string, link_type="markdown")
            == "Curaaaaabitur blandit [aaaaa](/dictionary/term/aaaaa) tempus ardua [bbbbb](/dictionary/term/aaaaa) ridiculous sed [ccccc](http://google.com) magna."
        )

        # When/Then: Excluded terms are not converted to links
        assert (
            await helpers.link_terms(test_string, link_type="markdown", excludes=["aaaaa", "ccccc"])
            == test_string
        )
