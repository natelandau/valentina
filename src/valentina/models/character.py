"""Character models for Valentina."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional, Union, cast

import discord
import inflect
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
    Emoji,
    HunterCreed,
    TraitCategory,
    VampireClan,
)
from valentina.models.aws import AWSService
from valentina.utils import errors
from valentina.utils.helpers import get_max_trait_value, num_to_circles, time_now

from .note import Note

if TYPE_CHECKING:
    from valentina.models import Campaign


p = inflect.engine()
p.defnoun("Ability", "Abilities")


class CharacterSheetSection(BaseModel):
    """Represent a character sheet section as a subdocument within Character.

    Use this class to define and manage individual sections of a character sheet.
    Each section includes a title and content, allowing for structured organization
    of character information. Implement this class as an embedded document within
    the Character model to maintain a clear hierarchy of character data.

    Attributes:
        title (str): The heading or name of the character sheet section.
        content (str): The detailed information or text content of the section.

    Note:
        Ensure proper integration with the parent Character document for seamless
        data management and retrieval.
    """

    title: str
    content: str


class CharacterTrait(Document):
    """Represent a character trait value as a subdocument within Character.

    Use this class to define and manage individual traits for a character.
    Each trait includes properties such as category, name, value, and maximum value.
    Implement methods to handle trait-specific operations and provide convenient
    access to trait information.

    Note:
    - This class is designed to be embedded within the Character document.
    - Ensure proper indexing of the 'character' field for efficient querying.
    """

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


class InventoryItem(Document):
    """Represent an item in a character's inventory.

    Use this class to create, manage, and store information about items
    that characters possess. Each item includes details such as its name,
    description, and type. Ensure that the 'character' field is properly
    indexed for efficient querying and retrieval of inventory items
    associated with specific characters.
    """

    character: Indexed(str)  # type: ignore [valid-type]
    name: str
    description: str = ""
    type: str  # InventoryItemType enum name


class Character(Document):
    """Represent a character in the database.

    This class defines the structure and properties of a character entity.
    It includes fields for basic information, traits, inventory, notes,
    and various character-specific attributes. Use this class to create,
    retrieve, update, and manage character data in the database.

    The Character model supports different character types (e.g., player,
    storyteller, debug) and game-specific attributes (e.g., clan, breed,
    auspice) for various role-playing game systems.
    """

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
    inventory: list[Link[InventoryItem]] = Field(default_factory=list)
    notes: list[Link[Note]] = Field(default_factory=list)

    type_chargen: bool = False
    type_debug: bool = False
    type_storyteller: bool = False
    type_player: bool = False
    type_developer: bool = False
    user_creator: int  # id of the user who created the character
    user_owner: int  # id of the user who owns the character
    channel: int | None = None  # id of the character's discord channel
    campaign: str | None = None  # id of the character's campaign

    # Profile
    age: int | None = None
    auspice: str | None = None
    bio: str | None = None
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
    def channel_name(self) -> str:
        """Channel name for the book."""
        if self.type_storyteller:
            emoji = Emoji.CHANNEL_PLAYER.value if self.is_alive else Emoji.CHANNEL_PLAYER_DEAD.value
            return f"{Emoji.CHANNEL_PRIVATE.value}{emoji}-{self.name.lower().replace(' ', '-')}"

        emoji = Emoji.CHANNEL_PLAYER.value if self.is_alive else Emoji.CHANNEL_PLAYER_DEAD.value
        return f"{emoji}-{self.name.lower().replace(' ', '-')}"

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

    async def add_image(self, extension: str, data: bytes) -> str:  # pragma: no cover
        """Add an image to a character and upload it to Amazon S3.

        Generate a unique key for the image, uploads the image to S3, and updates the character in the database to include the new image.

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
        logger.debug(f"S3: Uploading {key} to {self.name}")
        aws_svc.upload_image(data=data, key=key)

        # Add the image to the character's data
        self.images.append(key)

        # Save the character
        await self.save()

        return key

    async def add_trait(
        self,
        category: TraitCategory,
        name: str,
        value: int,
        max_value: int | None = None,
        display_on_sheet: bool = True,
        is_custom: bool = True,
    ) -> "CharacterTrait":
        """Create a new trait for the character.

        Add a new trait to the character's list of traits. Check if the trait already exists,
        determine if it's a custom trait, and set the appropriate maximum value. Save the new
        trait to the database and update the character's trait list.

        Args:
            category (TraitCategory): The category of the trait.
            name (str): The name of the trait.
            value (int): The initial value of the trait.
            max_value (int | None, optional): The maximum value for the trait. Defaults to None.
            display_on_sheet (bool, optional): Whether to display the trait on the character sheet. Defaults to True.
            is_custom (bool, optional): Whether the trait is custom. Defaults to True.

        Returns:
            CharacterTrait: The newly created trait object.

        Raises:
            errors.TraitExistsError: If a trait with the same name and category already exists for the character.
        """
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
            max_value=max_value or get_max_trait_value(name, category.name),
        )
        await new_trait.save()

        # Add the new trait to the character
        self.traits.append(new_trait)
        await self.save()

        return new_trait

    async def associate_with_campaign(self, new_campaign: "Campaign") -> bool:
        """Associate a character with a campaign.

        Associate the character with the specified campaign, update the database,
        confirm the character's channel, and sort the campaign channels. If the
        character is already associated with the given campaign, no action is taken.

        Args:
            ctx (ValentinaContext): The context object containing guild information
                and other relevant data for the operation.
            new_campaign (Campaign): The campaign to associate with the character.

        Returns:
            bool: True if the character was successfully associated with the new
                campaign, False if the character was already associated with the
                campaign.
        """
        if self.campaign == str(new_campaign.id):
            logger.debug(f"Character {self.name} is already associated with {new_campaign.name}")
            return False

        self.campaign = str(new_campaign.id)
        await self.save()

        return True

    def concept_description(self) -> str:
        """Return a text description of the character's concept and special abilities.

        Returns:
            str: A text description of the character's concept and special abilities.
        """
        if not self.concept_name:
            return ""

        concept_info = CharacterConcept[self.concept_name].value

        if self.char_class_name == CharClass.MORTAL.name:
            # Generate special abilities list
            special_abilities_list = [
                f"{i}. **{ability['name']}:** {ability['description']}\n"
                for i, ability in enumerate(concept_info.abilities, start=1)
            ]
            special_abilities = f'\n\n**Special {p.plural_noun("Ability", len(concept_info.abilities))}:**\n\n{"".join(special_abilities_list)}'
        else:
            special_abilities = ""

        return f"""
**{self.name} is a {concept_info.name}** - {concept_info.description}
{special_abilities}
"""

    async def delete_image(self, key: str) -> None:  # pragma: no cover
        """Delete a character's image from both the character data and Amazon S3.

        Remove the specified image key from the character's data and delete the
        corresponding image file from Amazon S3 storage. This method ensures
        that both the database reference and the actual image file are removed.

        Args:
            key (str): The unique identifier of the image to be deleted.

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
        logger.info(f"S3: Delete {key} from {self.name}")

    async def fetch_trait_by_name(self, name: str) -> Union["CharacterTrait", None]:
        """Fetch a CharacterTrait by name."""
        for trait in cast(list[CharacterTrait], self.traits):
            if trait.name == name:
                return trait

        return None

    def sheet_section_top_items(self) -> dict[str, str]:
        """Generate a dictionary of key attributes for the top section of a character sheet.

        Compile a dictionary containing essential character attributes for display
        in the top portion of a character sheet. Include attributes such as class,
        concept, demeanor, nature, and class-specific traits (e.g., clan for vampires,
        auspice for werewolves). Omit attributes that are not applicable or not set.

        Format attribute names as properly titled keys and ensure all values are
        strings, using '-' for missing or inapplicable attributes.

        Returns:
            dict[str, str]: A dictionary of character attributes, where keys are
            attribute names and values are their corresponding string representations.
        """
        attributes = [
            ("Class", self.char_class_name if self.char_class_name else "-"),
            ("Concept", self.concept_name),
            ("Demeanor", self.demeanor if self.demeanor else "-"),
            ("Nature", self.nature if self.nature else "-"),
            (
                "Auspice",
                self.auspice
                if self.auspice
                else "-"
                if self.char_class_name.lower() == "werewolf"
                else None,
            ),
            (
                "Breed",
                self.breed
                if self.breed
                else "-"
                if self.char_class_name.lower() == "werewolf"
                else None,
            ),
            (
                "Clan",
                self.clan_name
                if self.clan_name
                else "-"
                if self.char_class_name.lower() == "vampire"
                else None,
            ),
            (
                "Creed",
                self.creed_name
                if self.creed_name
                else "-"
                if self.char_class_name.lower() == "hunter"
                else None,
            ),
            ("Essence", self.essence),
            (
                "Generation",
                self.generation
                if self.generation
                else "-"
                if self.char_class_name.lower() == "vampire"
                else None,
            ),
            (
                "Sire",
                self.sire
                if self.sire
                else "-"
                if self.char_class_name.lower() == "vampire"
                else None,
            ),
            ("Tradition", self.tradition),
            (
                "Tribe",
                self.tribe
                if self.tribe
                else "-"
                if self.char_class_name.lower() == "werewolf"
                else None,
            ),
            ("Date of Birth", self.dob.strftime("%Y-%m-%d") if self.dob else "-"),
            ("Age", str(self.age)),
        ]

        # Create dictionary using a comprehension with conditional inclusion
        return {
            name: str(value).title().replace("_", " ")
            for name, value in attributes
            if value and value != "None"
        }

    async def update_channel_id(self, channel: discord.TextChannel) -> None:
        """Update the character's channel ID in the database.

        Args:
            channel (discord.TextChannel): The character's channel.
        """
        if self.channel != channel.id:
            self.channel = channel.id
            await self.save()
