"""Forms for individual character fields."""

import uuid

from quart_wtf import QuartForm
from wtforms import DateField, HiddenField, StringField, SubmitField, ValidationError
from wtforms.validators import DataRequired, Length, Optional

from valentina.utils import console

from .validators import validate_unique_character_name


class EmptyForm(QuartForm):
    """Form for creating a character."""

    title = ""
    prefix = str(uuid.uuid4())[:8]

    async def async_validators_name_last(self, name_last: StringField) -> None:
        """Check if the first + lastname are unique in the database."""
        console.log(f"{self.character_id.data=}")
        if not await validate_unique_character_name(
            name_first=self.name_first.data,
            name_last=name_last.data,
            character_id=self.character_id.data,
        ):
            msg = "Character name must not already exist."
            raise ValidationError(msg)

    async def async_validators_name_first(self, name_first: StringField) -> None:
        """Check if the first + lastname are unique in the database."""
        console.log(f"{self.character_id.data=}")
        if not await validate_unique_character_name(
            name_first=name_first.data,
            name_last=self.name_last.data,
            character_id=self.character_id.data,
        ):
            msg = "Character name must not already exist."
            raise ValidationError(msg)


class CharacterEditForm(QuartForm):
    """Form for creating a character."""

    title = ""
    prefix = str(uuid.uuid4())[:8]
    character_id = HiddenField()

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
    submit = SubmitField("Submit")

    async def async_validators_name_last(self, name_last: StringField) -> None:
        """Check if the first + lastname are unique in the database."""
        if not await validate_unique_character_name(
            name_first=self.name_first.data,
            name_last=name_last.data,
            character_id=self.character_id.data,
        ):
            msg = "Character name must not already exist."
            raise ValidationError(msg)

    async def async_validators_name_first(self, name_first: StringField) -> None:
        """Check if the first + lastname are unique in the database."""
        if not await validate_unique_character_name(
            name_first=name_first.data,
            name_last=self.name_last.data,
            character_id=self.character_id.data,
        ):
            msg = "Character name must not already exist."
            raise ValidationError(msg)
