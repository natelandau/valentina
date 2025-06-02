"""Representation of a task for the task broker."""

from datetime import datetime

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

from valentina.constants import BrokerTaskType
from valentina.utils.helpers import time_now


class BrokerTask(Document):
    """Representation of a task for the task broker."""

    task: BrokerTaskType
    guild_id: int
    author_name: str = ""
    data: dict = Field(default_factory=dict)
    has_error: bool = False
    date_created: datetime = Field(default_factory=time_now)
    date_modified: datetime = Field(default_factory=time_now)

    @before_event(Insert, Replace, Save, Update, SaveChanges)
    async def update_modified_date(self) -> None:
        """Update the date_modified field."""
        self.date_modified = time_now()

    @before_event(Insert, Replace, Save, Update, SaveChanges)
    async def guild_id_to_int(self) -> None:
        """Ensure the guild_id is an integer."""
        self.guild_id = int(self.guild_id)
