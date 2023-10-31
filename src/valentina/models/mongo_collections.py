"""MongoDB collections for Valentina."""
from datetime import datetime, timezone
from typing import Optional, Union, cast

import discord
import semver
from beanie import (
    DeleteRules,
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
    COOL_POINT_VALUE,
    CharacterConcept,
    CharClass,
    HunterCreed,
    PermissionManageCampaign,
    PermissionsGrantXP,
    PermissionsKillCharacter,
    PermissionsManageTraits,
    RollResultType,
    TraitCategory,
    VampireClan,
)
from valentina.models.aws import AWSService
from valentina.utils import errors
from valentina.utils.discord_utils import create_player_role, create_storyteller_role
from valentina.utils.helpers import get_max_trait_value, num_to_circles


def time_now() -> datetime:
    """Return the current time in UTC."""
    return datetime.now(timezone.utc).replace(microsecond=0)


# #### Sub-Documents


class GuildRollResultThumbnail(BaseModel):
    """Represents a thumbnail for a roll result as a subdocument attached to a Guild."""

    url: str
    roll_type: RollResultType
    user: int
    date_created: datetime = Field(default_factory=time_now)


class GuildPermissions(BaseModel):
    """Representation of a guild's permission settings as a subdocument attached to a Guild."""

    manage_traits: PermissionsManageTraits = PermissionsManageTraits.WITHIN_24_HOURS
    grant_xp: PermissionsGrantXP = PermissionsGrantXP.PLAYER_ONLY
    kill_character: PermissionsKillCharacter = PermissionsKillCharacter.CHARACTER_OWNER_ONLY
    manage_campaigns: PermissionManageCampaign = PermissionManageCampaign.STORYTELLER_ONLY


class GuildChannels(BaseModel):
    """Representation of a guild's channel ids as a subdocument attached to a Guild."""

    audit_log: int | None = None
    changelog: int | None = None
    error_log: int | None = None
    storyteller: int | None = None


class CampaignExperience(BaseModel):
    """Dictionary representing a character's campaign experience as a subdocument attached to a User."""

    xp_current: int = 0
    xp_total: int = 0
    cool_points: int = 0


class CampaignChapter(BaseModel):
    """Represents a chapter as a subdocument within Campaign."""

    description_long: str = None
    description_short: str = None
    name: str
    number: int
    date_created: datetime = Field(default_factory=time_now)

    def campaign_display(self) -> str:
        """Return the display for campaign overview."""
        display = f"**{self.number}: __{self.name}__**"
        display += f"\n{self.description_long}" if self.description_long else ""

        return display


class CampaignNPC(BaseModel):
    """Represents a campaign NPC as a subdocument within Campaign."""

    description: str
    name: str
    npc_class: str

    def campaign_display(self) -> str:
        """Return the display for campaign overview."""
        display = f"**{self.name}**"
        display += f" ({self.npc_class})" if self.npc_class else ""
        display += f"\n{self.description}" if self.description else ""

        return display


class CampaignNote(BaseModel):
    """Represents a campaign note as a subdocument within Campaign."""

    # TODO: Remove user-specific notes from cogs/views
    description: str
    name: str

    def campaign_display(self) -> str:
        """Return the display for campaign overview."""
        display = f"**{self.name}**\n"
        display += f"{self.description}" if self.description else ""

        return display


class CharacterSheetSection(BaseModel):
    """Represents a character sheet section as a subdocument within Character."""

    title: str
    content: str


class UserMacro(BaseModel):
    """Represents a user macro as a subdocument within User."""

    abbreviation: str
    date_created: datetime = Field(default_factory=time_now)
    description: str | None = None
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

    @property
    def most_recent_version(self) -> str:
        """Return the most recent version."""
        return max(self.versions, key=semver.Version.parse)


