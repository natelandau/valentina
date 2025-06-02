"""Custom Forms model for Valentina WebUI."""

from quart_wtf import QuartForm
from wtforms import DateField, SelectField, StringField, SubmitField, ValidationError
from wtforms.validators import DataRequired, Length, Optional

from valentina.constants import (
    CharClass,
    HunterCreed,
    VampireClan,
    WerewolfAuspice,
    WerewolfBreed,
    WerewolfTribe,
)
from valentina.models import Character


class CharacterCreateStep1(QuartForm):
    """Form for creating a character."""

    title = "Step 1"
    prefix = "step1"

    firstname = StringField(
        "First Name",
        default="",
        validators=[DataRequired(), Length(min=3, message="Must be at least 3 characters")],
        filters=[str.strip, str.title],
    )
    lastname = StringField(
        "Last Name",
        default="",
        validators=[DataRequired(), Length(min=3, message="Must be at least 3 characters")],
        filters=[str.strip, str.title],
    )
    nickname = StringField(
        "Nickname",
        default="",
        validators=[Optional()],
        filters=[str.strip, str.title],
    )
    char_class = SelectField(
        "Character Class",
        choices=[("", "-- Select --")]
        + [(x.name, x.value.name) for x in CharClass.playable_classes()],
        validators=[DataRequired()],
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
        "Date of Birth",
        description="Used to calculate age",
        validators=[Optional()],
        default="",
    )
    submit = SubmitField("Continue to Step 2")
    cancel = SubmitField("Cancel")

    async def async_validators_lastname(self, lastname: StringField) -> None:
        """Check if the first + lastname are unique in the database."""
        name_first = self.firstname.data
        name_last = lastname.data

        if (
            await Character.find(
                Character.name_first == name_first,
                Character.name_last == name_last,
            ).count()
            > 0
        ):
            msg = "Character name must not already exist."
            raise ValidationError(msg)

    async def async_validators_firstname(self, firstname: StringField) -> None:
        """Check if the first + lastname are unique in the database."""
        name_first = firstname.data
        name_last = self.lastname.data

        if (
            await Character.find(
                Character.name_first == name_first,
                Character.name_last == name_last,
            ).count()
            > 0
        ):
            msg = "Character name must not already exist."
            raise ValidationError(msg)


class VampireClassSpecifics(QuartForm):
    """Class specific items for Vampires."""

    title = "Vampire Class Specifics"
    prefix = "vampire"

    clan_name = SelectField(
        "Vampire Clan",
        choices=[("", "-- Select --")] + [(x.name, x.value.name) for x in VampireClan],
        validators=[DataRequired()],
    )
    sire = StringField(
        "Sire",
        default="",
        validators=[Optional()],
        filters=[str.strip, str.title],
    )
    generation = StringField(
        "Generation",
        default="",
        validators=[Optional()],
        filters=[str.strip, str.title],
    )
    submit = SubmitField("Continue to Step 3")
    cancel = SubmitField("Cancel")


class WerewolfClassSpecifics(QuartForm):
    """Class specific items for Werewolves."""

    title = "Werewolf Class Specifics"
    prefix = "werewolf"

    breed = SelectField(
        "Breed",
        choices=[("", "-- Select --")] + [(x.name, x.value.name) for x in WerewolfBreed],
        validators=[DataRequired()],
    )
    auspice = SelectField(
        "Breed",
        choices=[("", "-- Select --")] + [(x.name, x.value.name) for x in WerewolfAuspice],
        validators=[DataRequired()],
    )
    tribe = SelectField(
        "Breed",
        choices=[("", "-- Select --")] + [(x.name, x.value.name) for x in WerewolfTribe],
        validators=[DataRequired()],
    )
    submit = SubmitField("Continue to Step 3")
    cancel = SubmitField("Cancel")


class HunterClassSpecifics(QuartForm):
    """Class specific items for Hunters."""

    title = "Hunter Class Specifics"
    prefix = "hunter"

    creed = SelectField(
        "Creed",
        choices=[("", "-- Select --")] + [(x.name, x.value.name) for x in HunterCreed],
        validators=[DataRequired()],
    )
    submit = SubmitField("Continue to Step 3")
    cancel = SubmitField("Cancel")
