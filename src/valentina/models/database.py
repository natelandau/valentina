"""MongoDB collections for Valentina."""

from datetime import datetime

import semver
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


class GlobalProperty(Document):
    """Represents global properties in the database."""

    versions: list[str] = Field(default_factory=list)
    last_update: datetime = Field(default_factory=time_now)

    @before_event(Insert, Replace, Save, Update, SaveChanges)
    async def update_last_update(self) -> None:
        """Update the last_update field."""
        self.last_update = time_now()

    @property
    def most_recent_version(self) -> str:
        """Return the most recent version."""
        return max(self.versions, key=semver.Version.parse)
