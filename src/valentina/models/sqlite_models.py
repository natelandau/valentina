"""Models for the database."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import dotenv_values
from peewee import (
    BooleanField,
    DateTimeField,
    DeferredForeignKey,
    DoesNotExist,
    ForeignKeyField,
    IntegerField,
    Model,
    TextField,
)
from playhouse.sqlite_ext import CSqliteExtDatabase, JSONField

from valentina.utils import errors


# This is duplicated from valentina.utils.helpers to avoid circular imports
def time_now() -> datetime:
    """Return the current time in UTC."""
    return datetime.now(timezone.utc).replace(microsecond=0)


# Import configuration from environment variables
env_dir = Path(__file__).parents[3].absolute()
config = {
    **dotenv_values(env_dir / ".env"),  # load shared variables
    **dotenv_values(env_dir / ".env.secrets"),  # load sensitive variables
    **os.environ,  # override loaded values with environment variables
}
for k, v in config.items():
    config[k] = v.replace('"', "").replace("'", "").replace(" ", "")


# Instantiate Database
DATABASE = CSqliteExtDatabase(
    config["VALENTINA_DB_PATH"],
    pragmas={
        "journal_mode": "wal",
        "cache_size": -1 * 64000,  # 64MB
        "foreign_keys": 1,
        "ignore_check_constraints": 0,
        "synchronous": 1,
    },
)


class BaseModel(Model):
    """Base model for the database."""

    class Meta:
        """Meta class for the database, inherited by all subclasses."""

        database = DATABASE

    def __str__(self) -> str:
        """Return the string representation of the model."""
        return str(self.__dict__)


class DatabaseVersion(BaseModel):
    """Database version model for the database."""

    version = TextField()
    date = DateTimeField(default=time_now)


class Guild(BaseModel):
    """Guild model for the database."""

    id = IntegerField(primary_key=True)  # noqa: A003
    name = TextField()
    created = DateTimeField(default=time_now)
    data = JSONField(null=True)

    def __str__(self) -> str:
        """Return the string representation of the model."""
        return f"[{self.id}] {self.name}"

    class Meta:
        """Meta class for the model."""

        table_name = "guilds"


class GuildUser(BaseModel):
    """Table for storing information specific to users on a guild."""

    guild = ForeignKeyField(Guild, backref="users")
    user = IntegerField()
    data = JSONField(null=True)

    def __str__(self) -> str:
        """Return the string representation of the model."""
        return f"[{self.data['id']}] {self.data['display_name']}"

    def fetch_experience(self, campaign_id: int) -> tuple[int, int, int, int, int]:
        """Fetch the experience for a user for a specific campaign.

        Args:
            campaign_id (int): The campaign ID to fetch experience for.

        Returns:
            tuple[int, int, int, int, int]: The campaign experience, campaign total experience, lifetime experience, campaign total cool points, and lifetime cool points.
        """
        campaign_xp = self.data.get(f"{campaign_id}_experience", 0)
        campaign_total_xp = self.data.get(f"{campaign_id}_total_experience", 0)
        campaign_total_cp = self.data.get(f"{campaign_id}_total_cool_points", 0)
        lifetime_xp = self.data.get("lifetime_experience", 0)
        lifetime_cp = self.data.get("lifetime_cool_points", 0)

        return campaign_xp, campaign_total_xp, lifetime_xp, campaign_total_cp, lifetime_cp

    def add_experience(self, campaign_id: int, amount: int) -> tuple[int, int, int]:
        """Set the experience for a user for a specific campaign.

        Args:
            campaign_id (int): The campaign ID to set experience for.
            amount (int): The amount of experience to set.

        Returns:
            tuple[int, int, int]: The campaign experience, campaign total experience, and lifetime experience.
        """
        (
            campaign_xp,
            campaign_total_xp,
            lifetime_xp,
            _,
            _,
        ) = self.fetch_experience(campaign_id)

        new_xp = self.data[f"{campaign_id}_experience"] = campaign_xp + amount
        new_total = self.data[f"{campaign_id}_total_experience"] = campaign_total_xp + amount
        new_lifetime_total = self.data["lifetime_experience"] = lifetime_xp + amount

        self.save()

        return new_xp, new_total, new_lifetime_total

    def add_cool_points(self, campaign_id: int, amount: int) -> tuple[int, int]:
        """Set the cool points for a user for a specific campaign.

        Args:
            campaign_id (int): The campaign ID to set cool points for.
            amount (int): The amount of cool points to set.

        Returns:
            tuple[int, int]: The campaign total cool points and lifetime cool points.
        """
        (
            _,
            _,
            _,
            campaign_total_cp,
            lifetime_cp,
        ) = self.fetch_experience(campaign_id)

        new_total = self.data[f"{campaign_id}_total_cool_points"] = campaign_total_cp + amount
        new_lifetime = self.data["lifetime_cool_points"] = lifetime_cp + amount

        self.save()

        return new_total, new_lifetime

    def spend_experience(self, campaign_id: int, amount: int) -> int:
        """Spend experience for a user for a specific campaign.

        Args:
            campaign_id (int): The campaign ID to spend experience for.
            amount (int): The amount of experience to spend.

        Returns:
            int: The new campaign experience.
        """
        (
            campaign_xp,
            _,
            _,
            _,
            _,
        ) = self.fetch_experience(campaign_id)

        new_xp = self.data[f"{campaign_id}_experience"] = campaign_xp - amount

        if new_xp < 0:
            msg = f"Can not spend {amount} xp with only {campaign_xp} available"
            raise errors.NotEnoughExperienceError(msg)

        self.save()

        return new_xp


class CharacterClass(BaseModel):
    """Character Class model for the database."""

    name = TextField(unique=True)

    class Meta:
        """Meta class for the model."""

        table_name = "character_classes"


class VampireClan(BaseModel):
    """Vampire clans."""

    name = TextField(unique=True)

    class Meta:
        """Meta class for the model."""

        table_name = "vampire_clans"


###### Traits ######


class TraitCategory(BaseModel):
    """Trait Category model for the database."""

    name = TextField(unique=True)

    class Meta:
        """Meta class for the model."""

        table_name = "trait_categories"


class CustomTrait(BaseModel):
    """Custom Trait model for the database."""

    character = DeferredForeignKey("Character", backref="custom_traits")
    created = DateTimeField(default=time_now)
    modified = DateTimeField(default=time_now)
    description = TextField(null=True)
    name = TextField()
    category = ForeignKeyField(TraitCategory, backref="custom_traits")
    value = IntegerField(default=0)
    max_value = IntegerField(default=0)

    class Meta:
        """Meta class for the model."""

        table_name = "custom_traits"


class Trait(BaseModel):
    """Character Trait model for the database."""

    name = TextField(unique=True)
    category = ForeignKeyField(TraitCategory, backref="traits")

    class Meta:
        """Meta class for the model."""

        table_name = "traits"


###### Characters ######


class CustomSection(BaseModel):
    """Custom sections added to a character sheet."""

    character = DeferredForeignKey("Character", backref="custom_sections")
    created = DateTimeField(default=time_now)
    modified = DateTimeField(default=time_now)
    description = TextField(null=True)
    title = TextField()

    class Meta:
        """Meta class for the model."""

        table_name = "custom_sections"


class Character(BaseModel):
    """Character model for the database."""

    # GENERAL ####################################
    created = DateTimeField(default=time_now)
    data = JSONField(null=True)

    # Foreign Keys ###############################
    char_class = ForeignKeyField(CharacterClass, backref="characters")
    guild = ForeignKeyField(Guild, backref="characters")
    created_by = ForeignKeyField(GuildUser, backref="created_characters", null=True)
    owned_by = ForeignKeyField(GuildUser, backref="owned_characters", null=True)
    clan = ForeignKeyField(VampireClan, backref="characters", null=True)

    @property
    def name(self) -> str:
        """Return the name of the character including their nickname."""
        first_name = self.data.get("first_name", "")
        last_name = self.data.get("last_name", "")
        nickname = self.data.get("nickname", "")

        display_name = f"{first_name.title()}"
        display_name += f" ({nickname.title()})" if nickname else ""
        display_name += f" {last_name.title()}" if last_name else ""

        return display_name

    @property
    def full_name(self) -> str:
        """Return the first and last name of the character."""
        first_name = self.data.get("first_name", "")
        last_name = self.data.get("last_name", "")

        display_name = f"{first_name.title()}"
        display_name += f" {last_name.title()}" if last_name else ""
        return display_name

    @property
    def freebie_points(self) -> int:
        """Return the number of freebie points the character has available."""
        return self.data.get("freebie_points", 0)

    @property
    def class_name(self) -> str:
        """Return the character's class from the char_class table."""
        return self.char_class.name

    @property
    def clan_name(self) -> str:
        """Return the character's clan from the vampire_clans table."""
        return self.clan.name

    @property
    def traits_list(self) -> list[Trait | CustomTrait]:
        """Fetch all traits for this character.

        Returns:
            list[Trait | CustomTrait]: List of all traits and custom traits.
        """
        all_traits = []

        all_traits.extend(
            [tv.trait for tv in TraitValue.select().where(TraitValue.character == self)]
        )

        all_traits.extend(list(self.custom_traits))

        return sorted(set(all_traits), key=lambda x: x.name)

    @property
    def traits_dict(self) -> dict[str, list[Trait | CustomTrait]]:
        """Fetch all traits for this character.

        Returns:
            dict[str, list[Trait | CustomTrait]]: Dictionary of traits and custom traits with trait category as the key.
        """
        all_traits: dict[str, list[Trait | CustomTrait]] = {}

        for tv in TraitValue.select().where(TraitValue.character == self):
            category = str(tv.trait.category.name)
            all_traits.setdefault(category, [])
            all_traits[category].append(tv.trait)

        for ct in self.custom_traits:
            category = str(ct.category.name)
            all_traits.setdefault(category, [])
            all_traits[category].append(ct)

        return all_traits

    @property
    def all_trait_values(self) -> dict[str, list[tuple[str, int, int, str]]]:
        """Fetch all trait values for a character inclusive of common and custom for display on a character sheet.

        Returns:
            dict[str, list[tuple[str, int, int, str]]]: Dictionary key is category. Values are a tuple of (trait name, trait value, trait max value, trait dots)

        Example:
            {
                "PHYSICAL": [("Strength", 3, 5, "●●●○○"), ("Agility", 2, 5, "●●●○○")],
                "SOCIAL": [("Persuasion", 1, 5, "●○○○○")]
            }
        """
        from valentina.utils.helpers import get_max_trait_value, num_to_circles

        all_traits: dict[str, list[tuple[str, int, int, str]]] = {}

        for category, traits in self.traits_dict.items():
            all_traits.setdefault(category, [])

            for trait in traits:
                value = self.get_trait_value(trait)

                max_value = get_max_trait_value(trait=trait.name, category=category)
                dots = num_to_circles(value, max_value)
                all_traits[category].append((trait.name, value, max_value, dots))

        return all_traits

    def get_trait_value(self, trait: Trait | CustomTrait) -> int:
        """Return the character's value of a trait. If the trait is not found, return 0.

        Returns:
            int: The character's value of the trait.
        """
        try:
            if isinstance(trait, Trait):
                return TraitValue.get(TraitValue.character == self, TraitValue.trait == trait).value
        except DoesNotExist:
            return 0

        return trait.value  # custom traits

    @property
    def is_active(self) -> bool:
        """Return True if the character is set as active."""
        return self.data.get("is_active", False)

    @property
    def is_alive(self) -> bool:
        """Return True if the character is alive."""
        return self.data.get("is_alive", True)

    def kill(self) -> None:
        """Set the character as dead."""
        self.data["is_alive"] = False
        self.data["is_active"] = False
        self.save()

    def set_trait_value(self, trait: Trait | CustomTrait, value: int) -> None:
        """Set the character's value of a trait."""
        if isinstance(trait, CustomTrait):
            trait.value = value
            trait.modified = time_now()
            trait.save()

        elif isinstance(trait, Trait):
            trait_value, created = TraitValue.get_or_create(
                character=self, trait=trait, defaults={"value": value, "modified": time_now()}
            )

            if not created:
                trait_value.value = value
                trait_value.modified = time_now()
                trait_value.save()

        self.data["modified"] = str(time_now())
        self.save()

    def __str__(self) -> str:
        """Return the string representation of the model."""
        return f"[{self.id}] {self.name}"

    class Meta:
        """Meta class for the model."""

        table_name = "characters"


