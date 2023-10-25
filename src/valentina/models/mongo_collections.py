"""MongoDB collections for Valentina."""
from datetime import datetime, timezone
from typing import Optional, cast

import discord
import semver
from beanie import (
    Document,
    Indexed,
    Insert,
    Link,
    PydanticObjectId,
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
    CharClassType,
    HunterCreed,
    PermissionManageCampaign,
    PermissionsEditTrait,
    PermissionsEditXP,
    PermissionsKillCharacter,
    TraitCategory,
    VampireClan,
)
from valentina.models.aws import AWSService
from valentina.utils import errors, types
from valentina.utils.discord_utils import create_player_role, create_storyteller_role
from valentina.utils.helpers import get_max_trait_value, num_to_circles


def time_now() -> datetime:
    """Return the current time in UTC."""
    return datetime.now(timezone.utc).replace(microsecond=0)


# #### Sub-Documents


class CampaignExperience(Document):
    """Dictionary representing a character's campaign experience as a subdocument attached to a User."""

    campaign: PydanticObjectId
    xp_current: int = 0
    xp_total: int = 0
    cool_points: int = 0


class CampaignChapter(Document):
    """Represents a chapter as a subdocument within Campaign."""

    description_long: str = None
    description_short: str = None
    name: str
    number: int
    date_created: datetime = Field(default_factory=time_now)


class CampaignNPC(Document):
    """Represents a campaign NPC as a subdocument within Campaign."""

    description: str
    name: str
    npc_class: str


class CampaignNote(Document):
    """Represents a campaign note as a subdocument within Campaign."""

    # TODO: Remove user-specific notes from cogs/views
    description: str
    name: str


class CharacterSheetSection(BaseModel):
    """Represents a character sheet section as a subdocument within Character."""

    title: str
    content: str


class UserMacro(Document):
    """Represents a user macro as a subdocument within User."""

    abbreviation: str
    date_created: datetime = Field(default_factory=time_now)
    date_modified: datetime = Field(default_factory=time_now)
    description: str | None = None
    guild: int
    name: str
    trait_one: str | None = None
    trait_two: str | None = None


# #### Core Models


class GlobalProperty(Document):
    """Represents global properties in the database."""

    versions: list[str] = Field(default_factory=list)
    last_update: datetime = Field(default_factory=time_now)

    @before_event(Insert, Replace, Save, Update, SaveChanges)
    async def update_last_update(self) -> None:
        """Update the last_update field."""
        self.last_update = time_now()

    def most_recent_version(self) -> str:
        """Return the most recent version."""
        return max(self.versions, key=semver.Version.parse)


