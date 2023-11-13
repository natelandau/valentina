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
from valentina.utils.converters import (
    ValidCampaign,
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
    campaign = campaign_factory.build()
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
