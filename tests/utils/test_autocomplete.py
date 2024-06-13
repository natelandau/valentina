# type: ignore
"""Test the autocomplete functions."""

import pytest
from tests.factories import *

from valentina.constants import TraitCategory
from valentina.models import CampaignChapter, CharacterSheetSection
from valentina.utils import autocomplete


@pytest.mark.drop_db()
async def test_select_campaign(campaign_factory, mock_ctx1):
    """Test the select_campaign function."""
    # GIVEN a campaign in the database
    campaign = campaign_factory.build(
        name="mock_campaign", guild=str(mock_ctx1.interaction.guild.id), characters=[]
    )
    await campaign.insert()

    mock_ctx1.value = "mock"

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
async def test_select_char_class(mock_ctx1):
    """Test the select_char_class function."""
    # GIVEN a mock context
    mock_ctx1.options = {"char_class": "Mort"}

    # WHEN calling select_vampire_clan
    result = await autocomplete.select_char_class(mock_ctx1)

    # THEN the clan is returned
    assert len(result) == 1
    assert result[0].name == "Mortal"
    assert result[0].value == "MORTAL"

    # GIVEN a mock context
    mock_ctx1.options = {"char_class": "some_thing"}

    # WHEN calling select_vampire_clan
    result = await autocomplete.select_char_class(mock_ctx1)

    # THEN the clan is returned
    assert len(result) == 0


@pytest.mark.no_db()
async def test_select_char_concept(mock_ctx1):
    """Test the select_char_concept function."""
    # GIVEN a mock context
    mock_ctx1.options = {"concept": "Sold"}

    # WHEN calling select_vampire_clan
    result = await autocomplete.select_char_concept(mock_ctx1)

    # THEN the clan is returned
    assert len(result) == 1
    assert result[0].name == "Soldier"
    assert result[0].value == "SOLDIER"

    # GIVEN a mock context
    mock_ctx1.options = {"concept": "some_thing"}

    # WHEN calling select_vampire_clan
    result = await autocomplete.select_char_concept(mock_ctx1)

    # THEN the clan is returned
    assert len(result) == 0


@pytest.mark.no_db()
async def test_select_char_level(mock_ctx1):
    """Test the select_char_level function."""
    # GIVEN a mock context
    mock_ctx1.options = {"level": "Adv"}

    # WHEN calling select_vampire_clan
    result = await autocomplete.select_char_level(mock_ctx1)

    # THEN the clan is returned
    assert len(result) == 1
    assert result[0].name == "Advanced"
    assert result[0].value == "ADVANCED"

    # GIVEN a mock context
    mock_ctx1.options = {"level": "some_thing"}

    # WHEN calling select_vampire_clan
    result = await autocomplete.select_char_level(mock_ctx1)

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


@pytest.mark.drop_db()
async def test_select_chapter(mock_ctx1, book_factory, book_chapter_factory):
    """Test the select_chapter function."""
    chapter = book_chapter_factory.build(
        name="mock_chapter",
        number=1,
    )
    chapter_object = await chapter.insert()

    book = book_factory.build(chapters=[chapter_object])
    await book.insert()

    # WHEN calling select_chapter
    mock_ctx1.options = {"chapter": "mock"}
    result = await autocomplete.select_chapter(mock_ctx1)

    # THEN the chapter is returned
    assert len(result) == 1
    assert result[0].name == "1. mock_chapter"
    assert result[0].value == str(chapter_object.id)


@pytest.mark.drop_db()
async def test_select_book(mock_ctx1, book_factory, campaign_factory, guild_factory):
    """Test the select_book autocomplete function."""
    book = book_factory.build(name="mock_book", number=1)
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

    # WHEN calling select_chapter
    mock_ctx1.options = {"book": "mock"}
    result = await autocomplete.select_book(mock_ctx1)

    # THEN the chapter is returned
    assert len(result) == 1
    assert result[0].name == "1. mock_book"
    assert result[0].value == str(book_object.id)


