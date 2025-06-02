# type: ignore
"""Test the Guild database model."""

import pytest

from tests.factories import *
from valentina.constants import DICEROLL_THUMBS, RollResultType
from valentina.models import Campaign, GuildRollResultThumbnail
from valentina.utils import errors


async def test_add_roll_result_thumbnail(mock_ctx1, guild_factory):
    """Test the add_roll_result_thumbnail method."""
    # GIVEN a guild
    guild = guild_factory.build()
    await guild.insert()

    # WHEN adding a thumbnail
    await guild.add_roll_result_thumbnail(mock_ctx1, RollResultType.BOTCH, "test_url")

    # THEN the thumbnail is added
    assert guild.roll_result_thumbnails[0].url == "test_url"
    assert guild.roll_result_thumbnails[0].roll_type == RollResultType.BOTCH
    assert guild.roll_result_thumbnails[0].user == mock_ctx1.author.id

    # WHEN adding a thumbnail with the same url
    # THEN raise an error
    with pytest.raises(errors.ValidationError):
        await guild.add_roll_result_thumbnail(mock_ctx1, RollResultType.CRITICAL, "test_url")


@pytest.mark.drop_db
async def test_fetch_diceroll_thumbnail(guild_factory):
    """Test the fetch_diceroll_thumbnail method."""
    # GIVEN a guild
    guild = guild_factory.build()

    # WHEN fetching the diceroll thumbnail before any custom thumbnails are added
    result = await guild.fetch_diceroll_thumbnail(RollResultType.BOTCH)

    # THEN the default thumbnail is returned
    assert result == DICEROLL_THUMBS[RollResultType.BOTCH.name][0]

    # WHEN a custom thumbnail is added
    guild.roll_result_thumbnails = [
        GuildRollResultThumbnail(url="test", roll_type=RollResultType.BOTCH, user=1111),
    ]

    found_new_thumbnail = False
    for _ in range(20):
        # WHEN fetching the diceroll thumbnail
        result = await guild.fetch_diceroll_thumbnail(RollResultType.BOTCH)

        # THEN the custom thumbnail is returned
        if result == "test":
            found_new_thumbnail = True
            break

    assert found_new_thumbnail


@pytest.mark.drop_db
async def test_delete_campaign(campaign_factory, guild_factory):
    """Test the delete_campaign method."""
    # GIVEN a guild with a campaign
    guild = guild_factory.build()
    campaign = campaign_factory.build(guild=guild.id)
    await campaign.insert()

    guild.campaigns.append(campaign)

    # WHEN deleting the campaign
    await guild.delete_campaign(campaign)

    # THEN the active campaign is deleted
    assert guild.campaigns == []
    assert not await Campaign.find(Campaign.is_deleted == False).to_list()  # noqa: E712
    assert campaign.is_deleted
