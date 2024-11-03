"""Constants for the web UI."""

from dataclasses import dataclass
from enum import Enum
from typing import Union


@dataclass
class EditItem:
    """Class for an item that can be edited."""

    name: str
    route: str
    div_id: str
    tab: Union["CharacterViewTab", "CampaignViewTab"]

    @property
    def route_suffix(self) -> str:
        """Get just the suffix of the route. This is used in blueprints because the suffix is the view name and the prefix is the blueprint name."""
        # return the last part of the route which is two words separated by a dot
        return self.route.split(".")[1]


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


class CampaignViewTab(Enum):
    """Enum for the tabs of the campaign view."""

    OVERVIEW = "overview"
    BOOKS = "books"
    CHARACTERS = "characters"
    NOTES = "notes"
    STATISTICS = "statistics"

    @classmethod
    def get_member_by_value(cls, value: str) -> "CampaignViewTab":
        """Get a member of the enum by its value."""
        return cls[value.upper()]


class UserEditableInfo(Enum):
    """Enum for the editable info of a user. Used to build blueprint routes and template variables."""

    MACRO = EditItem(name="macro", route="user_profile.edit_macro", div_id="macro", tab=None)


class CampaignEditableInfo(Enum):
    """Enum for the editable info of a campaign. Used to build blueprint routes and template variables."""

    DESCRIPTION = EditItem(
        name="description",
        route="campaign.edit_description",
        div_id="description",
        tab=CampaignViewTab.OVERVIEW,
    )
    BOOK = EditItem(
        name="book", route="campaign.edit_book", div_id="book", tab=CampaignViewTab.BOOKS
    )
    CHAPTER = EditItem(
        name="chapter", route="campaign.edit_chapter", div_id="chapter", tab=CampaignViewTab.BOOKS
    )
    NOTE = EditItem(
        name="note", route="campaign.edit_note", div_id="note", tab=CampaignViewTab.NOTES
    )
    NPC = EditItem(
        name="npc", route="campaign.edit_npc", div_id="npc", tab=CampaignViewTab.CHARACTERS
    )


class CharacterEditableInfo(Enum):
    """Enum for the editable info of a character. Used to build blueprint routes and template variables."""

    NOTE = EditItem(
        name="note", route="character_edit.edit_note", div_id="note", tab=CharacterViewTab.INFO
    )
    CUSTOM_SECTION = EditItem(
        name="customsection",
        route="character_edit.edit_customsection",
        div_id="customsection",
        tab=CharacterViewTab.INFO,
    )
    INVENTORY = EditItem(
        name="inventory",
        route="character_edit.edit_inventory",
        div_id="inventory",
        tab=CharacterViewTab.INFO,
    )
    BIOGRAPHY = EditItem(
        name="biography",
        route="character_edit.edit_biography",
        div_id="biography",
        tab=CharacterViewTab.BIOGRAPHY,
    )
    DELETE = EditItem(
        name="delete",
        route="character_edit.delete_character",
        div_id="main-content",
        tab=CharacterViewTab.SHEET,
    )
