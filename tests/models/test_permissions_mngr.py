# type: ignore
"""Tests for the permissions manager model."""

from datetime import UTC, datetime, timedelta

import pytest

from tests.factories import *
from valentina.constants import (
    PermissionManageCampaign,
    PermissionsGrantXP,
    PermissionsKillCharacter,
    PermissionsManageTraits,
)
from valentina.models import PermissionManager
from valentina.models.guild import GuildPermissions


@pytest.mark.parametrize(
    (
        "is_admin",
        "is_storyteller",
        "grant_xp_setting",
        "expected_other",
        "expected_self",
    ),
    [
        (False, False, PermissionsGrantXP.STORYTELLER_ONLY, False, False),
        (False, True, PermissionsGrantXP.STORYTELLER_ONLY, True, True),
        (True, False, PermissionsGrantXP.STORYTELLER_ONLY, True, True),
        (False, False, PermissionsGrantXP.UNRESTRICTED, True, True),
        (False, True, PermissionsGrantXP.UNRESTRICTED, True, True),
        (True, False, PermissionsGrantXP.UNRESTRICTED, True, True),
        (False, False, PermissionsGrantXP.PLAYER_ONLY, False, True),
        (False, True, PermissionsGrantXP.PLAYER_ONLY, True, True),
        (True, False, PermissionsGrantXP.PLAYER_ONLY, True, True),
    ],
)
@pytest.mark.drop_db
async def test_grant_xp(
    guild_factory,
    user_factory,
    is_admin,
    is_storyteller,
    grant_xp_setting,
    expected_other,
    expected_self,
    debug,
) -> None:
    """Test permissions for granting XP."""
    guild = guild_factory.build()
    user1 = user_factory.build()
    user2 = user_factory.build()

    guild.permissions = GuildPermissions(grant_xp=grant_xp_setting)

    if is_admin:
        guild.administrators.append(user1.id)
    if is_storyteller:
        guild.storytellers.append(user1.id)
    await guild.insert()

    # debug("guild", guild)

    manager = PermissionManager(guild.id)
    assert await manager.can_grant_xp(author_id=user1.id, target_id=user2.id) == expected_other
    assert await manager.can_grant_xp(author_id=user1.id, target_id=user1.id) == expected_self


@pytest.mark.parametrize(
    (
        "is_admin",
        "is_storyteller",
        "setting",
        "expected",
    ),
    [
        (False, False, PermissionManageCampaign.UNRESTRICTED, True),
        (False, True, PermissionManageCampaign.UNRESTRICTED, True),
        (True, False, PermissionManageCampaign.UNRESTRICTED, True),
        (False, False, PermissionManageCampaign.STORYTELLER_ONLY, False),
        (False, True, PermissionManageCampaign.STORYTELLER_ONLY, True),
        (True, False, PermissionManageCampaign.STORYTELLER_ONLY, True),
    ],
)
@pytest.mark.drop_db
async def test_manage_campaigns(
    guild_factory,
    user_factory,
    is_admin,
    is_storyteller,
    setting,
    expected,
    debug,
) -> None:
    """Test permissions for managing campaigns."""
    guild = guild_factory.build()
    user1 = user_factory.build()

    guild.permissions = GuildPermissions(manage_campaigns=setting)

    if is_admin:
        guild.administrators.append(user1.id)
    if is_storyteller:
        guild.storytellers.append(user1.id)
    await guild.insert()

    # debug("guild", guild)

    manager = PermissionManager(guild.id)
    assert await manager.can_manage_campaign(author_id=user1.id) == expected


