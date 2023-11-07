# type: ignore
"""Test the autocomplete functions."""

import discord
import pytest
from discord.commands import OptionChoice
from rich import print

from valentina.models import Campaign
from valentina.utils import autocomplete

from .factories import *


@pytest.mark.drop_db()
async def test_select_campaign(campaign_factory, mock_ctx1):
    """Test the select_campaign function."""
    # GIVEN a campaign in the database
    campaign = campaign_factory.build(name="mock_campaign", guild=mock_ctx1.interaction.guild.id)
    await campaign.insert()

    mock_ctx1.options = {"campaign": "mock_campaign"}

    # WHEN calling select_campaign
    result = await autocomplete.select_campaign(mock_ctx1)

    # THEN the campaign is returned
    assert len(result) == 1
    assert result[0].name == "mock_campaign"
    assert result[0].value == str(campaign.id)


@pytest.mark.no_db()
async def test_select_vampire_clan(mock_ctx1):
    """Test the select_vampire_clan function."""
    # GIVEN a mock context
    mock_ctx1.options = {"vampire_clan": "Ventrue"}

    # WHEN calling select_vampire_clan
    result = await autocomplete.select_vampire_clan(mock_ctx1)

    # THEN the clan is returned
    assert len(result) == 1
    assert result[0].name == "Ventrue"
    assert result[0].value == "VENTRUE"

    # GIVEN a mock context
    mock_ctx1.options = {"vampire_clan": "some_thing"}

    # WHEN calling select_vampire_clan
    result = await autocomplete.select_vampire_clan(mock_ctx1)

    # THEN the clan is returned
    assert len(result) == 0


@pytest.mark.no_db()
async def test_select_trait_category(mock_ctx1):
    """Test the select_trait_category function."""
    # GIVEN a mock context
    mock_ctx1.options = {"category": "physical"}

    # WHEN calling select_trait_category
    result = await autocomplete.select_trait_category(mock_ctx1)

    # THEN the category is returned
    assert len(result) == 1
    assert result[0].name == "Physical"
    assert result[0].value == "PHYSICAL"

    # GIVEN a mock context
    mock_ctx1.options = {"category": "some_thing"}

    # WHEN calling select_trait_category
    result = await autocomplete.select_trait_category(mock_ctx1)

    # THEN the category is returned
    assert len(result) == 0


@pytest.mark.drop_db()
async def test_select_storyteller_character(mock_ctx1, character_factory):
    """Test the select_storyteller_character function."""
    # GIVEN two characters in the database and a mock_ context
    character1 = character_factory.build(
        name_first="character1",
        name_last="character1",
        guild=mock_ctx1.interaction.guild.id,
        type_storyteller=True,
        type_player=False,
        type_chargen=False,
        is_alive=True,
        traits=[],
    )

    character2 = character_factory.build(
        name_first="character2",
        name_last="character2",
        guild=mock_ctx1.interaction.guild.id,
        type_storyteller=False,
        type_player=True,
        type_chargen=False,
        is_alive=True,
        traits=[],
    )

    await character1.insert()
    await character2.insert()

    mock_ctx1.value = "char"

    # WHEN calling select_storyteller_character
    result = await autocomplete.select_storyteller_character(mock_ctx1)

    # THEN the storyteller character is returned
    assert len(result) == 1
    assert result[0].name == "character1 character1"
    assert result[0].value == str(character1.id)
