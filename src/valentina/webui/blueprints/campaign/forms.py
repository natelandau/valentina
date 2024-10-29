"""Forms for editing a campaign."""

from quart_wtf import QuartForm
from wtforms import HiddenField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length


class CampaignDescriptionForm(QuartForm):
    """Form for editing a campaign description."""

    title = "Campaign Overview"

    name = StringField(
        "Campaign Name",
        default="",
        validators=[DataRequired(), Length(min=3, message="Must be at least 3 characters")],
        filters=[str.strip, str.title],
    )

    description = TextAreaField(
        "Description",
        validators=[DataRequired(), Length(min=3, message="Must be at least 3 characters")],
        description="Markdown is supported",
    )

    item_id = HiddenField()
    submit = SubmitField("Submit")


class CampaignBookForm(QuartForm):
    """Form for editing a campaign book."""

    title = "Add Book"
    campaign_id = HiddenField()
    name = StringField(
        "Book Name",
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
    submit = SubmitField("Submit")


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
    submit = SubmitField("Submit")


class CampaignNoteForm(QuartForm):
    """Form for a campaign note."""

    text = TextAreaField("Text", validators=[DataRequired()])

    note_id = HiddenField()
    book_id = HiddenField()
    chapter_id = HiddenField()

    submit = SubmitField("Submit")


class CampaignNPCForm(QuartForm):
    """Form for a campaign NPC."""

    name = StringField(
        "NPC Name",
        default="",
        validators=[DataRequired(), Length(min=3, message="Must be at least 3 characters")],
        filters=[str.strip, str.title],
    )
    description = TextAreaField(
        "Description",
        description="Markdown is supported",
    )

    npc_class = StringField(
        "NPC Class",
        default="",
        validators=[DataRequired(), Length(min=3, message="Must be at least 3 characters")],
        filters=[str.strip, str.title],
        description="e.g. 'Vampire', 'Mortal'",
    )

    uuid = HiddenField()
    campaign_id = HiddenField()
    submit = SubmitField("Submit")
