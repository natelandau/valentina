"""Models for the database."""
import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import dotenv_values
from peewee import (
    BooleanField,
    DateTimeField,
    DeferredForeignKey,
    ForeignKeyField,
    IntegerField,
    Model,
    TextField,
)
from playhouse.sqlite_ext import CSqliteExtDatabase


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


class Guild(BaseModel):
    """Guild model for the database."""

    id = IntegerField(primary_key=True)  # noqa: A003
    name = TextField()
    created = DateTimeField(default=time_now)
    modified = DateTimeField(default=time_now)
    log_channel_id = IntegerField(null=True)
    use_audit_log = BooleanField(default=False)
    xp_permissions = IntegerField(default=0)
    trait_permissions = IntegerField(default=0)
    use_storyteller_channel = BooleanField(default=False)
    storyteller_channel_id = IntegerField(null=True)

    def __str__(self) -> str:
        """Return the string representation of the model."""
        return f"[{self.id}] {self.name}"

    class Meta:
        """Meta class for the model."""

        table_name = "guilds"


class User(BaseModel):
    """User model for the database."""

    id = IntegerField(primary_key=True)  # noqa: A003
    username = TextField(null=True)
    name = TextField(null=True)
    avatar_url = TextField(null=True)
    first_seen = DateTimeField(default=time_now)
    mention = TextField(null=True)
    last_seen = DateTimeField(default=time_now)

    class Meta:
        """Meta class for the model."""

        table_name = "users"


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


class Macro(BaseModel):
    """Macros for quick dice rolls."""

    name = TextField()
    abbreviation = TextField()
    description = TextField(null=True)
    created = DateTimeField(default=time_now)
    modified = DateTimeField(default=time_now)
    guild = ForeignKeyField(Guild, backref="macros")
    user = ForeignKeyField(User, backref="macros")

    def remove(self) -> None:
        """Delete the macro and associated macro traits."""
        for mt in self.traits:
            mt.delete_instance()

        super().delete_instance()

    class Meta:
        """Meta class for the model."""

        table_name = "macros"


class RollThumbnail(BaseModel):
    """Thumbnail for a roll."""

    url = TextField()
    roll_type = TextField()
    created = DateTimeField(default=time_now)
    guild = ForeignKeyField(Guild, backref="roll_thumbnails")
    user = ForeignKeyField(User, backref="roll_thumbnails")

    class Meta:
        """Meta class for the model."""

        table_name = "roll_thumbnails"


class Character(BaseModel):
    """Character model for the database."""

    # GENERAL ####################################
    first_name = TextField()
    last_name = TextField(null=True)
    nickname = TextField(null=True)
    created = DateTimeField(default=time_now)
    modified = DateTimeField(default=time_now)
    storyteller_character = BooleanField(default=False)
    # Foreign Keys ###############################
    char_class = ForeignKeyField(CharacterClass, backref="characters")
    guild = ForeignKeyField(Guild, backref="characters")
    claimed_by = ForeignKeyField(User, backref="claimed_character", null=True)
    created_by = ForeignKeyField(User, backref="created_characters")
    owned_by = ForeignKeyField(User, backref="owned_characters", null=True)
    clan = ForeignKeyField(VampireClan, backref="characters", null=True)
    # Character Sheet ############################
    alive = BooleanField(default=True)
    age = IntegerField(null=True)
    archived = BooleanField(default=False)
    bio = TextField(null=True)
    concept = TextField(null=True)
    cool_points = IntegerField(default=0)
    cool_points_total = IntegerField(default=0)
    experience = IntegerField(default=0)
    experience_total = IntegerField(default=0)
    # Profile ############################
    nature = TextField(null=True)
    demeanor = TextField(null=True)
    generation = TextField(null=True)  # Vampire
    sire = TextField(null=True)  # Vampire
    breed = TextField(null=True)  # Werewolf
    tribe = TextField(null=True)  # Werewolf
    auspice = TextField(null=True)  # Werewolf
    essence = TextField(null=True)  # Mage
    tradition = TextField(null=True)  # Mage
    date_of_birth = DateTimeField(null=True, formats=["%Y-%m-%d"])

    @property
    def name(self) -> str:
        """Return the name of the character."""
        display_name = f"{self.first_name.title()}"
        display_name += f" ({self.nickname.title()})" if self.nickname else ""
        display_name += f" {self.last_name.title() }" if self.last_name else ""
        return display_name

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
            list[Trait | CustomTrait]: List of all traits and custom traits when flat_traits is True.
        """
        all_traits = []
        for tv in TraitValue.select().where(TraitValue.character == self):
            all_traits.append(tv.trait)

        for ct in self.custom_traits:
            all_traits.append(ct)

        return sorted(list(set(all_traits)), key=lambda x: x.name)

    @property
    def traits_dict(self) -> dict[str, list[Trait | CustomTrait]]:
        """Fetch all traits for this character.

        Returns:
            dict[str, list[Trait | CustomTrait]]: Dictionary of traits and custom traits with trait category as the key.
        """
        all_traits: dict[str, list[Trait | CustomTrait]] = {}

        for tv in TraitValue.select().where(TraitValue.character == self):
            category = str(tv.trait.category.name)

            if category not in all_traits:
                all_traits[category] = []

            all_traits[category].append(tv.trait)

        for ct in self.custom_traits:
            category = str(ct.category.name)

            if category not in all_traits:
                all_traits[category] = []

            all_traits[category].append(ct)

        return all_traits

    @property
    def all_trait_values(self) -> dict[str, list[tuple[str, int, int, str]]]:
        """Fetch all trait values for a character inclusive of common and custom for display on a character sheet.

        Returns:
            dict[str, list[tuple[str, int, int, str]]]: Dictionary key is category. Values are a tuple of (trait name, trait value, trait max value, trait dots)

        Example:
            {
                "Physical": [("Strength", 3, 5, "●●●○○"), ("Agility", 2, 5, "●●●○○")],
                "Social": [("Persuasion", 1, 5, "●○○○○")]
            }
        """
        from valentina.utils.helpers import get_max_trait_value, num_to_circles

        all_traits: dict[str, list[tuple[str, int, int, str]]] = {}

        for category, traits in self.traits_dict.items():
            if category not in all_traits:
                all_traits[category] = []

            for trait in traits:
                if isinstance(trait, Trait):
                    value = TraitValue.get(
                        TraitValue.character == self, TraitValue.trait == trait
                    ).value

                if isinstance(trait, CustomTrait):
                    value = trait.value

                max_value = get_max_trait_value(trait=trait.name, category=category)
                dots = num_to_circles(value, max_value)
                all_traits[category].append((trait.name, value, max_value, dots))

        return all_traits

    def trait_value(self, trait: Trait | CustomTrait) -> int:
        """Return the character's value of a trait."""
        try:
            if isinstance(trait, Trait):
                return TraitValue.get(TraitValue.character == self, TraitValue.trait == trait).value

            return trait.value  # custom traits
        except TraitValue.DoesNotExist:
            return 0

    def __str__(self) -> str:
        """Return the string representation of the model."""
        return f"[{self.id}] {self.name}"

    class Meta:
        """Meta class for the model."""

        table_name = "characters"


