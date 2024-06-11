# type: ignore
"""Tests for the converters module."""

import datetime

import pytest
from discord.ext.commands import BadArgument
from tests.factories import *

from valentina.constants import (
    CharacterConcept,
    CharClass,
    RNGCharLevel,
    TraitCategory,
    VampireClan,
)
from valentina.models import CampaignChapter
from valentina.utils.converters import (
    CampaignChapterConverter,
    ValidBookNumber,
    ValidCampaign,
    ValidChapterNumber,
    ValidCharacterConcept,
    ValidCharacterLevel,
    ValidCharacterName,
    ValidCharacterObject,
    ValidCharClass,
    ValidCharTrait,
    ValidClan,
    ValidImageURL,
    ValidTraitCategory,
    ValidYYYYMMDD,
)


@pytest.mark.no_db()
async def test_valid_char_class():
    """Test the ValidCharClass converter."""
    # GIVEN a ctx objext

    # WHEN the converter is called with a valid class name
    # THEN assert the result is the correct CharClass
    assert await ValidCharClass().convert(None, "MORTAL") == CharClass.MORTAL

    # WHEN the converter is called with an invalid class name
    # THEN assert a BadArgument is raised
    with pytest.raises(BadArgument):
        await ValidCharClass().convert(None, "NOT A CLASS")


@pytest.mark.no_db()
async def test_valid_character_concept():
    """Test the ValidCharacterConcept converter."""
    # GIVEN a ctx objext

    # WHEN the converter is called with a valid class name
    # THEN assert the result is the correct CharacterConcept
    assert await ValidCharacterConcept().convert(None, "SOLDIER") == CharacterConcept.SOLDIER

    # WHEN the converter is called with an invalid name
    # THEN assert a BadArgument is raised
    with pytest.raises(BadArgument):
        await ValidCharacterConcept().convert(None, "NOT_EXISTS")


@pytest.mark.no_db()
async def test_valid_rng_level():
    """Test the ValidCharacterLevel converter."""
    # GIVEN a ctx objext

    # WHEN the converter is called with a valid class name
    # THEN assert the result is the correct RNGCharLevel
    assert await ValidCharacterLevel().convert(None, "ADVANCED") == RNGCharLevel.ADVANCED

    # WHEN the converter is called with an invalid name
    # THEN assert a BadArgument is raised
    with pytest.raises(BadArgument):
        await ValidCharacterLevel().convert(None, "NOT_EXISTS")


@pytest.mark.no_db()
async def test_valid_character_name():
    """Test the ValidCharacterName converter."""
    # WHEN the converter is called with a valid name
    # THEN assert the result is the correct name
    assert await ValidCharacterName().convert(None, "Test") == "Test"

    # WHEN the converter is called with a name that isn't capitalized
    # THEN assert the result is the capitalized name
    assert await ValidCharacterName().convert(None, "testName") == "Testname"

    # WHEN the converter is called with a name that is too long
    # THEN assert a BadArgument is raised
    with pytest.raises(BadArgument):
        await ValidCharacterName().convert(None, "a" * 40)

    # WHEN the converter is called with a name that contains invalid characters
    # THEN assert a BadArgument is raised
    with pytest.raises(BadArgument):
        await ValidCharacterName().convert(None, "Test!Name")


@pytest.mark.no_db()
async def test_valid_clan():
    """Test the ValidClan converter."""
    # WHEN the converter is called with a valid class name
    # THEN assert the result is the correct ValidClan
    assert await ValidClan().convert(None, "BRUJAH") == VampireClan.BRUJAH

    # WHEN the converter is called with an invalid name
    # THEN assert a BadArgument is raised
    with pytest.raises(BadArgument):
        await ValidClan().convert(None, "NOT_EXISTS")


async def test_valid_char_trait(trait_factory):
    """Test the ValidCharTrait converter."""
    trait = trait_factory.build(revision_id=None)
    await trait.insert()

    # WHEN the converter is called with a valid trait id
    # THEN assert the result is the correct trait object
    assert await ValidCharTrait().convert(None, str(trait.id)) == trait

    # WHEN the converter is called with an invalid trait id
    # THEN assert a BadArgument is raised
    with pytest.raises(BadArgument):
        await ValidCharTrait().convert(None, "6542b9437aac63f18a1fc237")


async def test_valid_character_object(character_factory):
    """Test the ValidCharacter converter."""
    character = character_factory.build(traits=[])
    await character.insert()

    # WHEN the converter is called with a valid character id
    # THEN assert the result is the correct character object
    result = await ValidCharacterObject().convert(None, str(character.id))
    assert result.id == character.id

    # WHEN the converter is called with an invalid character id
    # THEN assert a BadArgument is raised
    with pytest.raises(BadArgument):
        await ValidCharacterObject().convert(None, "6542b9437aac63f18a1fc237")


async def test_valid_campaign(campaign_factory):
    """Test the ValidCampaign converter."""
    campaign = campaign_factory.build(characters=[])
    await campaign.insert()

    # WHEN the converter is called with a valid campaign id
    # THEN assert the result is the correct campaign object
    result = await ValidCampaign().convert(None, str(campaign.id))
    assert result.id == campaign.id

    # WHEN the converter is called with an invalid campaign id
    # THEN assert a BadArgument is raised
    with pytest.raises(BadArgument):
        await ValidCampaign().convert(None, "6542b9437aac63f18a1fc237")