class Guild(Document):
    """Represents a guild in the database."""

    id: int  # type: ignore [assignment]  # noqa: A003

    active_campaign: Link["Campaign"] = None
    campaigns: list[Link["Campaign"]] = Field(default_factory=list)
    changelog_posted_version: str | None = None
    channels: GuildChannels = GuildChannels()
    date_created: datetime = Field(default_factory=time_now)
    date_modified: datetime = Field(default_factory=time_now)
    name: str
    permissions: GuildPermissions = GuildPermissions()
    roll_result_thumbnails: list[GuildRollResultThumbnail] = Field(default_factory=list)

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
        if self.channels.changelog:
            return discord.utils.get(guild.text_channels, id=self.channels.changelog)

        return None

    def fetch_storyteller_channel(self, guild: discord.Guild) -> discord.TextChannel | None:
        """Retrieve the storyteller channel for the guild from the settings.

        Fetch the guild's settings to determine if a storyteller channel has been set.  If set, return the corresponding TextChannel object; otherwise, return None.

        Args:
            guild (discord.Guild): The guild to fetch the storyteller channel for.

        Returns:
            discord.TextChannel|None: The storyteller channel, if it exists and is set; otherwise, None.
        """
        if self.channels.storyteller:
            return discord.utils.get(guild.text_channels, id=self.channels.storyteller)

        return None

    def fetch_audit_log_channel(self, guild: discord.Guild) -> discord.TextChannel | None:
        """Retrieve the audit log channel for the guild from the settings.

        Fetch the guild's settings to determine if an audit log channel has been set.  If set, return the corresponding TextChannel object; otherwise, return None.

        Args:
            guild (discord.Guild): The guild to fetch the audit log channel for.

        Returns:
            discord.TextChannel|None: The audit log channel, if it exists and is set; otherwise, None.
        """
        if self.channels.audit_log:
            return discord.utils.get(guild.text_channels, id=self.channels.audit_log)

        return None

    def fetch_error_log_channel(self, guild: discord.Guild) -> discord.TextChannel | None:
        """Retrieve the error log channel for the guild from the settings.

        Fetch the guild's settings to determine if an error log channel has been set.  If set, return the corresponding TextChannel object; otherwise, return None.

        Args:
            guild (discord.Guild): The guild to fetch the error log channel for.

        Returns:
            discord.TextChannel|None: The error log channel, if it exists and is set; otherwise, None.
        """
        if self.channels.error_log:
            return discord.utils.get(guild.text_channels, id=self.channels.error_log)

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

    async def fetch_active_campaign(self) -> "Campaign":
        """Fetch the active campaign for the guild."""
        try:
            return await Campaign.get(self.active_campaign.id, fetch_links=True)  # type: ignore [attr-defined]
        except AttributeError as e:
            raise errors.NoActiveCampaignError from e

    async def delete_campaign(self, campaign: "Campaign") -> None:
        """Delete a campaign from the guild. Remove the campaign from the guild's list of campaigns and delete the campaign from the database.

        Args:
            campaign (Campaign): The campaign to delete.
        """
        # Remove the campaign from the active campaign if it is active
        if self.active_campaign and self.active_campaign == campaign:
            self.active_campaign = None

        if campaign in self.campaigns:
            self.campaigns.remove(campaign)

        await campaign.delete(link_rule=DeleteRules.DELETE_LINKS)

        await self.save()

    async def add_roll_result_thumb(
        self, ctx: discord.ApplicationContext, roll_type: RollResultType, url: str
    ) -> None:
        """Add a roll result thumbnail to the database."""
        for thumb in self.roll_result_thumbnails:
            if thumb.url == url:
                msg = "That thumbnail already exists"
                raise errors.ValidationError(msg)

        self.roll_result_thumbnails.append(
            GuildRollResultThumbnail(url=url, roll_type=roll_type, user=ctx.author.id)
        )
        await self.save()

        logger.info(
            f"DATABASE: Add '{RollResultType.name}' roll result thumbnail for '{ctx.guild.name}'"
        )