###### Chronicle Models ######
class Chronicle(BaseModel):
    """Chronicle model for the database."""

    name = TextField(unique=True)
    description = TextField(null=True)
    created = DateTimeField(default=time_now)
    modified = DateTimeField(default=time_now)
    guild = ForeignKeyField(Guild, backref="chronicles")
    current_date = DateTimeField(null=True, formats=["%Y-%m-%d"])
    is_active = BooleanField(default=False)

    def remove(self) -> None:
        """Delete the macro and associated macro traits."""
        for npc in self.npcs:
            npc.delete_instance()

        for note in self.notes:
            note.delete_instance()

        for chap in self.chapters:
            chap.delete_instance()

        super().delete_instance()

    class Meta:
        """Meta class for the model."""

        table_name = "chronicles"


class ChronicleNPC(BaseModel):
    """NPC model for the database."""

    name = TextField()
    description = TextField(null=True)
    npc_class = TextField(null=True)
    alive = BooleanField(default=True)
    created = DateTimeField(default=time_now)
    modified = DateTimeField(default=time_now)
    chronicle = ForeignKeyField(Chronicle, backref="npcs")

    class Meta:
        """Meta class for the model."""

        table_name = "chronicle_npcs"

    def chronicle_display(self) -> str:
        """Return the display for chronicle overview."""
        display = f"**{self.name}**"
        display += f" ({self.npc_class})" if self.npc_class else ""
        display += f"\n{self.description}" if self.description else ""

        return display


class ChronicleChapter(BaseModel):
    """Chronicle Chapter model for the database."""

    chapter = IntegerField()
    name = TextField(null=True)
    date = DateTimeField(null=True)
    short_description = TextField(null=True)
    description = TextField(null=True)
    created = DateTimeField(default=time_now)
    modified = DateTimeField(default=time_now)
    chronicle = ForeignKeyField(Chronicle, backref="chapters")

    class Meta:
        """Meta class for the model."""

        table_name = "chronicle_chapters"

    def chronicle_display(self) -> str:
        """Return the display for chronicle overview."""
        display = f"**{self.chapter}: __{self.name}__**"
        display += f"\n{self.description}" if self.description else ""

        return display


class ChronicleNote(BaseModel):
    """Notes for a chronicle."""

    name = TextField()
    description = TextField(null=True)
    created = DateTimeField(default=time_now)
    modified = DateTimeField(default=time_now)
    chronicle = ForeignKeyField(Chronicle, backref="notes")
    user = ForeignKeyField(User, backref="chronicle_notes")
    chapter = ForeignKeyField(ChronicleChapter, backref="notes", null=True)
    private = BooleanField(default=False)

    class Meta:
        """Meta class for the model."""

        table_name = "chronicle_notes"

    def chronicle_display(self) -> str:
        """Return the display for chronicle overview."""
        display = f"**{self.name}**"
        display += f"{self.description}" if self.description else ""

        return display


# Lookup tables


class GuildUser(BaseModel):
    """Join table for Guild and User."""

    guild = ForeignKeyField(Guild, backref="users")
    user = ForeignKeyField(User, backref="guilds")


class MacroTrait(BaseModel):
    """Join table for Macro and Trait."""

    macro = ForeignKeyField(Macro, backref="traits")
    trait = ForeignKeyField(Trait, backref="macros", null=True)
    custom_trait = ForeignKeyField(CustomTrait, backref="macros", null=True)

    class Meta:
        """Meta class for the model."""

        table_name = "macro_traits"
        indexes = (
            (("macro", "trait"), False),
            (("macro", "custom_trait"), False),
        )


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
