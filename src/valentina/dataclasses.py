"""Dataclasses for Valentina app."""

from dataclasses import dataclass

from valentina.models import Campaign, CampaignBook, Character


@dataclass
class ChannelObjects:
    """Dataclass for Channel Objects."""

    campaign: Campaign | None
    book: CampaignBook | None
    character: Character | None

    def __bool__(self) -> bool:
        """Return True if any of the objects are present."""
        return any([self.campaign, self.book, self.character])

    def has_book(self) -> bool:
        """Return True if the object has a book."""
        return bool(self.book)

    def has_character(self) -> bool:
        """Return True if the object has a character."""
        return bool(self.character)

    def has_campaign(self) -> bool:
        """Return True if the object has a campaign."""
        return bool(self.campaign)