class User(Document):
    """Represents a user in the database."""

    id: int  # type: ignore [assignment]  # noqa: A003

    active_characters: dict[str, Link["Character"]] = Field(default_factory=dict)
    characters: list[Link["Character"]] = Field(default_factory=list)
    campaign_experience: dict[str, CampaignExperience] = Field(default_factory=dict)
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
        xp = 0

        for obj in self.campaign_experience.values():
            xp += obj.xp_total

        return xp

    @property
    def lifetime_cool_points(self) -> int:
        """Return the user's lifetime cool points."""
        cool_points = 0

        for obj in self.campaign_experience.values():
            cool_points += obj.cool_points

        return cool_points

    def _find_campaign_xp(self, campaign: "Campaign") -> CampaignExperience | None:
        """Return the user's campaign experience for a given campaign.

        Args:
            campaign (Campaign): The campaign to fetch experience for.

        Returns:
            CampaignExperience|None: The user's campaign experience if it exists; otherwise, None.
        """
        try:
            return self.campaign_experience[str(campaign.id)]
        except KeyError as e:
            raise errors.NoExperienceInCampaignError from e

    def fetch_campaign_xp(self, campaign: "Campaign") -> tuple[int, int, int]:
        """Return the user's campaign experience for a given campaign.

        Args:
            campaign (Campaign): The campaign to fetch experience for.

        Returns:
            tuple[int, int, int]: Tuple of (current xp, total xp, cool points) if the user has experience for the campaign; otherwise, None.
        """
        campaign_experience = self._find_campaign_xp(campaign)

        return (
            campaign_experience.xp_current,
            campaign_experience.xp_total,
            campaign_experience.cool_points,
        )

    async def spend_campaign_xp(self, campaign: "Campaign", amount: int) -> int:
        """Spend experience for a campaign.

        Args:
            campaign (Campaign): The campaign to spend experience for.
            amount (int): The amount of experience to spend.

        Returns:
            int: The new campaign experience.
        """
        campaign_experience = self._find_campaign_xp(campaign)

        new_xp = campaign_experience.xp_current - amount

        if new_xp < 0:
            msg = f"Can not spend {amount} xp with only {campaign_experience.xp_current} available"
            raise errors.NotEnoughExperienceError(msg)

        campaign_experience.xp_current = new_xp
        await self.save()

        return new_xp

    async def add_campaign_xp(self, campaign: "Campaign", amount: int) -> int:
        """Add experience for a campaign.

        Args:
            campaign (Campaign): The campaign to add experience for.
            amount (int): The amount of experience to add.

        Returns:
            int: The new campaign experience.
        """
        try:
            campaign_experience = self._find_campaign_xp(campaign)
        except errors.NoExperienceInCampaignError:
            campaign_experience = CampaignExperience()
            self.campaign_experience[str(campaign.id)] = campaign_experience

        campaign_experience.xp_current += amount
        campaign_experience.xp_total += amount
        await self.save()

        return campaign_experience.xp_current

    async def add_campaign_cool_points(self, campaign: "Campaign", amount: int) -> int:
        """Add cool points and increase experience for the current campaign.

        Args:
            campaign (Campaign): The campaign to add cool points for.
            amount (int): The amount of cool points to add.

        Returns:
            int: The new campaign cool points.
        """
        campaign_experience = self._find_campaign_xp(campaign)

        campaign_experience.cool_points += amount
        campaign_experience.xp_total += amount * COOL_POINT_VALUE
        campaign_experience.xp_current += amount * COOL_POINT_VALUE
        await self.save()

        return campaign_experience.cool_points

    async def active_character(self, guild: discord.Guild, raise_error: bool = True) -> "Character":
        """Return the active character for the user in the guild."""
        try:
            active_char_id = self.active_characters[str(guild.id)].id  # type: ignore [attr-defined]
        except KeyError as e:
            if raise_error:
                raise errors.NoActiveCharacterError from e
            return None

        return await Character.get(active_char_id, fetch_links=True)  # type: ignore [attr-defined]

    def all_characters(self, guild: discord.Guild) -> list["Character"]:
        """Return all characters for the user in the guild."""
        return [x for x in cast(list["Character"], self.characters) if x.guild == guild.id]

    async def set_active_character(self, character: "Character") -> None:
        """Set the active character for the user in the guild.

        Args:
            character (Character): The character to set as active.
        """
        self.active_characters[str(character.guild)] = character
        await self.save()

    async def remove_character(self, character: "Character") -> None:
        """Remove a character from the user's list of characters."""
        # Remove the character from the active characters list if it is active
        if (
            str(character.guild) in self.active_characters
            and self.active_characters[str(character.guild)].id == character.id  # type: ignore [attr-defined]
        ):
            del self.active_characters[str(character.guild)]

        # Remove the character from the list of characters
        for c in cast(list["Character"], self.characters):
            if c.id == character.id:
                self.characters.remove(c)

        await self.save()


class Campaign(Document):
    """Represents a campaign in the database."""

    date_created: datetime = Field(default_factory=time_now)
    date_modified: datetime = Field(default_factory=time_now)
    date_in_game: Optional[datetime] = None
    description: str | None = None
    guild: int
    name: str
    # FIXME: Decide between Links or objects
    chapters: list[CampaignChapter] = Field(default_factory=list)
    notes: list[CampaignNote] = Field(default_factory=list)
    npcs: list[CampaignNPC] = Field(default_factory=list)

    @before_event(Insert, Replace, Save, Update, SaveChanges)
    async def update_modified_date(self) -> None:
        """Update the date_modified field."""
        self.date_modified = time_now()


class Character(Document):
    """Represents a character in the database."""

    char_class_name: str  # CharClass enum name
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
    user_creator: int  # id of the user who created the character
    user_owner: int  # id of the user who owns the character
    freebie_points: int = 0

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

    async def fetch_owner(self, fetch_links: bool = True) -> User:
        """Fetch the user who owns the character."""
        return await User.get(self.user_owner, fetch_links=fetch_links)

    async def fetch_trait_by_name(self, name: str) -> Union["CharacterTrait", None]:
        """Fetch a CharacterTrait by name."""
        for trait in cast(list[CharacterTrait], self.traits):
            if trait.name == name:
                return trait

        return None


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


class RollProbability(Document):
    """Represents a roll probability in the database."""

    # Metadata
    pool: Indexed(int)  # type: ignore [valid-type]
    difficulty: Indexed(int)  # type: ignore [valid-type]
    dice_size: Indexed(int)  # type: ignore [valid-type]
    created: datetime = Field(default_factory=time_now)

    # Results
    total_results: float
    botch_dice: float
    success_dice: float
    failure_dice: float
    critical_dice: float
    total_successes: float
    total_failures: float
    # The name of each value in the RollResultType enum
    BOTCH: float
    CRITICAL: float
    FAILURE: float
    SUCCESS: float
    OTHER: float


class RollStatistic(Document):
    """Track roll results for statistics."""

    user: Indexed(int)  # type: ignore [valid-type]
    guild: Indexed(int)  # type: ignore [valid-type]
    character: Indexed(str) | None = None  # type: ignore [valid-type]
    result: RollResultType  # type: ignore [valid-type]
    pool: int
    difficulty: int
    date_rolled: datetime = Field(default_factory=time_now)
    traits: list[str] = Field(default_factory=list)