###### Macros ######


class Macro(BaseModel):
    """Macros for quick dice rolls."""

    name = TextField()
    abbreviation = TextField()
    description = TextField(null=True)
    created = DateTimeField(default=time_now)
    modified = DateTimeField(default=time_now)
    guild = ForeignKeyField(Guild, backref="macros")
    user = ForeignKeyField(GuildUser, backref="macros")

    def remove(self) -> None:
        """Delete the macro and associated macro traits."""
        for mt in self.traits:
            mt.delete_instance()

        super().delete_instance()

    class Meta:
        """Meta class for the model."""

        table_name = "macros"


class MacroTrait(BaseModel):
    """Join table for Macro and Trait."""

    macro = ForeignKeyField(Macro, backref="traits")
    trait = ForeignKeyField(Trait, backref="macros", null=True)
    custom_trait = ForeignKeyField(CustomTrait, backref="macros", null=True)

    @classmethod
    def create_from_trait_name(cls, macro: Macro, trait_name: str) -> MacroTrait:
        """Create a MacroTrait for the given macro and trait_name."""
        try:
            trait = Trait.get(Trait.name == trait_name)
            return cls.create(macro=macro, trait=trait)
        except DoesNotExist:
            custom_trait = CustomTrait.get(CustomTrait.name == trait_name)
            return cls.create(macro=macro, custom_trait=custom_trait)

    @classmethod
    def create_from_trait(cls, macro: Macro, trait: Trait | CustomTrait) -> MacroTrait:
        """Create a MacroTrait for the given macro and trait."""
        if isinstance(trait, Trait):
            return cls.create(macro=macro, trait=trait)

        return cls.create(macro=macro, custom_trait=trait)

    class Meta:
        """Meta class for the model."""

        table_name = "macro_traits"
        indexes = (
            (("macro", "trait"), False),
            (("macro", "custom_trait"), False),
        )