@pytest.mark.drop_db()
async def test_select_char_trait(mock_ctx1, user_factory, character_factory, trait_factory):
    """Test the select_char_trait function."""
    # GIVEN a character with a trait and a user with an active character
    trait = trait_factory.build(
        category_name=TraitCategory.PHYSICAL.name, name="Dexterity", value=3, max_value=5
    )
    await trait.insert()
    character = character_factory.build(
        name_first="character",
        name_last="character",
        guild=mock_ctx1.guild.id,
        type_storyteller=True,
        type_player=False,
        type_chargen=False,
        is_alive=True,
        traits=[trait],
    )
    await character.insert()

    user = user_factory.build(
        id=mock_ctx1.author.id,
        active_characters={str(mock_ctx1.guild.id): character},
        characters=[character],
        campaign_experience={},
        macros=[],
    )
    await user.insert()

    # WHEN calling select_char_trait
    mock_ctx1.options = {"trait": "dexterity"}
    result = await autocomplete.select_char_trait(mock_ctx1)

    # THEN the trait and its index is returned
    assert len(result) == 1
    assert result[0].name == "Dexterity"
    assert result[0].value == str(trait.id)


@pytest.mark.drop_db()
async def test_select_char_trait_two(mock_ctx1, user_factory, character_factory, trait_factory):
    """Test the select_char_trait_two function."""
    # GIVEN a character with a trait and a user with an active character
    trait = trait_factory.build(
        category_name=TraitCategory.PHYSICAL.name, name="Dexterity", value=3, max_value=5
    )
    await trait.insert()
    character = character_factory.build(
        name_first="character",
        name_last="character",
        guild=mock_ctx1.guild.id,
        type_storyteller=True,
        type_player=False,
        type_chargen=False,
        is_alive=True,
        traits=[trait],
    )
    await character.insert()

    user = user_factory.build(
        id=mock_ctx1.author.id,
        active_characters={str(mock_ctx1.guild.id): character},
        characters=[character],
        campaign_experience={},
        macros=[],
    )
    await user.insert()

    # WHEN calling select_char_trait
    mock_ctx1.options = {"trait_two": "dexterity"}
    result = await autocomplete.select_char_trait_two(mock_ctx1)

    # THEN the trait and its index is returned
    assert len(result) == 1
    assert result[0].name == "Dexterity"
    assert result[0].value == str(trait.id)


@pytest.mark.drop_db()
async def test_select_custom_section(mock_ctx1, character_factory, user_factory):
    """Test the select_custom_section function."""
    # GIVEN a character with a custom section and a user with an active character
    section = CharacterSheetSection(title="mock_section", content="mock_description")
    character = character_factory.build(
        name_first="character",
        name_last="character",
        guild=mock_ctx1.guild.id,
        type_storyteller=True,
        type_player=False,
        type_chargen=False,
        is_alive=True,
        sheet_sections=[section],
        traits=[],
    )
    await character.insert()

    user = user_factory.build(
        id=mock_ctx1.author.id,
        active_characters={str(mock_ctx1.guild.id): character},
        characters=[character],
        campaign_experience={},
        macros=[],
    )
    await user.insert()

    # WHEN calling select_custom_section
    mock_ctx1.value = "mock"
    result = await autocomplete.select_custom_section(mock_ctx1)

    # THEN the section is returned
    assert len(result) == 1
    assert result[0].name == "mock_section"
    assert result[0].value == "0"


@pytest.mark.drop_db()
async def test_select_character_from_user(mock_ctx1, character_factory, user_factory):
    """Test the select_character_from_user function."""
    # GIVEN a user with multiple characters
    character1 = character_factory.build(
        name_first="character1",
        name_last="character1",
        guild=mock_ctx1.guild.id,
        type_storyteller=False,
        type_player=True,
        type_chargen=False,
        is_alive=True,
        traits=[],
    )
    character2 = character_factory.build(
        name_first="character2",
        name_last="character2",
        guild=mock_ctx1.guild.id,
        type_storyteller=True,
        type_player=False,
        type_chargen=False,
        is_alive=True,
        traits=[],
    )
    await character1.insert()
    await character2.insert()

    user = user_factory.build(
        id=mock_ctx1.author.id,
        active_characters={str(mock_ctx1.guild.id): character1},
        characters=[character1, character2],
        campaign_experience={},
        macros=[],
    )
    await user.insert()

    # WHEN calling select_character_from_user
    mock_ctx1.value = "character"
    result = await autocomplete.select_character_from_user(mock_ctx1)

    # THEN the correct result is returned
    assert len(result) == 1
    assert result[0].name == "character1 character1"
    assert result[0].value == str(character1.id)


