# type: ignore
"""Test the Guild database model."""
import pytest

from valentina.constants import DICEROLL_THUMBS, RollResultType
from valentina.models import Campaign, GuildRollResultThumbnail
from valentina.utils import errors


async def test_add_roll_result_thumbnail(create_guild, mock_ctx1):
    """Test the add_roll_result_thumbnail method."""
    # GIVEN a guild
    guild = await create_guild()

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


async def test_fetch_diceroll_thumbnail(create_guild):
    """Test the fetch_diceroll_thumbnail method."""
    # GIVEN a guild
    guild = await create_guild()

    # WHEN fetching the diceroll thumbnail before any custom thumbnails are added
    result = await guild.fetch_diceroll_thumbnail(RollResultType.BOTCH)

    # THEN the default thumbnail is returned
    assert result == DICEROLL_THUMBS[RollResultType.BOTCH.name][0]

    # WHEN a custom thumbnail is added
    guild.roll_result_thumbnails = [
        GuildRollResultThumbnail(url="test", roll_type=RollResultType.BOTCH, user=1111)
    ]
    await guild.save()

    found_new_thumbnail = False
    for _ in range(20):
        # WHEN fetching the diceroll thumbnail
        result = await guild.fetch_diceroll_thumbnail(RollResultType.BOTCH)

        # THEN the custom thumbnail is returned
        if result == "test":
            found_new_thumbnail = True
            break

    assert found_new_thumbnail


async def test_fetch_active_campaign(create_guild, create_campaign):
    """Test the fetch_active_campaign method."""
    # GIVEN a guild with a campaign
    guild = await create_guild()
    campaign = await create_campaign(guild=guild.id)

    # WHEN fetching the active campaign before it is set
    # THEN a NoActiveCampaignError is raised
    with pytest.raises(errors.NoActiveCampaignError):
        active_campaign = await guild.fetch_active_campaign()

    # GIVEN an active campaign
    guild.active_campaign = campaign
    await guild.save()

    # WHEN fetching the active campaign
    active_campaign = await guild.fetch_active_campaign()

    # THEN the correct campaign is returned
    assert active_campaign == campaign


async def test_delete_campaign(create_guild, create_campaign):
    """Test the delete_campaign method."""
    # GIVEN a guild with a campaign
    guild = await create_guild()
    campaign = await create_campaign(guild=guild.id)
    guild.campaigns.append(campaign)
    guild.active_campaign = campaign
    await guild.save()

    # WHEN deleting the campaign
    await guild.delete_campaign(campaign)

    # THEN the active campaign is deleted
    assert guild.active_campaign is None
    assert guild.campaigns == []
    assert not await Campaign.find_all().to_list()