###### Campaign Models ######


class Campaign(BaseModel):
    """Campaign model for the database."""

    guild = ForeignKeyField(Guild, backref="campaigns")
    created = DateTimeField(default=time_now)
    modified = DateTimeField(default=time_now)
    name = TextField(unique=True)
    description = TextField(null=True)
    current_date = DateTimeField(null=True, formats=["%Y-%m-%d"])
    is_active = BooleanField(default=False)
    data = JSONField(null=True)

    class Meta:
        """Meta class for the model."""

        table_name = "campaigns"


class CampaignNPC(BaseModel):
    """NPC model for the database."""

    campaign = ForeignKeyField(Campaign, backref="npcs")
    created = DateTimeField(default=time_now)
    modified = DateTimeField(default=time_now)

    name = TextField()
    description = TextField(null=True)
    npc_class = TextField(null=True)
    data = JSONField(null=True)

    class Meta:
        """Meta class for the model."""

        table_name = "campaign_npcs"

    def campaign_display(self) -> str:
        """Return the display for campaign overview."""
        display = f"**{self.name}**"
        display += f" ({self.npc_class})" if self.npc_class else ""
        display += f"\n{self.description}" if self.description else ""

        return display


class CampaignChapter(BaseModel):
    """Campaign Chapter model for the database."""

    campaign = ForeignKeyField(Campaign, backref="chapters")
    created = DateTimeField(default=time_now)
    modified = DateTimeField(default=time_now)
    chapter_number = IntegerField()
    name = TextField(null=True)
    short_description = TextField(null=True)
    description = TextField(null=True)
    data = JSONField(null=True)

    class Meta:
        """Meta class for the model."""

        table_name = "campaign_chapters"

    def campaign_display(self) -> str:
        """Return the display for campaign overview."""
        display = f"**{self.chapter_number}: __{self.name}__**"
        display += f"\n{self.description}" if self.description else ""

        return display


