"""Constants for the web UI."""

from enum import Enum


class CharacterViewTab(Enum):
    """Enum for the tabs of the character view."""

    SHEET = "sheet"
    BIOGRAPHY = "biography"
    INFO = "info"
    IMAGES = "images"
    STATISTICS = "statistics"

    @classmethod
    def get_member_by_value(cls, value: str) -> "CharacterViewTab":
        """Get a member of the enum by its value."""
        return cls[value.upper()]


class CharacterEditableInfo(Enum):
    """Enum for the editable info of a character. Used to build blueprint routes and template variables."""

    NOTE = "note"
    CUSTOM_SECTION = "customsection"
    INVENTORY = "inventory"

    @classmethod
    def get_member_by_value(cls, value: str) -> "CharacterEditableInfo":
        """Get a member of the enum by its value."""
        return cls[value.upper()]