@pytest.mark.drop_db()
async def test_select_any_player_character(mock_ctx1, character_factory, user_factory):
    """Test the select_any_player_character function."""
    user = user_factory.build(
        id=mock_ctx1.author.id,
        active_characters={},
        characters=[],
        name="mock_user",
    )
    await user.insert()

    character1 = character_factory.build(
        name_first="character1",
        name_last="character1",
        guild=mock_ctx1.guild.id,
        type_storyteller=False,
        type_player=True,
        type_chargen=False,
        is_alive=True,
        traits=[],
        user_owner=user.id,
    )
    character2 = character_factory.build(
        name_first="character2",
        name_last="character2",
        guild=mock_ctx1.guild.id,
        type_storyteller=True,
        type_player=False,
        type_chargen=False,
        is_alive=True,
        traits=[],
        user_owner=user.id,
    )
    character3 = character_factory.build(
        name_first="character3",
        name_last="character3",
        guild=mock_ctx1.guild.id,
        type_storyteller=False,
        type_player=True,
        type_chargen=False,
        is_alive=False,
        traits=[],
        user_owner=user.id,
    )
    await character1.insert()
    await character2.insert()
    await character3.insert()

    # WHEN calling select_any_player_character
    mock_ctx1.value = "character"
    result = await autocomplete.select_any_player_character(mock_ctx1)

    # THEN the correct result is returned
    assert len(result) == 2
    assert result[0].name == "character1 character1 [@mock_user]"
    assert result[0].value == str(character1.id)


@pytest.mark.drop_db()
async def test_select_trait_from_char_option(mock_ctx1, character_factory, trait_factory):
    """Test the select_trait_from_char_option function."""
    trait = trait_factory.build(
        category_name=TraitCategory.PHYSICAL.name, name="Dexterity", value=3, max_value=5
    )
    await trait.insert()
    character = character_factory.build(
        name_first="character",
        name_last="character",
        guild=mock_ctx1.guild.id,
        type_storyteller=True,
        type_player=False,
        type_chargen=False,
        is_alive=True,
        traits=[trait],
    )
    await character.insert()

    # WHEN calling select_trait_from_char_option
    mock_ctx1.options = {"trait": "dexterity", "character": str(character.id)}
    result = await autocomplete.select_trait_from_char_option(mock_ctx1)

    # THEN the trait and its index is returned
    assert len(result) == 1
    assert result[0].name == "Dexterity"
    assert result[0].value == str(trait.id)


@pytest.mark.drop_db()
async def test_select_trait_from_char_option_two(mock_ctx1, character_factory, trait_factory):
    """Test the select_trait_from_char_option_two function."""
    trait = trait_factory.build(
        category_name=TraitCategory.PHYSICAL.name, name="Dexterity", value=3, max_value=5
    )
    await trait.insert()
    character = character_factory.build(
        name_first="character",
        name_last="character",
        guild=mock_ctx1.guild.id,
        type_storyteller=True,
        type_player=False,
        type_chargen=False,
        is_alive=True,
        traits=[trait],
    )
    await character.insert()

    # WHEN calling select_trait_from_char_option
    mock_ctx1.options = {"trait_two": "dexterity", "character": str(character.id)}
    result = await autocomplete.select_trait_from_char_option_two(mock_ctx1)

    # THEN the trait and its index is returned
    assert len(result) == 1
    assert result[0].name == "Dexterity"
    assert result[0].value == str(trait.id)