class CampaignNote(BaseModel):
    """Notes for a campaign."""

    campaign = ForeignKeyField(Campaign, backref="notes")
    chapter = ForeignKeyField(CampaignChapter, backref="notes", null=True)
    user = ForeignKeyField(GuildUser, backref="campaign_notes")
    created = DateTimeField(default=time_now)
    modified = DateTimeField(default=time_now)
    name = TextField()
    description = TextField(null=True)
    data = JSONField(null=True)

    class Meta:
        """Meta class for the model."""

        table_name = "campaign_notes"

    def campaign_display(self) -> str:
        """Return the display for campaign overview."""
        display = f"**{self.name}**\n"
        display += f"{self.description}" if self.description else ""

        return display


###### Dice Rolls ######


class RollThumbnail(BaseModel):
    """Thumbnail for a roll."""

    url = TextField()
    roll_type = TextField()
    created = DateTimeField(default=time_now)
    guild = ForeignKeyField(Guild, backref="roll_thumbnails")
    user = ForeignKeyField(GuildUser, backref="roll_thumbnails")
    data = JSONField(null=True)

    class Meta:
        """Meta class for the model."""

        table_name = "roll_thumbnails"


class RollStatistic(BaseModel):
    """Track roll results for statistics."""

    user = ForeignKeyField(GuildUser, backref="roll_statistics")
    guild = ForeignKeyField(Guild, backref="roll_statistics")
    character = ForeignKeyField(Character, backref="roll_statistics", null=True)
    result = TextField()
    pool = IntegerField()
    difficulty = IntegerField()
    date_rolled = DateTimeField(default=time_now)
    data = JSONField(null=True)


