"""User models for Valentina."""

from datetime import datetime
from typing import cast

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


class User(Document):
    """Represents a user in the database."""

    id: int  # type: ignore [assignment]

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
        """Return the user's lifetime experience level."""
        xp = 0

        for obj in self.campaign_experience.values():
            xp += obj.xp_total

        return xp

    @property
    def lifetime_cool_points(self) -> int:
        """Return the user's lifetime cool points."""
        cool_points = 0

        for obj in self.campaign_experience.values():
            cool_points += obj.cool_points

        return cool_points

    def _find_campaign_xp(self, campaign: Campaign) -> CampaignExperience | None:
        """Return the user's campaign experience for a given campaign.

        Args:
            campaign (Campaign): The campaign to fetch experience for.

        Returns:
            CampaignExperience|None: The user's campaign experience if it exists; otherwise, None.
        """
        try:
            return self.campaign_experience[str(campaign.id)]
        except KeyError as e:
            raise errors.NoExperienceInCampaignError from e

    def fetch_campaign_xp(self, campaign: Campaign) -> tuple[int, int, int]:
        """Return the user's campaign experience for a given campaign.

        Args:
            campaign (Campaign): The campaign to fetch experience for.

        Returns:
            tuple[int, int, int]: Tuple of (current xp, total xp, cool points) if the user has experience for the campaign; otherwise, None.
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
        """Spend experience for a campaign.

        Args:
            campaign (Campaign): The campaign to spend experience for.
            amount (int): The amount of experience to spend.

        Returns:
            int: The new campaign experience.
        """
        campaign_experience = self._find_campaign_xp(campaign)

        new_xp = campaign_experience.xp_current - amount

        if new_xp < 0:
            msg = f"Can not spend {amount} xp with only {campaign_experience.xp_current} available"
            raise errors.NotEnoughExperienceError(msg)

        campaign_experience.xp_current = new_xp
        await self.save()

        return new_xp

    async def add_campaign_xp(self, campaign: Campaign, amount: int) -> int:
        """Add experience for a campaign.

        Args:
            campaign (Campaign): The campaign to add experience for.
            amount (int): The amount of experience to add.

        Returns:
            int: The new campaign experience.
        """
        try:
            campaign_experience = self._find_campaign_xp(campaign)
        except errors.NoExperienceInCampaignError:
            campaign_experience = CampaignExperience()
            self.campaign_experience[str(campaign.id)] = campaign_experience

        campaign_experience.xp_current += amount
        campaign_experience.xp_total += amount
        await self.save()

        return campaign_experience.xp_current

    async def add_campaign_cool_points(self, campaign: Campaign, amount: int) -> int:
        """Add cool points and increase experience for the current campaign.

        Args:
            campaign (Campaign): The campaign to add cool points for.
            amount (int): The amount of cool points to add.

        Returns:
            int: The new campaign cool points.
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
        """Return all characters for the user in the guild."""
        return [x for x in cast(list[Character], self.characters) if x.guild == guild.id]

    async def remove_character(self, character: Character) -> None:
        """Remove a character from the user's list of characters."""
        # Remove the character from the list of characters
        self.characters = [x for x in self.characters if x.id != character.id]  # type: ignore [attr-defined]

        await self.save()
