"""Character models for Valentina."""
from datetime import datetime
from typing import Optional, Union, cast

from beanie import (
    Document,
    Indexed,
    Insert,
    Link,
    Replace,
    Save,
    SaveChanges,
    Update,
    before_event,
)
from loguru import logger
from pydantic import BaseModel, Field

from valentina.constants import (
    CharacterConcept,
    CharClass,
    HunterCreed,
    TraitCategory,
    VampireClan,
)
from valentina.models.aws import AWSService
from valentina.utils import errors
from valentina.utils.helpers import get_max_trait_value, num_to_circles, time_now


class CharacterSheetSection(BaseModel):
    """Represents a character sheet section as a subdocument within Character."""

    title: str
    content: str


class CharacterTrait(Document):
    """Represents a character trait value as a subdocument within Character."""

    category_name: str  # TraitCategory enum name
    character: Indexed(str)  # type: ignore [valid-type]
    display_on_sheet: bool = True
    is_custom: bool = False
    max_value: int
    name: str
    value: int

    @property
    def dots(self) -> str:
        """Return the trait's value as a string of dots."""
        return num_to_circles(self.value, self.max_value)

    @property
    def category(self) -> TraitCategory:
        """Return the trait's category."""
        return TraitCategory[self.category_name] if self.category_name else None


class Character(Document):
    """Represents a character in the database."""

    char_class_name: str  # CharClass enum name
    date_created: datetime = Field(default_factory=time_now)
    date_modified: datetime = Field(default_factory=time_now)
    freebie_points: int = 0
    guild: Indexed(int)  # type: ignore [valid-type]
    images: list[str] = Field(default_factory=list)
    is_alive: bool = True
    name_first: str
    name_last: str
    name_nick: str | None = None

    sheet_sections: list[CharacterSheetSection] = Field(default_factory=list)
    traits: list[Link[CharacterTrait]] = Field(default_factory=list)

    type_chargen: bool = False
    type_debug: bool = False
    type_storyteller: bool = False
    type_player: bool = False
    type_developer: bool = False
    user_creator: int  # id of the user who created the character
    user_owner: int  # id of the user who owns the character

    # Profile
    bio: str | None = None
    age: int | None = None
    auspice: str | None = None
    breed: str | None = None
    clan_name: str | None = None  # VampireClan enum name
    concept_name: str | None = None  # CharacterConcept enum name
    creed_name: str | None = None  # HunterCreed enum name
    demeanor: str | None = None
    dob: Optional[datetime] = None
    essence: str | None = None
    generation: str | None = None
    nature: str | None = None
    sire: str | None = None
    tradition: str | None = None
    tribe: str | None = None

    @before_event(Insert, Replace, Save, Update, SaveChanges)
    async def update_modified_date(self) -> None:
        """Update the date_modified field."""
        self.date_modified = time_now()

    @property
    def name(self) -> str:
        """Return the character's name."""
        return f"{self.name_first} {self.name_last}"

    @property
    def full_name(self) -> str:
        """Return the character's full name."""
        nick = f" '{self.name_nick}'" if self.name_nick else ""
        last = f" {self.name_last}" if self.name_last else ""

        return f"{self.name_first}{nick}{last}".strip()

    @property
    def char_class(self) -> CharClass:
        """Return the character's class."""
        try:
            return CharClass[self.char_class_name.upper()] if self.char_class_name else None
        except KeyError as e:
            raise errors.NoCharacterClassError from e

    @property
    def concept(self) -> CharacterConcept | None:
        """Return the character's concept as an enum value if available, else a string.

        Returns:
            CharacterConcept|None: The character's concept, if it exists; otherwise, None.
        """
        try:
            return CharacterConcept[self.concept_name] if self.concept_name else None
        except KeyError:
            return None

    @property
    def clan(self) -> VampireClan:
        """Return the character's clan."""
        try:
            return VampireClan[self.clan_name] if self.clan_name else None
        except KeyError:
            return None

    @property
    def creed(self) -> HunterCreed:
        """Return the user who created the character."""
        try:
            return HunterCreed[self.creed_name] if self.creed_name else None
        except KeyError:
            return None

    async def add_image(self, extension: str, data: bytes) -> str:
        """Add an image to a character and upload it to Amazon S3.

        This function generates a unique key for the image, uploads the image to S3, and updates the character in the database to include the new image.

        Args:
            extension (str): The file extension of the image.
            data (bytes): The image data in bytes.

        Returns:
            str: The key to the image in Amazon S3.
        """
        aws_svc = AWSService()

        # Generate the key for the image
        key_prefix = f"{self.guild}/characters/{self.id}"
        image_number = len(self.images) + 1
        image_name = f"{image_number}.{extension}"
        key = f"{key_prefix}/{image_name}"

        # Upload the image to S3
        aws_svc.upload_image(data=data, key=key)

        # Add the image to the character's data
        self.images.append(key)

        # Save the character
        await self.save()

        return key

    async def delete_image(self, key: str) -> None:
        """Delete a character's image from both the character data and Amazon S3.

        This method updates the character's data to remove the image reference
        and also deletes the actual image stored in Amazon S3.

        Args:
            ctx (discord.ApplicationContext): The context containing the bot object.
            character (Character): The character object to update.
            key (str): The key representing the image to be deleted.

        Returns:
            None
        """
        aws_svc = AWSService()

        # Remove image key from character's data
        if key in self.images:
            self.images.remove(key)
            await self.save()
            logger.debug(f"DATA: Removed image key '{key}' from character '{self.name}'")

        # Delete the image from Amazon S3
        aws_svc.delete_object(key)
        logger.info(f"S3: Deleted {key} from {self.name}")

    async def add_trait(
        self,
        category: TraitCategory,
        name: str,
        value: int,
        max_value: int | None = None,
        display_on_sheet: bool = True,
        is_custom: bool = True,
    ) -> "CharacterTrait":
        """Create a new trait."""
        # Check if the trait already exists
        for trait in cast(list[CharacterTrait], self.traits):
            if trait.name == name and trait.category_name == category.name.upper():
                raise errors.TraitExistsError

        # Check if the trait is custom
        if name.lower() in [x.lower() for x in category.value.COMMON] + [
            x.lower() for x in getattr(category.value, self.char_class_name, [])
        ]:
            is_custom = False
            max_value = get_max_trait_value(name, category.name)

        # Create the new trait
        new_trait = CharacterTrait(
            category_name=category.name,
            character=str(self.id),
            name=name,
            value=value,
            display_on_sheet=display_on_sheet,
            is_custom=is_custom,
            max_value=max_value if max_value else get_max_trait_value(name, category.name),
        )
        await new_trait.save()

        # Add the new trait to the character
        self.traits.append(new_trait)
        await self.save()

        return new_trait

    async def fetch_trait_by_name(self, name: str) -> Union["CharacterTrait", None]:
        """Fetch a CharacterTrait by name."""
        for trait in cast(list[CharacterTrait], self.traits):
            if trait.name == name:
                return trait

        return None
