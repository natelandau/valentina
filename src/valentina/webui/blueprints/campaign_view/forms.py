"""Forms for editing a campaign."""

import uuid

from quart_wtf import QuartForm
from wtforms import StringField, TextAreaField
from wtforms.validators import DataRequired, Length


class CampaignOverviewForm(QuartForm):
    """Form for editing a campaign overview."""

    title = "Campaign Overview"
    prefix = str(uuid.uuid4())[:8]

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
