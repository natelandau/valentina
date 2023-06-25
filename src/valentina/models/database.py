"""Models for the database."""
from datetime import datetime, timezone

from peewee import BooleanField, DateTimeField, ForeignKeyField, IntegerField, Model, TextField

from valentina import DATABASE


def time_now() -> datetime:
    """Return the current time in UTC."""
    return datetime.now(timezone.utc).replace(microsecond=0)


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
    first_seen = DateTimeField(default=time_now)
    last_connected = DateTimeField(default=time_now)


class User(BaseModel):
    """User model for the database."""

    id = IntegerField(primary_key=True)  # noqa: A003
    username = TextField(null=True)
    name = TextField(null=True)
    avatar_url = TextField(null=True)
    first_seen = DateTimeField(default=time_now)
    mention = TextField(null=True)
    last_seen = DateTimeField(default=time_now)


class CharacterClass(BaseModel):
    """Character Class model for the database."""

    name = TextField(unique=True)


class Character(BaseModel):
    """Character model for the database."""

    # GENERAL ####################################
    first_name = TextField()
    last_name = TextField(null=True)
    nickname = TextField(null=True)
    char_class = ForeignKeyField(CharacterClass, backref="characters")
    guild = ForeignKeyField(Guild, backref="characters")
    claimed_by = ForeignKeyField(User, backref="claimed_character", null=True)
    created_by = ForeignKeyField(User, backref="created_characters")
    owned_by = ForeignKeyField(User, backref="owned_characters", null=True)
    created = DateTimeField(default=time_now)
    modified = DateTimeField(default=time_now)
    alive = BooleanField(default=True)
    age = IntegerField(null=True)
    archived = BooleanField(default=False)
    bio = TextField(null=True)
    concept = TextField(null=True)
    cool_points = IntegerField(default=0)
    cool_points_total = IntegerField(default=0)
    demeanor = TextField(null=True)
    experience = IntegerField(default=0)
    experience_total = IntegerField(default=0)
    gender = TextField(null=True)
    nature = TextField(null=True)
    ### Physical #############################
    strength = IntegerField(default=0)
    dexterity = IntegerField(default=0)
    stamina = IntegerField(default=0)
    ### Social #############################
    charisma = IntegerField(default=0)
    manipulation = IntegerField(default=0)
    appearance = IntegerField(default=0)
    ### Mental #############################
    perception = IntegerField(default=0)
    intelligence = IntegerField(default=0)
    wits = IntegerField(default=0)
    ### Talents #############################
    alertness = IntegerField(default=0)
    athletics = IntegerField(default=0)
    brawl = IntegerField(default=0)
    dodge = IntegerField(default=0)
    empathy = IntegerField(default=0)
    expression = IntegerField(default=0)
    intimidation = IntegerField(default=0)
    leadership = IntegerField(default=0)
    primal_urge = IntegerField(default=0)
    streetwise = IntegerField(default=0)
    subterfuge = IntegerField(default=0)
    ### Skills #############################
    animal_ken = IntegerField(default=0)
    crafts = IntegerField(default=0)
    drive = IntegerField(default=0)
    etiquette = IntegerField(default=0)
    firearms = IntegerField(default=0)
    insight = IntegerField(default=0)
    larceny = IntegerField(default=0)
    meditation = IntegerField(default=0)
    melee = IntegerField(default=0)
    performance = IntegerField(default=0)
    persuasion = IntegerField(default=0)
    repair = IntegerField(default=0)
    stealth = IntegerField(default=0)
    survival = IntegerField(default=0)
    technology = IntegerField(default=0)
    ### Knowledges #############################
    academics = IntegerField(default=0)
    bureaucracy = IntegerField(default=0)
    computer = IntegerField(default=0)
    enigmas = IntegerField(default=0)
    finance = IntegerField(default=0)
    investigation = IntegerField(default=0)
    law = IntegerField(default=0)
    linguistics = IntegerField(default=0)
    medicine = IntegerField(default=0)
    occult = IntegerField(default=0)
    politics = IntegerField(default=0)
    rituals = IntegerField(default=0)
    science = IntegerField(default=0)
    ### Virtues #############################
    conscience = IntegerField(default=0)
    self_control = IntegerField(default=0)
    courage = IntegerField(default=0)
    ### Universal #############################
    humanity = IntegerField(default=0)
    willpower = IntegerField(default=0)
    desperation = IntegerField(default=0)
    reputation = IntegerField(default=0)
    ### Mage  Universal ######################
    arete = IntegerField(default=0)
    quintessence = IntegerField(default=0)
    ### Vampire Universal #####################
    blood_pool = IntegerField(default=0)
    ### Hunter Universal ######################
    conviction = IntegerField(default=0)
    ### Werewolf Universal ####################
    gnosis = IntegerField(default=0)
    rage = IntegerField(default=0)
    ### Spheres #############################
    correspondence = IntegerField(default=0)
    entropy = IntegerField(default=0)
    forces = IntegerField(default=0)
    life = IntegerField(default=0)
    matter = IntegerField(default=0)
    mind = IntegerField(default=0)
    prime = IntegerField(default=0)
    spirit = IntegerField(default=0)
    time = IntegerField(default=0)
    ### Disciplines #############################
    animalism = IntegerField(default=0)
    auspex = IntegerField(default=0)
    blood_sorcery = IntegerField(default=0)
    celerity = IntegerField(default=0)
    dominate = IntegerField(default=0)
    fortitude = IntegerField(default=0)
    obeah = IntegerField(default=0)
    obfuscate = IntegerField(default=0)
    oblivion = IntegerField(default=0)
    potence = IntegerField(default=0)
    presence = IntegerField(default=0)
    protean = IntegerField(default=0)
    vicissitude = IntegerField(default=0)
    ### Renown - werewolf #########################
    glory = IntegerField(default=0)
    honor = IntegerField(default=0)
    wisdom = IntegerField(default=0)

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

    def __str__(self) -> str:
        """Return the string representation of the model."""
        return f"""Character({self.id} {self.name})"""


class CustomTrait(BaseModel):
    """Custom Trait model for the database."""

    character = ForeignKeyField(Character, backref="custom_traits")
    created = DateTimeField(default=time_now)
    description = TextField(null=True)
    guild = ForeignKeyField(Guild, backref="custom_traits")
    name = TextField()
    category = TextField(null=True)
    value = IntegerField(default=0)
    max_value = IntegerField(default=0)


class CustomCharSection(BaseModel):
    """Custom sections added to a character sheet."""

    character = ForeignKeyField(Character, backref="custom_traits")
    created = DateTimeField(default=time_now)
    description = TextField(null=True)
    guild = ForeignKeyField(Guild, backref="custom_traits")
    title = TextField()


class GuildUser(BaseModel):
    """Join table for Guild and User."""

    guild = ForeignKeyField(Guild, backref="users")
    user = ForeignKeyField(User, backref="guilds")


class Macro(BaseModel):
    """Macros for quick dice rolls."""

    name = TextField()
    abbreviation = TextField()
    description = TextField(null=True)
    created = DateTimeField(default=time_now)
    trait_one = TextField(null=True)
    trait_two = TextField(null=True)
    guild = ForeignKeyField(Guild, backref="macros")
    user = ForeignKeyField(User, backref="macros")
