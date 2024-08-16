"""Character models for Valentina."""

import asyncio
from datetime import datetime
from typing import TYPE_CHECKING, Optional, Union, cast

import discord
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
    CHANNEL_PERMISSIONS,
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
    from valentina.models import Campaign  # noqa: TCH004
    from valentina.models.bot import ValentinaContext


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


class InventoryItem(Document):
    """Represents an item in a character's inventory."""

    character: Indexed(str)  # type: ignore [valid-type]
    name: str
    description: str = ""
    type: str  # InventoryItemType enum name


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
        emoji = Emoji.SILHOUETTE.value if self.is_alive else Emoji.DEAD.value

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
            max_value=max_value or get_max_trait_value(name, category.name),
        )
        await new_trait.save()

        # Add the new trait to the character
        self.traits.append(new_trait)
        await self.save()

        return new_trait

    async def associate_with_campaign(  # pragma: no cover
        self, ctx: "ValentinaContext", new_campaign: "Campaign"
    ) -> bool:
        """Associate a character with a campaign.

        This method associates the character with the specified campaign, updates the database,
        confirms the character's channel, and sorts the campaign channels.

        Args:
            ctx (ValentinaContext): The context object containing guild information.
            new_campaign (Campaign): The new campaign to associate with the character.

        Returns:
            bool: True if the character was successfully associated with the new campaign, False if already associated.
        """
        if self.campaign == str(new_campaign.id):
            logger.debug(f"Character {self.name} is already associated with {new_campaign.name}")
            return False

        self.campaign = str(new_campaign.id)
        await self.save()

        await self.confirm_channel(ctx, new_campaign)
        await new_campaign.sort_channels(ctx)
        return True

    async def confirm_channel(
        self, ctx: "ValentinaContext", campaign: Optional["Campaign"]
    ) -> discord.TextChannel | None:
        """Confirm or create the channel for the character within the campaign.

        This method ensures the character's channel exists within the campaign's category. It updates the channel information in the database if necessary, renames it if it has the wrong name, or creates a new one if it doesn't exist.

        Args:
            ctx (ValentinaContext): The context object containing guild information.
            campaign (Optional[Campaign]): The campaign object. If not provided, it will be fetched using the character's campaign ID.

        Returns:
            discord.TextChannel | None: The channel object if found or created, otherwise None.
        """
        campaign = campaign or await Campaign.get(self.campaign)
        if not campaign:
            return None

        category, channels = await campaign.fetch_campaign_category_channels(ctx)

        if not category:
            return None

        is_channel_name_in_category = any(self.channel_name == channel.name for channel in channels)
        is_channel_id_in_category = (
            any(self.channel == channel.id for channel in channels) if self.channel else False
        )
        owned_by_user = discord.utils.get(ctx.bot.users, id=self.user_owner)

        # If channel name exists in category but not in database, add channel id to self
        if is_channel_name_in_category and not self.channel:
            await asyncio.sleep(1)  # Keep the rate limit happy
            for channel in channels:
                if channel.name == self.channel_name:
                    self.channel = channel.id
                    await self.save()
                    return channel

        # If channel.id exists but has wrong name, rename it
        elif self.channel and is_channel_id_in_category and not is_channel_name_in_category:
            channel_object = next(
                (channel for channel in channels if self.channel == channel.id), None
            )
            return await ctx.channel_update_or_add(
                channel=channel_object,
                name=self.channel_name,
                category=category,
                permissions=CHANNEL_PERMISSIONS["campaign_character_channel"],
                permissions_user_post=owned_by_user,
                topic=f"Character channel for {self.name}",
            )

        # If channel does not exist, create it
        elif not is_channel_name_in_category:
            await asyncio.sleep(1)  # Keep the rate limit happy
            book_channel = await ctx.channel_update_or_add(
                name=self.channel_name,
                category=category,
                permissions=CHANNEL_PERMISSIONS["campaign_character_channel"],
                permissions_user_post=owned_by_user,
                topic=f"Character channel for {self.name}",
            )
            self.channel = book_channel.id
            await self.save()
            return book_channel

        await asyncio.sleep(1)  # Keep the rate limit happy
        return discord.utils.get(channels, name=self.channel_name)

    async def delete_channel(self, ctx: "ValentinaContext") -> None:  # pragma: no cover
        """Delete the channel associated with the character.

        This method removes the channel linked to the character from the guild and updates the character's channel information.

        Args:
            ctx (ValentinaContext): The context object containing guild information.

        Returns:
            None
        """
        if not self.channel:
            return

        channel = ctx.guild.get_channel(self.channel)

        if not channel:
            return

        await channel.delete()
        self.channel = None
        await self.save()

    async def delete_image(self, key: str) -> None:  # pragma: no cover
        """Delete a character's image from both the character data and Amazon S3.

        This method updates the character's data to remove the image reference
        and also deletes the actual image stored in Amazon S3.

        Args:
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
        logger.info(f"S3: Delete {key} from {self.name}")

    async def fetch_trait_by_name(self, name: str) -> Union["CharacterTrait", None]:
        """Fetch a CharacterTrait by name."""
        for trait in cast(list[CharacterTrait], self.traits):
            if trait.name == name:
                return trait

        return None

    async def update_channel_permissions(
        self, ctx: "ValentinaContext", campaign: "Campaign"
    ) -> discord.TextChannel | None:  # pragma: no cover
        """Update the permissions for the character's channel.

        This method updates the permissions for a character's channel, renames it, and sets the appropriate category and topic. Run this method after updating the character's user_owner.

        Args:
            ctx (ValentinaContext): The context object containing guild information.
            campaign (Campaign): The campaign object to which the character belongs.

        Returns:
            discord.TextChannel | None: The updated channel object, or None if the channel does not exist.
        """
        if not self.channel:
            return None

        channel = ctx.guild.get_channel(self.channel)
        channel_name = f"{Emoji.SILHOUETTE.value}-{self.name.lower().replace(' ', '-')}"
        owned_by_user = discord.utils.get(ctx.bot.users, id=self.user_owner)
        category = discord.utils.get(ctx.guild.categories, id=campaign.channel_campaign_category)

        if not channel:
            return None

        return await ctx.channel_update_or_add(
            channel=channel,
            name=channel_name,
            category=category,
            permissions=CHANNEL_PERMISSIONS["campaign_character_channel"],
            permissions_user_post=owned_by_user,
            topic=f"Character channel for {self.name}",
        )

    def sheet_section_top_items(self) -> dict[str, str]:
        """Return the items to populate the top portion of a character sheet.

        Populate a dictionary with attributes that are present in the character
        and return the dictionary with properly titled values.

        Returns:
            dict[str, str]: Dictionary with character attributes.
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