class RollProbability(BaseModel):
    """Track proability of roll results."""

    pool = IntegerField()
    difficulty = IntegerField()
    dice_size = IntegerField()
    created = DateTimeField(default=time_now)
    data = JSONField(null=True)


###### Lookup Tables ######


class TraitValue(BaseModel):
    """Join table for Character and Trait."""

    character = ForeignKeyField(Character, backref="trait_values")
    trait = ForeignKeyField(Trait, backref="trait_values", null=True)
    value = IntegerField(default=0)
    modified = DateTimeField(default=time_now)

    class Meta:
        """Meta class for the model."""

        table_name = "trait_values"
        indexes = ((("character", "trait", "value"), False),)


class TraitClass(BaseModel):
    """Join table for Trait and CharacterClass."""

    trait = ForeignKeyField(Trait, backref="classes")
    character_class = ForeignKeyField(CharacterClass, backref="traits")

    class Meta:
        """Meta class for the model."""

        table_name = "trait_classes"
        indexes = (
            (("trait", "character_class"), False),
            (("character_class", "trait"), False),
        )


class TraitCategoryClass(BaseModel):
    """Join table for TraitCategory and CharacterClass."""

    category = ForeignKeyField(TraitCategory, backref="classes")
    character_class = ForeignKeyField(CharacterClass, backref="trait_categories")

    class Meta:
        """Meta class for the model."""

        table_name = "trait_category_classes"
        indexes = (
            (("category", "character_class"), False),
            (("character_class", "category"), False),
        )
