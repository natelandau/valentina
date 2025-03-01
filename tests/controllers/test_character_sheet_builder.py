# type: ignore
"""Tests for the character sheet builder."""

import pytest

from tests.factories import *
from valentina.constants import CharClass, CharSheetSection, TraitCategory
from valentina.controllers import CharacterSheetBuilder
from valentina.models import CharacterTrait


@pytest.mark.drop_db
async def test_fetch_sheet_character_traits(debug, trait_factory, character_factory):
    """Test the fetch_sheet_character_traits method."""
    char_class = CharClass.WEREWOLF
    character = character_factory.build(char_class=char_class.name)
    await character.insert()

    # for section in CharSheetSection.get_members_in_order():
    for cat in TraitCategory.get_members_in_order():
        for trait_name in cat.get_all_class_trait_names(char_class=char_class):
            await character.add_trait(
                CharacterTrait(
                    name=trait_name,
                    category_name=cat.name,
                    value=1,
                    max_value=5,
                    character=str(character.id),
                )
            )

    sheet_builder = CharacterSheetBuilder(character=character)
    sheet_data = sheet_builder.fetch_sheet_character_traits(show_zeros=False)

    # debug("sheet_data", sheet_data)

    assert len(sheet_data) == 3

    assert sheet_data[0].section == CharSheetSection.ATTRIBUTES
    assert len(sheet_data[0].categories) == 3
    assert sheet_data[0].categories[0].category == TraitCategory.PHYSICAL
    assert len(sheet_data[0].categories[0].traits) == 3

    assert sheet_data[1].section == CharSheetSection.ABILITIES
    assert len(sheet_data[1].categories) == 3
    assert sheet_data[1].categories[0].category == TraitCategory.TALENTS
    assert len(sheet_data[1].categories[0].traits) == 11

    assert sheet_data[2].section == CharSheetSection.ADVANTAGES
    assert len(sheet_data[2].categories) == 3
    assert sheet_data[2].categories[0].category == TraitCategory.BACKGROUNDS
    assert len(sheet_data[2].categories[0].traits) == 17


@pytest.mark.parametrize(
    ("char_class", "keys"),
    [
        (CharClass.MAGE, ["tradition", "essence"]),
        (CharClass.VAMPIRE, ["generation", "sire", "clan"]),
        (CharClass.WEREWOLF, ["tribe", "auspice", "breed"]),
    ],
)
@pytest.mark.drop_db
async def test_fetch_sheet_profile(
    debug, character_factory, campaign_factory, user_factory, char_class, keys
):
    """Test the fetch_sheet_profile method."""
    campaign = await campaign_factory.build().insert()
    user = user_factory.build(name="test_user")
    await user.insert()
    character = character_factory.build(
        user_owner=user.id,
        char_class_name=char_class.name,
        type_player=True,
        campaign=str(campaign.id),
    )
    await character.insert()

    common_profile_keys = ["class", "alive", "concept", "demeanor", "nature", "owner"]
    storyteller_keys = ["character type"]

    # When checking for the player view
    sheet_builder = CharacterSheetBuilder(character=character)
    sheet_profile = await sheet_builder.fetch_sheet_profile()

    # Then the profile should contain the expected keys
    for key in keys + common_profile_keys:
        assert key.title() in sheet_profile

    for key in storyteller_keys:
        assert key.title() not in sheet_profile

    # When checking for the storyteller view
    storyteller_sheet_profile = await sheet_builder.fetch_sheet_profile(storyteller_view=True)

    # Then the profile should contain the expected keys
    for key in keys + common_profile_keys + storyteller_keys:
        assert key.title() in storyteller_sheet_profile

    assert storyteller_sheet_profile["Owner"] == "Test User"


def test_fetch_all_class_traits(debug, character_factory) -> None:
    """Test the fetch_all_class_traits method."""
    character = character_factory.build(char_class_name=CharClass.WEREWOLF.name)
    sheet_builder = CharacterSheetBuilder(character=character)
    sheet_data = sheet_builder.fetch_all_class_traits()

    assert len(sheet_data) == 3
    assert sheet_data[0].section == CharSheetSection.ATTRIBUTES
    assert sheet_data[0].categories[0].category == TraitCategory.PHYSICAL
    for trait in sheet_data[0].categories[0].traits_for_creation:
        assert trait.max_value == 5
        assert trait.category == TraitCategory.PHYSICAL
        assert trait.name in TraitCategory.PHYSICAL.get_all_class_trait_names(
            char_class=CharClass.WEREWOLF
        )

    assert sheet_data[2].section == CharSheetSection.ADVANTAGES
    assert sheet_data[2].categories[0].category == TraitCategory.BACKGROUNDS
    for background in ["Resources", "Contacts", "Allies", "Retainers", "Influence", "Pure Breed"]:
        assert background in [x.name for x in sheet_data[2].categories[0].traits_for_creation]

    unorganized_traits = sheet_builder.fetch_all_class_traits_unorganized()
    assert len(unorganized_traits) == 70