@pytest.mark.parametrize(
    (
        "is_old_char",
        "is_character_owner",
        "is_admin",
        "is_storyteller",
        "setting",
        "expected",
    ),
    [
        (False, False, False, False, PermissionsManageTraits.UNRESTRICTED, True),
        (True, False, False, False, PermissionsManageTraits.UNRESTRICTED, True),
        (True, True, False, False, PermissionsManageTraits.UNRESTRICTED, True),
        (False, True, False, False, PermissionsManageTraits.UNRESTRICTED, True),
        (False, False, True, False, PermissionsManageTraits.UNRESTRICTED, True),
        (False, False, False, True, PermissionsManageTraits.UNRESTRICTED, True),
        (False, False, False, False, PermissionsManageTraits.CHARACTER_OWNER_ONLY, False),
        (True, False, False, False, PermissionsManageTraits.CHARACTER_OWNER_ONLY, False),
        (True, True, False, False, PermissionsManageTraits.CHARACTER_OWNER_ONLY, True),
        (False, True, False, False, PermissionsManageTraits.CHARACTER_OWNER_ONLY, True),
        (False, False, True, False, PermissionsManageTraits.CHARACTER_OWNER_ONLY, True),
        (False, False, False, True, PermissionsManageTraits.CHARACTER_OWNER_ONLY, True),
        (False, False, False, False, PermissionsManageTraits.WITHIN_24_HOURS, False),
        (True, False, False, False, PermissionsManageTraits.WITHIN_24_HOURS, False),
        (True, True, False, False, PermissionsManageTraits.WITHIN_24_HOURS, False),
        (False, True, False, False, PermissionsManageTraits.WITHIN_24_HOURS, True),
        (False, False, True, False, PermissionsManageTraits.WITHIN_24_HOURS, True),
        (False, False, False, True, PermissionsManageTraits.WITHIN_24_HOURS, True),
        (True, False, False, True, PermissionsManageTraits.WITHIN_24_HOURS, True),
        (False, False, False, False, PermissionsManageTraits.STORYTELLER_ONLY, False),
        (True, False, False, False, PermissionsManageTraits.STORYTELLER_ONLY, False),
        (True, True, False, False, PermissionsManageTraits.STORYTELLER_ONLY, False),
        (False, True, False, False, PermissionsManageTraits.STORYTELLER_ONLY, False),
        (False, False, True, False, PermissionsManageTraits.STORYTELLER_ONLY, True),
        (False, False, False, True, PermissionsManageTraits.STORYTELLER_ONLY, True),
    ],
)
@pytest.mark.drop_db
async def test_manage_traits(
    guild_factory,
    user_factory,
    character_factory,
    is_old_char,
    is_character_owner,
    is_admin,
    is_storyteller,
    setting,
    expected,
    debug,
) -> None:
    """Test permissions for managing traits."""
    guild = guild_factory.build()
    user1 = user_factory.build()

    if is_old_char and is_character_owner:
        character = character_factory.build(
            user_owner=user1.id, date_created=datetime.now(UTC) - timedelta(days=2)
        )
    elif is_old_char:
        character = character_factory.build(date_created=datetime.now(UTC) - timedelta(days=2))
    elif is_character_owner:
        character = character_factory.build(user_owner=user1.id, date_created=datetime.now(UTC))
    else:
        character = character_factory.build(date_created=datetime.now(UTC))

    await character.insert()

    # debug("character", character)

    guild.permissions = GuildPermissions(manage_traits=setting)

    if is_admin:
        guild.administrators.append(user1.id)
    if is_storyteller:
        guild.storytellers.append(user1.id)
    await guild.insert()

    # debug("guild", guild)

    manager = PermissionManager(guild.id)
    assert (
        await manager.can_manage_traits(author_id=user1.id, character_id=character.id) == expected
    )


@pytest.mark.parametrize(
    (
        "is_char_owner",
        "is_admin",
        "is_storyteller",
        "setting",
        "expected",
    ),
    [
        (False, False, False, PermissionsKillCharacter.UNRESTRICTED, True),
        (True, False, False, PermissionsKillCharacter.UNRESTRICTED, True),
        (False, False, True, PermissionsKillCharacter.UNRESTRICTED, True),
        (False, True, False, PermissionsKillCharacter.UNRESTRICTED, True),
        (False, False, False, PermissionsKillCharacter.CHARACTER_OWNER_ONLY, False),
        (True, False, False, PermissionsKillCharacter.CHARACTER_OWNER_ONLY, True),
        (False, False, True, PermissionsKillCharacter.CHARACTER_OWNER_ONLY, True),
        (False, True, False, PermissionsKillCharacter.CHARACTER_OWNER_ONLY, True),
        (False, False, False, PermissionsKillCharacter.STORYTELLER_ONLY, False),
        (True, False, False, PermissionsKillCharacter.STORYTELLER_ONLY, False),
        (False, False, True, PermissionsKillCharacter.STORYTELLER_ONLY, True),
        (False, True, False, PermissionsKillCharacter.STORYTELLER_ONLY, True),
    ],
)
@pytest.mark.drop_db
async def test_can_kill_character(
    guild_factory,
    user_factory,
    character_factory,
    is_char_owner,
    is_admin,
    is_storyteller,
    setting,
    expected,
    debug,
) -> None:
    """Test permissions for killing characters."""
    guild = guild_factory.build()
    user1 = user_factory.build()

    if is_char_owner:
        character = character_factory.build(user_owner=user1.id)
    else:
        character = character_factory.build()

    await character.insert()

    guild.permissions = GuildPermissions(kill_character=setting)
    if is_admin:
        guild.administrators.append(user1.id)
    if is_storyteller:
        guild.storytellers.append(user1.id)
    await guild.insert()

    # debug("guild", guild)

    manager = PermissionManager(guild.id)
    assert (
        await manager.can_kill_character(author_id=user1.id, character_id=character.id) == expected
    )
