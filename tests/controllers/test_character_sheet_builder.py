# type: ignore
"""Tests for the character sheet builder."""

import pytest

from tests.factories import *
from valentina.constants import CharClass, CharSheetSection, TraitCategory
from valentina.controllers import CharacterSheetBuilder


@pytest.mark.drop_db
async def test_fetch_sheet_data(debug, trait_factory, character_factory):
    """Test the fetch_sheet_data method."""
    char_class = CharClass.WEREWOLF
    character = character_factory.build(char_class=char_class.name)
    await character.insert()

    # for section in CharSheetSection.get_members_in_order():
    for cat in TraitCategory.get_members_in_order():
        for trait_name in cat.get_all_class_trait_names(char_class=char_class):
            await character.add_trait(category=cat, name=trait_name, value=1, max_value=5)

    sheet_builder = CharacterSheetBuilder(character=character)
    sheet_data = sheet_builder.fetch_sheet_data(show_zeros=False)

    # debug("sheet_data", sheet_data)

    assert len(sheet_data) == 3

    assert sheet_data[0].section == CharSheetSection.ATTRIBUTES
    assert len(sheet_data[0].category) == 3
    assert sheet_data[0].category[0].category == TraitCategory.PHYSICAL
    assert len(sheet_data[0].category[0].traits) == 3

    assert sheet_data[1].section == CharSheetSection.ABILITIES
    assert len(sheet_data[1].category) == 3
    assert sheet_data[1].category[0].category == TraitCategory.TALENTS
    assert len(sheet_data[1].category[0].traits) == 11

    assert sheet_data[2].section == CharSheetSection.ADVANTAGES
    assert len(sheet_data[2].category) == 3
    assert sheet_data[2].category[0].category == TraitCategory.BACKGROUNDS
    assert len(sheet_data[2].category[0].traits) == 17
