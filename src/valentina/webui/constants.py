"""Constants for the web UI."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Union


class CharCreateType(Enum):
    """Enum for the type of character creation."""

    STORYTELLER = "storyteller"
    PLAYER = "player"


@dataclass
class EditableItem:
    """Class for an item that can be edited.

    name: The name of the item.
    route: The route to the page that displays the item.
    sort_attribute: The attribute to sort the item by.
    description: The description of the item.
    table_headers: The headers of the table that displays the item.
    item_name: Used to describe the type of item in the table if different from the name.
    """

    name: str
    route: str
    sort_attribute: str = ""
    description: str = ""
    table_headers: list[str] = field(default_factory=list)
    item_name: str = ""

    @property
    def route_suffix(self) -> str:
        """Get just the suffix of the route. This is used in blueprints because the suffix is the view name and the prefix is the blueprint name."""
        # return the last part of the route which is two words separated by a dot (e.g. test.view -> view)
        return self.route.split(".")[1]


class TextType(Enum):
    """Enum for the type of text."""

    BIOGRAPHY = EditableItem(name="Biography", route="partials.text_biography")
    CAMPAIGN_DESCRIPTION = EditableItem(
        name="Description",
        route="partials.text_campaign_description",
    )


class TableType(Enum):
    """Enum for the type of table."""

    NOTE = EditableItem(
        name="Notes",
        route="partials.table_note",
        description="Jot down quick and dirty notes",
        sort_attribute="text",
    )
    INVENTORYITEM = EditableItem(
        name="Inventory Items",
        route="partials.table_inventory",
        description="Items the character owns",
        sort_attribute="type,name",
        table_headers=["Item", "Category", "Description"],
    )
    NPC = EditableItem(
        name="NPCs",
        route="partials.table_npc",
        description="Quick reference to campaign NPCs",
        sort_attribute="name",
        table_headers=["Name", "Class", "Description"],
    )
    MACRO = EditableItem(
        name="Macros",
        route="partials.table_macro",
        description="Speed dice rolling by preselecting traits",
        table_headers=["Name", "Abbreviation", "Description", "Trait1", "Trait2"],
        sort_attribute="name",
    )
    CHAPTER = EditableItem(
        name="Chapters",
        route="partials.table_chapter",
        description="Chapters of the campaign book",
        table_headers=["#", "Chapter", "Description"],
        sort_attribute="number",
    )
    DICTIONARY = EditableItem(
        name="Dictionary",
        route="partials.table_dictionary",
        description="Terms in the dictionary",
        sort_attribute="term",
        table_headers=["Term", "Definition"],
        item_name="Dictionary Term",
    )


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


class CampaignEditableInfo(Enum):
    """Enum for the editable info of a campaign. Used to build blueprint routes and template variables."""

    BOOK = EditItem(
        name="book",
        route="campaign.edit_book",
        div_id="book",
        tab=CampaignViewTab.BOOKS,
    )


class CharacterEditableInfo(Enum):
    """Enum for the editable info of a character. Used to build blueprint routes and template variables."""

    CUSTOM_SECTION = EditItem(
        name="customsection",
        route="character_edit.edit_customsection",
        div_id="customsection",
        tab=CharacterViewTab.INFO,
    )
