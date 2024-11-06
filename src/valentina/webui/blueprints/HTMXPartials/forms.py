"""Forms for HTMX Partials."""

from quart_wtf import QuartForm
from wtforms import HiddenField, SelectField, StringField, TextAreaField
from wtforms.validators import DataRequired, Length

from valentina.constants import InventoryItemType, TraitCategory


class UserMacroForm(QuartForm):
    """Form for a user macro."""

    name = StringField(
        default="",
        validators=[DataRequired(), Length(min=3, message="Must be at least 3 characters")],
    )
    abbreviation = StringField(
        default="",
        description="4 characters or less",
        validators=[DataRequired(), Length(max=4, message="Must be 4 characters or less")],
    )
    description = TextAreaField(description="Markdown is supported")

    trait_one = SelectField(
        "Trait One",
        choices=[("", "-- Select --")] + [(t, t) for t in TraitCategory.get_all_trait_names()],
        validators=[DataRequired()],
    )

    trait_two = SelectField(
        "Trait Two",
        choices=[("", "-- Select --")] + [(t, t) for t in TraitCategory.get_all_trait_names()],
        validators=[DataRequired()],
    )

    uuid = HiddenField()
    user_id = HiddenField()


class InventoryItemForm(QuartForm):
    """Form for an inventory item."""

    name = StringField("Name", validators=[DataRequired()])
    type = SelectField(
        "Type",
        choices=[("", "-- Select --")] + [(x.name, x.value) for x in InventoryItemType],
        validators=[DataRequired()],
    )
    description = TextAreaField("Description")
    item_id = HiddenField()
    character_id = HiddenField()


class NoteForm(QuartForm):
    """Form for a campaign note."""

    text = TextAreaField(
        "Text", validators=[DataRequired(), Length(min=5)], description="Markdown is supported"
    )

    note_id = HiddenField()
    book_id = HiddenField()
    campaign_id = HiddenField()
    character_id = HiddenField()


class CampaignChapterForm(QuartForm):
    """Form for editing a campaign chapter."""

    name = StringField(
        "Chapter Name",
        default="",
        validators=[DataRequired(), Length(min=3, message="Must be at least 3 characters")],
        filters=[str.strip, str.title],
    )
    description_short = TextAreaField(
        "Short Description",
        validators=[],
        description="Markdown is supported",
    )
    description_long = TextAreaField(
        "Description",
        validators=[],
        description="Markdown is supported",
    )

    book_id = HiddenField()
    chapter_id = HiddenField()


class CampaignNPCForm(QuartForm):
    """Form for a campaign NPC."""

    name = StringField(
        "NPC Name",
        default="",
        validators=[DataRequired(), Length(min=3, message="Must be at least 3 characters")],
        filters=[str.strip, str.title],
    )
    npc_class = StringField(
        "NPC Class",
        default="",
        validators=[DataRequired(), Length(min=3, message="Must be at least 3 characters")],
        filters=[str.strip, str.title],
        description="e.g. 'Vampire', 'Mortal'",
    )
    description = TextAreaField(
        "Description",
        description="Markdown is supported",
    )

    uuid = HiddenField()
    campaign_id = HiddenField()