class Guild(Document):
    """Represents a guild in the database."""

    id: int  # type: ignore [assignment]  # noqa: A003

    changelog_posted_version: str | None = None
    channel_id_audit_log: int | None = None
    channel_id_changelog: int | None = None
    channel_id_error_log: int | None = None
    channel_id_storyteller: int | None = None
    date_created: datetime = Field(default_factory=time_now)
    date_modified: datetime = Field(default_factory=time_now)
    name: str
    permissions_edit_trait: PermissionsEditTrait = PermissionsEditTrait.WITHIN_24_HOURS
    permissions_edit_xp: PermissionsEditXP = PermissionsEditXP.PLAYER_ONLY
    permissions_kill_character: PermissionsKillCharacter = (
        PermissionsKillCharacter.CHARACTER_OWNER_ONLY
    )
    permissions_manage_campaigns: PermissionManageCampaign = (
        PermissionManageCampaign.STORYTELLER_ONLY
    )

    @before_event(Insert, Replace, Save, Update, SaveChanges)
    async def update_modified_date(self) -> None:
        """Update the date_modified field."""
        self.date_modified = time_now()

    def fetch_changelog_channel(self, guild: discord.Guild) -> discord.TextChannel | None:
        """Retrieve the changelog channel for the guild from the settings.

        Fetch the guild's settings to determine if a changelog channel has been set.  If set, return the corresponding TextChannel object; otherwise, return None.

        Args:
            guild (discord.Guild): The guild to fetch the changelog channel for.

        Returns:
            discord.TextChannel|None: The changelog channel, if it exists and is set; otherwise, None.
        """
        if self.channel_id_changelog:
            return discord.utils.get(guild.text_channels, id=self.channel_id_changelog)

        return None

    def fetch_storyteller_channel(self, guild: discord.Guild) -> discord.TextChannel | None:
        """Retrieve the storyteller channel for the guild from the settings.

        Fetch the guild's settings to determine if a storyteller channel has been set.  If set, return the corresponding TextChannel object; otherwise, return None.

        Args:
            guild (discord.Guild): The guild to fetch the storyteller channel for.

        Returns:
            discord.TextChannel|None: The storyteller channel, if it exists and is set; otherwise, None.
        """
        if self.channel_id_storyteller:
            return discord.utils.get(guild.text_channels, id=self.channel_id_storyteller)

        return None

    def fetch_audit_log_channel(self, guild: discord.Guild) -> discord.TextChannel | None:
        """Retrieve the audit log channel for the guild from the settings.

        Fetch the guild's settings to determine if an audit log channel has been set.  If set, return the corresponding TextChannel object; otherwise, return None.

        Args:
            guild (discord.Guild): The guild to fetch the audit log channel for.

        Returns:
            discord.TextChannel|None: The audit log channel, if it exists and is set; otherwise, None.
        """
        if self.channel_id_audit_log:
            return discord.utils.get(guild.text_channels, id=self.channel_id_audit_log)

        return None

    def fetch_error_log_channel(self, guild: discord.Guild) -> discord.TextChannel | None:
        """Retrieve the error log channel for the guild from the settings.

        Fetch the guild's settings to determine if an error log channel has been set.  If set, return the corresponding TextChannel object; otherwise, return None.

        Args:
            guild (discord.Guild): The guild to fetch the error log channel for.

        Returns:
            discord.TextChannel|None: The error log channel, if it exists and is set; otherwise, None.
        """
        if self.channel_id_error_log:
            return discord.utils.get(guild.text_channels, id=self.channel_id_error_log)

        return None

    async def setup_roles(self, guild: discord.Guild) -> None:
        """Create or update the guild's roles.

        Args:
            guild (discord.Guild): The guild to create/update roles for.
        """
        # Create roles
        await create_storyteller_role(guild)
        await create_player_role(guild)
        logger.debug(f"GUILD: Roles created/updated on {self.name}")


class User(Document):
    """Represents a user in the database."""

    id: int  # type: ignore [assignment]  # noqa: A003
    active_characters: list[Link["Character"]] = Field(default_factory=list)
    characters: list[Link["Character"]] = Field(default_factory=list)
    campaign_experience: list[CampaignExperience] = Field(default_factory=list)
    date_created: datetime = Field(default_factory=time_now)
    date_modified: datetime = Field(default_factory=time_now)
    macros: list[UserMacro] = Field(default_factory=list)
    name: str | None = None
    guilds: list[int] = Field(default_factory=list)

    @before_event(Insert, Replace, Save, Update, SaveChanges)
    async def update_modified_date(self) -> None:
        """Update the date_modified field."""
        self.date_modified = time_now()

    @property
    def lifetime_experience(self) -> int:
        """Return the user's lifetime experience level."""
        return sum([xp.xp_total for xp in self.campaign_experience])

    @property
    def lifetime_cool_points(self) -> int:
        """Return the user's lifetime cool points."""
        return sum([xp.cool_points for xp in self.campaign_experience])

    def active_character(self, guild: discord.Guild) -> "Character":
        """Return the active character for the user in the guild."""
        try:
            return next(
                x for x in cast(list["Character"], self.active_characters) if x.guild == guild.id
            )
        except StopIteration as e:
            raise errors.NoActiveCharacterError from e

    def all_characters(self, guild: discord.Guild) -> list["Character"]:
        """Return all characters for the user in the guild."""
        return [x for x in cast(list["Character"], self.characters) if x.guild == guild.id]

    async def set_active_character(self, guild: discord.Guild, character: "Character") -> None:
        """Set the active character for the user in the guild.

        Args:
            guild (discord.Guild): The guild to set the active character for.
            character (Character): The character to set as active.
        """
        # Remove current active character for the guild, if any
        for c in cast(list["Character"], self.active_characters):
            if c.guild == guild.id:
                self.active_characters.remove(c)
                break

        # Set new active character
        self.active_characters.append(character)
        await self.save()

    async def remove_character(self, character: "Character") -> None:
        """Remove a character from the user's list of characters."""
        for c in cast(list["Character"], self.characters):
            if c.id == character.id:
                self.characters.remove(c)

        for c in cast(list["Character"], self.active_characters):
            if c.id == character.id:
                self.active_characters.remove(c)

        await self.save()


