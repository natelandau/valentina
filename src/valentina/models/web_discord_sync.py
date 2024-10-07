"""Database model to store objects which need to be synced between the webui and Discord.

Discord has no concept of a session object and the webui has no concept of a discord ctx object. This model stores objects which need to be synced between the two.
"""

from datetime import datetime
from typing import Literal

from beanie import Document
from pydantic import Field, field_validator

from valentina.constants import DBSyncModelType, DBSyncUpdateType
from valentina.utils.helpers import time_now


class WebDiscordSync(Document):
    """Model to store objects which need to be synced between the webui and Discord.

    Attributes:
        date_created (datetime): The date the object was created.
        object_id (str): The ID of the object to sync.
        object_type (DBSyncModelType): The type of object to sync.
        update_type (DBSyncUpdateType): The type of update to perform.
        target (Literal["web", "discord"]): The target to sync the object to.
        date_processed (datetime | None): The date the object was processed.
        processed (bool): Whether the object has been processed.
    """

    date_created: datetime = Field(default_factory=time_now)
    date_processed: datetime | None = None
    guild_id: int
    object_id: str
    object_type: DBSyncModelType
    processed: bool = False
    target: Literal["web", "discord"]
    update_type: DBSyncUpdateType
    user_id: int

    @field_validator("guild_id")
    @classmethod
    def guild_id_to_int(cls, v: str | int) -> int:
        """Validate that the guiid id is an integer."""
        return int(v)

    @field_validator("user_id")
    @classmethod
    def user_id_to_int(cls, v: str | int) -> int:
        """Validate that the user id is an integer."""
        return int(v)

    async def mark_processed(self) -> None:
        """Mark the object as processed."""
        self.processed = True
        self.date_processed = time_now()
        await self.save()
