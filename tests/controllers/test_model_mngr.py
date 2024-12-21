# type: ignore
"""Test the model manager."""

import pytest

from tests.factories import *
from valentina.controllers import delete_character
from valentina.models import Character


@pytest.mark.skip(reason="Skipping until we have a way to mock the import of bot")
@pytest.mark.drop_db
async def test_delete_character(debug, user_factory, character_factory, guild_factory):
    """Test the delete character function."""
    # GIVEN a guild with two characters and a user who owns both characters
    guild = guild_factory.build()
    await guild.insert()

    character1 = character_factory.build(guild=guild.id, channel=None, images=[])
    await character1.insert()

    character2 = character_factory.build(guild=guild.id, channel=None, images=[])
    await character2.insert()

    user = user_factory.build(guilds=[guild.id], characters=[character1, character2])
    await user.insert()

    character1.user_creator = user.id
    character1.user_owner = user.id
    await character1.save()

    character2.user_creator = user.id
    character2.user_owner = user.id
    await character2.save()

    # WHEN deleting one of the characters
    await delete_character(character1)
    refreshed_user = await User.get(user.id, fetch_links=True)

    # THEN only that character is deleted and removed from the user's character list
    assert character1 not in await Character.find_all().to_list()
    assert character2 in await Character.find_all().to_list()

    assert len(refreshed_user.characters) == 1
    assert refreshed_user.characters[0].id == character2.id
