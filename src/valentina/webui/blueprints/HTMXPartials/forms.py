"""Forms for HTMX Partials."""

import re

from bson import ObjectId
from quart_wtf import QuartForm
from quart_wtf.file import FileAllowed, FileField
from wtforms import (
    HiddenField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import URL, DataRequired, Length, Optional, Regexp, ValidationError

from valentina.constants import VALID_IMAGE_EXTENSIONS, InventoryItemType, TraitCategory
from valentina.models import DictionaryTerm


class CharacterImageUploadForm(QuartForm):
    """Form for uploading an image to a character."""

    image = FileField(
        "Upload Character Image",
        validators=[FileAllowed(VALID_IMAGE_EXTENSIONS, "Images only!")],  # type: ignore [arg-type]
    )
    submit = SubmitField("Submit")
    cancel = SubmitField("Cancel")


class AddExperienceForm(QuartForm):
    """Form for adding experience."""

    title = "Add Experience"

    campaign = SelectField("Campaign", validators=[Optional()])
    experience = StringField(
        "Experience",
        default="0",
        validators=[Regexp(regex=r"^\d+$", message="Must be a positive integer")],
    )
    cool_points = StringField(
        "Cool Points",
        default="0",
        validators=[Regexp(regex=r"^\d+$", message="Must be a positive integer")],
    )
    target_id = HiddenField()
    submit = SubmitField("Submit")
    cancel = SubmitField("Cancel")


class CampaignDescriptionForm(QuartForm):
    """Form for editing a campaign description and name."""

    title = "Campaign Overview"

    name = StringField(
        "Campaign Name",
        default="",
        validators=[DataRequired(), Length(min=3, message="Must be at least 3 characters")],
        filters=[str.strip, str.title],
    )

    campaign_description = TextAreaField(
        "Description",
        validators=[DataRequired(), Length(min=3, message="Must be at least 3 characters")],
        description="Markdown is supported",
    )

    campaign_id = HiddenField()


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


class DictionaryTermForm(QuartForm):
    """Form for a dictionary term."""

    term = StringField("Term", validators=[DataRequired(), Length(min=5)])
    link = StringField("Link", validators=[Optional(), URL()])
    definition = TextAreaField(
        "Definition",
        validators=[Optional(), Length(min=10)],
        description="Markdown is supported",
    )
    synonyms = StringField("Synonyms", validators=[Optional()], description="Comma separated")

    term_id = HiddenField()
    guild_id = HiddenField()

    async def async_validators_term(self, term: StringField) -> None:
        """Check if the term is unique."""
        existing_db_id = ObjectId(self.term_id.data) if self.term_id.data else None

        # Check against other term names
        if (
            await DictionaryTerm.find(
                DictionaryTerm.guild_id == int(self.guild_id.data),
                DictionaryTerm.id != existing_db_id,
                DictionaryTerm.term == term.data.strip().lower(),
            ).count()
            > 0
        ):
            msg = "Term already exists."
            raise ValidationError(msg)

        # Check against other synonyms
        all_db_terms = await DictionaryTerm.find(
            DictionaryTerm.guild_id == int(self.guild_id.data),
            DictionaryTerm.id != existing_db_id,
            DictionaryTerm.term != term.data.strip().lower(),
        ).to_list()

        for db_term in all_db_terms:
            if self.term.data.strip().lower() in db_term.synonyms:
                msg = f"Already a synonym of <em>{db_term.term}</em>."
                raise ValidationError(msg)

    async def async_validators_synonyms(self, synonyms: StringField) -> None:
        """Check if the synonyms are unique."""
        existing_db_id = ObjectId(self.term_id.data) if self.term_id.data else None

        synonyms_list = [s.strip().lower() for s in synonyms.data.split(",") if re.search(r"\w", s)]
        for synonym in synonyms_list:
            if synonym == self.term.data.strip().lower():
                msg = "Synonym cannot be the same as the term."
                raise ValidationError(msg)

            if len(synonym) < 5:  # noqa: PLR2004
                msg = "Synonym must be at least 5 characters."
                raise ValidationError(msg)

            # Check against other term names
            if (
                await DictionaryTerm.find(
                    DictionaryTerm.guild_id == int(self.guild_id.data),
                    DictionaryTerm.id != existing_db_id,
                    DictionaryTerm.term == synonym,
                ).count()
                > 0
            ):
                msg = f"Synonym <em>{synonym}</em> already exists."
                raise ValidationError(msg)

            # Check against other synonyms
            all_db_terms = await DictionaryTerm.find(
                DictionaryTerm.guild_id == int(self.guild_id.data),
                DictionaryTerm.id != existing_db_id,
            ).to_list()

            for db_term in all_db_terms:
                if synonym in db_term.synonyms:
                    msg = f"{synonym} is already a synonym of <em>{db_term.term}</em>."
                    raise ValidationError(msg)

    async def async_validators_link(self, link: StringField) -> None:
        """Fail if the link and a definition are both provided."""
        if link.data and self.definition.data:
            msg = "Link and definition cannot both be provided."
            raise ValidationError(msg)

        if not link.data and not self.definition.data:
            msg = "Either a link or a definition must be provided."
            raise ValidationError(msg)

    async def async_validators_definition(self, definition: TextAreaField) -> None:
        """Fail if a link and definition are both provided."""
        if self.link.data and definition.data:
            msg = "Link and definition cannot both be provided."
            raise ValidationError(msg)

        if not definition.data and not self.link.data:
            msg = "Either a link or a definition must be provided."
            raise ValidationError(msg)


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


class CharacterBioForm(QuartForm):
    """A form for editing the character biography."""

    title = "The Character's Biography"

    bio = TextAreaField(
        "Biography",
        description="Markdown is supported.",
        validators=[DataRequired(), Length(min=5, message="Must be at least 5 characters")],
    )
    character_id = HiddenField()
