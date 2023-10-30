# type: ignore
"""Test the Guild database model."""
import pytest

from valentina.models.mongo_collections import Campaign
from valentina.utils import errors


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


async def test_delete_campagin(create_guild, create_campaign):
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