@pytest.mark.no_db()
async def test_valid_image_url():
    """Test the ValidImageURL converter."""
    # WHEN the converter is called with an invalid url
    # THEN assert a BadArgument is raised
    with pytest.raises(BadArgument):
        await ValidImageURL().convert(None, "not a url")


@pytest.mark.no_db()
async def test_valid_trait_category():
    """Test the ValidTraitCategory converter."""
    # WHEN the converter is called with a valid trait category
    # THEN assert the result is the correct trait category
    assert await ValidTraitCategory().convert(None, "physical") == TraitCategory.PHYSICAL

    # WHEN the converter is called with an invalid trait category
    # THEN assert a BadArgument is raised
    with pytest.raises(BadArgument):
        await ValidTraitCategory().convert(None, "not_valid")


@pytest.mark.no_db()
async def test_valid_yyyymmdd():
    """Test the ValidYYYYMMDD converter."""
    # WHEN the converter is called with a valid date
    # THEN assert the result is the correct date
    assert await ValidYYYYMMDD().convert(None, "2021-01-01") == datetime.datetime(2021, 1, 1, 0, 0)

    # WHEN the converter is called with an invalid date
    # THEN assert a BadArgument is raised
    with pytest.raises(BadArgument):
        await ValidYYYYMMDD().convert(None, "01-01-2021")


@pytest.mark.drop_db()
async def test_valid_chapter_number(mock_ctx1, book_chapter_factory, book_factory):
    """Test the ValidChapterNumber converter."""
    chapter = book_chapter_factory.build()
    chapter_object = await chapter.insert()

    book = book_factory.build(chapters=[chapter_object])
    await book.insert()

    # WHEN the converter is called with a valid chapter number
    # THEN assert the result is the correct number
    assert await ValidChapterNumber().convert(mock_ctx1, 1) == 1

    # WHEN the converter is called with an invalid chapter number
    # THEN assert a BadArgument is raised
    with pytest.raises(BadArgument):
        await ValidChapterNumber().convert(mock_ctx1, "not a number")

    # WHEN the converter is called with a number less than zero
    # THEN assert a BadArgument is raised
    with pytest.raises(BadArgument):
        await ValidChapterNumber().convert(mock_ctx1, 0)

    # WHEN the converter is called with a number greater than number of chapters
    # THEN assert a BadArgument is raised
    with pytest.raises(BadArgument):
        await ValidChapterNumber().convert(mock_ctx1, 2)


@pytest.mark.drop_db()
async def test_campaign_chapter_converter(mock_ctx1, guild_factory, campaign_factory):
    """Test the CampaignChapterConverter converter.

    TODO: Remove this after chapter migration
    """
    # GIVEN a guild with a campaign and a mock context
    chapter = CampaignChapter(
        name="mock_chapter",
        number=1,
        description_short="mock_description",
        description_long="mock_description",
    )

    campaign = campaign_factory.build(guild=mock_ctx1.guild.id, chapters=[chapter], characters=[])
    await campaign.insert()

    guild = guild_factory.build(
        id=mock_ctx1.guild.id,
        campaigns=[campaign],
        active_campaign=campaign,
        roll_result_thumbnails=[],
    )
    await guild.insert()
    # WHEN the converter is called with a valid chapter number
    # THEN assert the result is the correct number
    assert await CampaignChapterConverter().convert(mock_ctx1, 1) == chapter

    # WHEN the converter is called with an invalid chapter number
    # THEN assert a BadArgument is raised
    with pytest.raises(BadArgument):
        await CampaignChapterConverter().convert(mock_ctx1, 2)

    # WHEN the converter is called with a number less than zero
    # THEN assert a BadArgument is raised
    with pytest.raises(BadArgument):
        await CampaignChapterConverter().convert(mock_ctx1, 0)


@pytest.mark.drop_db()
async def test_valid_book_number(mock_ctx1, guild_factory, campaign_factory, book_factory):
    """Test the ValidBookNumber converter."""
    book = book_factory.build()
    book_object = await book.insert()

    campaign = campaign_factory.build(guild=mock_ctx1.guild.id, books=[book_object], characters=[])
    await campaign.insert()

    guild = guild_factory.build(
        id=mock_ctx1.guild.id,
        campaigns=[campaign],
        active_campaign=campaign,
        roll_result_thumbnails=[],
    )
    await guild.insert()

    # WHEN the converter is called with a valid chapter number
    # THEN assert the result is the correct number
    assert await ValidBookNumber().convert(mock_ctx1, 1) == 1

    # WHEN the converter is called with an invalid chapter number
    # THEN assert a BadArgument is raised
    with pytest.raises(BadArgument):
        await ValidBookNumber().convert(mock_ctx1, "not a number")

    # WHEN the converter is called with a number less than zero
    # THEN assert a BadArgument is raised
    with pytest.raises(BadArgument):
        await ValidBookNumber().convert(mock_ctx1, 0)

    # WHEN the converter is called with a number greater than number of books
    # THEN assert a BadArgument is raised
    with pytest.raises(BadArgument):
        await ValidBookNumber().convert(mock_ctx1, 2)
