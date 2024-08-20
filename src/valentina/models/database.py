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
    """Represent global properties in the database.

    Use this class to store and manage global configuration settings and properties
    that are applicable across the entire application. These properties may include
    version information, system-wide settings, or any other data that needs to be
    globally accessible.
    """

    versions: list[str] = Field(default_factory=list)
    last_update: datetime = Field(default_factory=time_now)

    @before_event(Insert, Replace, Save, Update, SaveChanges)
    async def update_last_update(self) -> None:
        """Update the last_update field with the current timestamp.

        This method is automatically called before insert, replace, save, update,
        and save changes events. It ensures that the last_update field always
        reflects the most recent modification time of the GlobalProperty document.

        The time_now() function is used to get the current timestamp in a
        consistent format across the application.
        """
        self.last_update = time_now()

    @property
    def most_recent_version(self) -> str:
        """Return the most recent version from the list of versions.

        Determine and return the highest semantic version from the versions list.
        If the list is empty, return '0.0.0' as the default version.

        Returns:
            str: The most recent version string.
        """
        if len(self.versions) == 0:
            return "0.0.0"

        return max(self.versions, key=semver.Version.parse)
