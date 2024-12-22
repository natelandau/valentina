"""Model for the Valentina dictionary."""

import re
from datetime import datetime
from typing import Optional

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


class DictionaryTerm(Document):
    """Represent a term in the dictionary."""

    term: str
    link: Optional[str] = ""
    definition: Optional[str] = ""
    guild_id: int
    synonyms: list[str] = Field(default_factory=list)
    date_created: datetime = Field(default_factory=time_now)
    date_modified: datetime = Field(default_factory=time_now)

    @before_event(Insert, Replace, Save, Update, SaveChanges)
    async def update_modified_date(self) -> None:
        """Update the date_modified field."""
        self.date_modified = time_now()

    @before_event(Insert, Replace, Save, Update, SaveChanges)
    def term_to_lowercase(self) -> None:
        """Normalize the term to lowercase."""
        self.term = self.term.lower().strip()

    @before_event(Insert, Replace, Save, Update, SaveChanges)
    def normalize_synonyms(self) -> None:
        """Normalize the synonyms."""
        self.synonyms = [x.lower().strip() for x in self.synonyms if re.search(r"\w", x)]
