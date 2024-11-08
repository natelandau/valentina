"""Forms for editing a campaign."""

from quart_wtf import QuartForm
from wtforms import HiddenField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length


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
