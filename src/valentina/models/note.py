"""Model representing a note."""

from datetime import datetime
from typing import TYPE_CHECKING

import discord
from beanie import (
    Document,
    Insert,
    Replace,
    Save,
    SaveChanges,
    Update,
    before_event,
)
from pydantic import Field

from valentina.utils.helpers import time_now

if TYPE_CHECKING:
    from valentina.models.bot import ValentinaContext


class Note(Document):
    """Model representing a note."""

    created_by: int  # user_id
    date_created: datetime = Field(default_factory=time_now)
    date_modified: datetime = Field(default_factory=time_now)
    text: str
    parent_id: str  # campaign_id, book_id, or character_id

    @before_event(Insert, Replace, Save, Update, SaveChanges)  # pragma: no cover
    async def update_modified_date(self) -> None:
        """Update the date_modified field."""
        self.date_modified = time_now()

    async def display(self, ctx: "ValentinaContext") -> str:
        """Display the note."""
        creator = discord.utils.get(ctx.bot.users, id=self.created_by)

        return f"{self.text.capitalize()} _`@{creator.display_name if creator else 'Unknown'}`_"
