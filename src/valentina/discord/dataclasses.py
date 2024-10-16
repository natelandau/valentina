"""Dataclasses for Valentina app."""

from dataclasses import dataclass

from valentina.models import Campaign, CampaignBook, Character


@dataclass(eq=True)
class ChannelObjects:
    """Dataclass for Channel Objects."""

    campaign: Campaign | None
    book: CampaignBook | None
    character: Character | None
    is_storyteller_channel: bool

    def __bool__(self) -> bool:
        """Return True if any of the objects are present."""
        return any([self.campaign, self.book, self.character])
