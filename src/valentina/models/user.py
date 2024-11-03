"""User models for Valentina."""

from datetime import datetime
from typing import cast
from uuid import UUID, uuid4

import discord
from beanie import (
    Document,
    Insert,
    Link,
    Replace,
    Save,
    SaveChanges,
    Update,
    before_event,
)
from pydantic import BaseModel, Field

from valentina.constants import COOL_POINT_VALUE
from valentina.models import Campaign, Character
from valentina.utils import errors
from valentina.utils.helpers import time_now


class CampaignExperience(BaseModel):
    """Dictionary representing a user's campaign experience as a subdocument attached to a User."""

    xp_current: int = 0
    xp_total: int = 0
    cool_points: int = 0


class UserMacro(BaseModel):
    """Represents a user macro as a subdocument within User."""

    abbreviation: str
    date_created: datetime = Field(default_factory=time_now)
    description: str | None = None
    name: str
    trait_one: str | None = None
    trait_two: str | None = None
    uuid: UUID = Field(default_factory=uuid4)


class User(Document):
    """Represent a user in the database and manage user-related data.

    Use this class to create, retrieve, update, and delete user records in the database.
    Store and manage user information such as ID, avatar, characters, campaign experience,
    creation date, macros, name, and associated guilds. Implement methods to handle
    user-specific operations and provide convenient access to user data.
    """

    id: int  # type: ignore [assignment]

    avatar_url: str | None = None
    characters: list[Link[Character]] = Field(default_factory=list)
    campaign_experience: dict[str, CampaignExperience] = Field(default_factory=dict)
    date_created: datetime = Field(default_factory=time_now)
    date_modified: datetime = Field(default_factory=time_now)
    macros: list[UserMacro] = Field(default_factory=list)
    name: str | None = None
    guilds: list[int] = Field(default_factory=list)

    @before_event(Insert, Replace, Save, Update, SaveChanges)
    async def update_modified_date(self) -> None:
        """Update the date_modified field."""
        self.date_modified = time_now()

    @property
    def lifetime_experience(self) -> int:
        """Calculate and return the user's total lifetime experience across all campaigns.

        Sum up the total experience points (XP) accumulated by the user in all campaigns
        they have participated in. This method provides a comprehensive view of the user's
        overall progression and achievements within the system.

        Returns:
            int: The total lifetime experience points of the user.

        Note:
            This property aggregates XP from all campaign experiences stored in the
            user's campaign_experience dictionary.
        """
        xp = 0

        for obj in self.campaign_experience.values():
            xp += obj.xp_total

        return xp

    @property
    def lifetime_cool_points(self) -> int:
        """Calculate and return the user's total lifetime cool points across all campaigns.

        Sum up the cool points accumulated by the user in all campaigns they have
        participated in. This property provides an overview of the user's overall
        achievements and recognition within the system.

        Returns:
            int: The total lifetime cool points of the user.

        Note:
            Aggregate cool points from all campaign experiences stored in the
            user's campaign_experience dictionary.
        """
        cool_points = 0

        for obj in self.campaign_experience.values():
            cool_points += obj.cool_points

        return cool_points

    def _find_campaign_xp(self, campaign: Campaign) -> CampaignExperience | None:
        """Find and return the user's campaign experience for a given campaign.

        Search for the campaign experience associated with the provided campaign
        in the user's campaign_experience dictionary. If found, return the
        CampaignExperience object. If not found, raise a NoExperienceInCampaignError.

        Args:
            campaign (Campaign): The campaign to fetch experience for.

        Returns:
            CampaignExperience: The user's campaign experience for the specified campaign.

        Raises:
            NoExperienceInCampaignError: If no experience is found for the given campaign.
        """
        try:
            return self.campaign_experience[str(campaign.id)]
        except KeyError as e:
            raise errors.NoExperienceInCampaignError from e

    def fetch_campaign_xp(self, campaign: Campaign) -> tuple[int, int, int]:
        """Fetch and return the user's campaign experience for a given campaign.

        Retrieve the user's experience data for the specified campaign. If the user
        has no experience in the campaign, return default values.

        Args:
            campaign (Campaign): The campaign to fetch experience for.

        Returns:
            tuple[int, int, int]: A tuple containing (current XP, total XP, cool points).
                If the user has no experience in the campaign, return (0, 0, 0).

        Note:
            This method handles the NoExperienceInCampaignError internally and
            returns default values instead of raising an exception.
        """
        try:
            campaign_experience = self._find_campaign_xp(campaign)
        except errors.NoExperienceInCampaignError:
            return 0, 0, 0

        return (
            campaign_experience.xp_current,
            campaign_experience.xp_total,
            campaign_experience.cool_points,
        )

    async def spend_campaign_xp(self, campaign: Campaign, amount: int) -> int:
        """Spend experience points for a specific campaign.

        Deduct the specified amount of experience points from the user's current
        experience in the given campaign. Raise an error if there are insufficient
        points to spend.

        Args:
            campaign (Campaign): The campaign for which to spend experience points.
            amount (int): The amount of experience points to spend.

        Returns:
            int: The new current experience points for the campaign after spending.

        Raises:
            errors.NotEnoughExperienceError: If the user doesn't have enough
                experience points to spend the specified amount.
        """
        campaign_experience = self._find_campaign_xp(campaign)

        new_xp = campaign_experience.xp_current - amount

        if new_xp < 0:
            msg = f"Can not spend {amount} xp with only {campaign_experience.xp_current} available"
            raise errors.NotEnoughExperienceError(msg)

        campaign_experience.xp_current = new_xp
        await self.save()

        return new_xp

    async def add_campaign_xp(
        self, campaign: Campaign, amount: int, increase_lifetime: bool = True
    ) -> int:
        """Add experience points to a user's campaign.

        Increase both the current and total experience points for the specified campaign.
        If the user has no prior experience in the campaign, create a new CampaignExperience entry.

        Args:
            campaign (Campaign): The campaign to add experience points for.
            amount (int): The amount of experience points to add.
            increase_lifetime (bool): Whether to increase the user's lifetime experience.

        Returns:
            int: The new current experience points for the campaign after addition.

        Note:
            This method handles the NoExperienceInCampaignError internally by creating
            a new CampaignExperience entry if needed.
        """
        try:
            campaign_experience = self._find_campaign_xp(campaign)
        except errors.NoExperienceInCampaignError:
            campaign_experience = CampaignExperience()
            self.campaign_experience[str(campaign.id)] = campaign_experience

        campaign_experience.xp_current += amount
        if increase_lifetime:
            campaign_experience.xp_total += amount
        await self.save()

        return campaign_experience.xp_current

    async def add_campaign_cool_points(self, campaign: Campaign, amount: int) -> int:
        """Add cool points and increase experience for the specified campaign.

        Add the given amount of cool points to the user's campaign experience.
        Also increase the total and current experience points based on the cool points added.
        If the user has no prior experience in the campaign, create a new CampaignExperience entry.

        Args:
            campaign (Campaign): The campaign to add cool points for.
            amount (int): The amount of cool points to add.

        Returns:
            int: The new total of cool points for the campaign after addition.

        Note:
            This method handles the NoExperienceInCampaignError internally by creating
            a new CampaignExperience entry if needed.
        """
        try:
            campaign_experience = self._find_campaign_xp(campaign)
        except errors.NoExperienceInCampaignError:
            campaign_experience = CampaignExperience()
            self.campaign_experience[str(campaign.id)] = campaign_experience

        campaign_experience.cool_points += amount
        campaign_experience.xp_total += amount * COOL_POINT_VALUE
        campaign_experience.xp_current += amount * COOL_POINT_VALUE
        await self.save()

        return campaign_experience.cool_points

    def all_characters(self, guild: discord.Guild) -> list[Character]:
        """Retrieve all characters belonging to the user in the specified guild.

        This method filters the user's characters based on the given guild ID.

        Args:
            guild (discord.Guild): The Discord guild to filter characters by.

        Returns:
            list[Character]: A list of Character objects associated with the user
            and the specified guild.
        """
        return [x for x in cast(list[Character], self.characters) if x.guild == guild.id]

    async def remove_character(self, character: Character) -> None:
        """Remove a character from the user's list of characters.

        Remove the specified character from the user's list of characters and save the updated user data.

        Args:
            character (Character): The character to be removed from the user's list.

        Returns:
            None
        """
        # Remove the character from the list of characters
        self.characters = [x for x in self.characters if x.id != character.id]  # type: ignore [attr-defined]

        await self.save()
