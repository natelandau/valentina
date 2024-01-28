"""Campaign models for Valentina."""

from datetime import datetime
from typing import Optional

from beanie import (
    Document,
    Insert,
    Replace,
    Save,
    SaveChanges,
    Update,
    before_event,
)
from pydantic import BaseModel, Field

from valentina.utils.helpers import time_now


class CampaignChapter(BaseModel):
    """Represents a chapter as a subdocument within Campaign."""

    description_long: str = None
    description_short: str = None
    name: str
    number: int
    date_created: datetime = Field(default_factory=time_now)

    def campaign_display(self) -> str:
        """Return the display for campaign overview."""
        display = f"**{self.number}: __{self.name}__**"
        display += f"\n{self.description_long}" if self.description_long else ""

        return display


class CampaignNPC(BaseModel):
    """Represents a campaign NPC as a subdocument within Campaign."""

    description: str
    name: str
    npc_class: str

    def campaign_display(self) -> str:
        """Return the display for campaign overview."""
        display = f"**{self.name}**"
        display += f" ({self.npc_class})" if self.npc_class else ""
        display += f"\n{self.description}" if self.description else ""

        return display


class CampaignNote(BaseModel):
    """Represents a campaign note as a subdocument within Campaign."""

    # TODO: Remove user-specific notes from cogs/views
    description: str
    name: str

    def campaign_display(self) -> str:
        """Return the display for campaign overview."""
        display = f"**{self.name}**\n"
        display += f"{self.description}" if self.description else ""

        return display


class Campaign(Document):
    """Represents a campaign in the database."""

    date_created: datetime = Field(default_factory=time_now)
    date_modified: datetime = Field(default_factory=time_now)
    date_in_game: Optional[datetime] = None
    description: str | None = None
    desperation: int = 0
    danger: int = 0
    guild: int
    name: str
    chapters: list[CampaignChapter] = Field(default_factory=list)
    notes: list[CampaignNote] = Field(default_factory=list)
    npcs: list[CampaignNPC] = Field(default_factory=list)

    @before_event(Insert, Replace, Save, Update, SaveChanges)
    async def update_modified_date(self) -> None:
        """Update the date_modified field."""
        self.date_modified = time_now()