class Campaign(Document):
    """Represents a campaign in the database."""

    date_created: datetime = Field(default_factory=time_now)
    date_modified: datetime = Field(default_factory=time_now)
    date_in_game: Optional[datetime] = None
    description: str | None = None
    guild: int
    is_active: bool = False
    name: str
    # FIXME: Decide between Links or objects
    chapters: list[CampaignChapter] = Field(default_factory=list)
    notes: list[CampaignNote] = Field(default_factory=list)
    npcs: list[CampaignNPC] = Field(default_factory=list)
    # chapters: list[Link[CampaignChapter]] = Field(default_factory=list)
    # notes: list[Link[CampaignNote]] = Field(default_factory=list)
    # npcs: list[Link[CampaignNPC]] = Field(default_factory=list)

    @before_event(Insert, Replace, Save, Update, SaveChanges)
    async def update_modified_date(self) -> None:
        """Update the date_modified field."""
        self.date_modified = time_now()


class Character(Document):
    """Represents a character in the database."""

    char_class_name: str
    date_created: datetime = Field(default_factory=time_now)
    date_modified: datetime = Field(default_factory=time_now)
    guild: Indexed(int)  # type: ignore [valid-type]
    images: list[str] = Field(default_factory=list)
    is_alive: bool = True
    name_first: str
    name_last: str
    name_nick: str | None = None

    sheet_sections: list[CharacterSheetSection] = Field(default_factory=list)
    traits: list[Link["CharacterTrait"]] = Field(default_factory=list)

    type_chargen: bool = False
    type_debug: bool = False
    type_storyteller: bool = False
    type_player: bool = False
    type_developer: bool = False
    user_creator: Link[User]
    user_owner: Link[User]
    # Profile
    bio: str | None = None
    age: int | None = None
    auspice: str | None = None
    breed: str | None = None
    clan_name: str | None = None
    concept_name: str | None = None
    creed_name: str | None = None
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
        nick = f" ({self.name_nick})" if self.name_nick else ""
        last = f" {self.name_last}" if self.name_last else ""

        return f"{self.name_first}{nick}{last}".strip()

    @property
    def char_class(self) -> CharClassType:
        """Return the character's class."""
        if self.__dict__.get("char_class_name", None):
            return CharClassType[self.char_class_name]

        return None

    @property
    def concept(self) -> CharacterConcept | None:
        """Return the character's concept as an enum value if available, else a string.

        Returns:
            CharacterConcept|None: The character's concept, if it exists; otherwise, None.
        """
        if self.__dict__.get("concept_name", None):
            try:
                return CharacterConcept[self.concept_name.title()]
            except KeyError:
                return None

        return None

    @property
    def clan(self) -> VampireClan:
        """Return the character's clan."""
        if self.__dict__.get("clan_name", None):
            return VampireClan[self.clan_name]
        return None

    @property
    def creed(self) -> HunterCreed:
        """Return the user who created the character."""
        if self.__dict__.get("creed_name", None):
            return HunterCreed[self.creed_name]
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
        aws_svc.delete_object(key)  # type: ignore [attr-defined]
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
            if trait.name == name and trait.category_name == category.name:
                raise errors.TraitExistsError

        # Check if the trait is custom
        if name.lower() in [x.lower() for x in category.value.COMMON] + [
            x.lower() for x in getattr(category.value, self.char_class_name, [])
        ]:
            is_custom = False

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
