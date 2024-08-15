"""Fields for WTForms that are specific to the Valentina web UI."""

from wtforms import DateField, HiddenField, StringField, SubmitField
from wtforms.validators import DataRequired, Length, Optional

name_first = StringField(
    "First Name",
    default="",
    validators=[DataRequired(), Length(min=3, message="Must be at least 3 characters")],
    filters=[str.strip, str.title],
)
name_last = StringField(
    "Last Name",
    default="",
    validators=[DataRequired(), Length(min=3, message="Must be at least 3 characters")],
    filters=[str.strip, str.title],
)
name_nick = StringField(
    "Nickname",
    default="",
    validators=[Optional()],
    filters=[str.strip, str.title],
)
demeanor = StringField(
    "Demeanor",
    default="",
    validators=[Optional(), Length(min=3, message="Must be at least 3 characters")],
    filters=[str.strip, str.title],
)
nature = StringField(
    "Nature",
    default="",
    validators=[Optional(), Length(min=3, message="Must be at least 3 characters")],
    filters=[str.strip, str.title],
)
dob = DateField(
    "Date of Birth", description="Used to calculate age", validators=[Optional()], default=""
)
breed = StringField(
    "Breed",
    default="",
    validators=[Optional()],
    filters=[str.strip, str.title],
)
auspice = StringField(
    "Auspice",
    default="",
    validators=[Optional()],
    filters=[str.strip, str.title],
)
tribe = StringField(
    "Tribe",
    default="",
    validators=[Optional()],
    filters=[str.strip, str.title],
)
sire = StringField(
    "Sire",
    default="",
    validators=[Optional(), Length(min=3, message="Must be at least 3 characters")],
    filters=[str.strip, str.title],
)
generation = StringField(
    "Generation",
    default="",
    validators=[Optional()],
    filters=[str.strip, str.title],
)
submit = SubmitField("Submit")
character_id = HiddenField()
