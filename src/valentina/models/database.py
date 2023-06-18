"""Models for the database."""
from datetime import datetime, timezone

from loguru import logger
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


class Guild(BaseModel):
    """Guild model for the database."""

    id = IntegerField(primary_key=True)  # noqa: A003
    name = TextField()
    first_seen = DateTimeField(default=time_now)
    last_connected = DateTimeField(default=time_now)


class DatabaseVersion(BaseModel):
    """Database version model for the database."""

    version = TextField()


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
    created = DateTimeField(default=time_now)
    modified = DateTimeField(default=time_now)
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
    notes = TextField(null=True)
    player_id = IntegerField(null=True)
    # ATTRIBUTES #################################
    strength = IntegerField(default=0)
    dexterity = IntegerField(default=0)
    stamina = IntegerField(default=0)
    charisma = IntegerField(default=0)
    manipulation = IntegerField(default=0)
    appearance = IntegerField(default=0)
    perception = IntegerField(default=0)
    intelligence = IntegerField(default=0)
    wits = IntegerField(default=0)
    # ABILITIES ##################################
    academics = IntegerField(default=0)
    alertness = IntegerField(default=0)
    animal_ken = IntegerField(default=0)
    athletics = IntegerField(default=0)
    brawl = IntegerField(default=0)
    bureaucracy = IntegerField(default=0)
    computer = IntegerField(default=0)
    crafts = IntegerField(default=0)
    dodge = IntegerField(default=0)
    drive = IntegerField(default=0)
    empathy = IntegerField(default=0)
    enigmas = IntegerField(default=0)
    etiquette = IntegerField(default=0)
    expression = IntegerField(default=0)
    finance = IntegerField(default=0)
    firearms = IntegerField(default=0)
    insight = IntegerField(default=0)
    intimidation = IntegerField(default=0)
    investigation = IntegerField(default=0)
    larceny = IntegerField(default=0)
    law = IntegerField(default=0)
    leadership = IntegerField(default=0)
    linguistics = IntegerField(default=0)
    medicine = IntegerField(default=0)
    meditation = IntegerField(default=0)
    melee = IntegerField(default=0)
    occult = IntegerField(default=0)
    performance = IntegerField(default=0)
    persuasion = IntegerField(default=0)
    politics = IntegerField(default=0)
    primal_urge = IntegerField(default=0)
    repair = IntegerField(default=0)
    rituals = IntegerField(default=0)
    science = IntegerField(default=0)
    stealth = IntegerField(default=0)
    streetwise = IntegerField(default=0)
    subterfuge = IntegerField(default=0)
    survival = IntegerField(default=0)
    technology = IntegerField(default=0)
    # VIRTUES #################################
    conscience = IntegerField(default=0)
    self_control = IntegerField(default=0)
    courage = IntegerField(default=0)
    # UNIVERSAL ################################
    humanity = IntegerField(default=0)
    willpower = IntegerField(default=0)
    desperation = IntegerField(default=0)
    reputation = IntegerField(default=0)
    # MAGE #####################################
    arete = IntegerField(default=0)
    quintessence = IntegerField(default=0)
    # WEREWOLF #################################
    glory = IntegerField(default=0)
    gnosis = IntegerField(default=0)
    honor = IntegerField(default=0)
    rage = IntegerField(default=0)
    wisdom = IntegerField(default=0)
    # VAMPIRE ##################################
    blood_pool = IntegerField(default=0)
    # HUNTER ###################################
    conviction = IntegerField(default=0)
    # MAGE_SPHERES #############################
    correspondence = IntegerField(default=0)
    entropy = IntegerField(default=0)
    forces = IntegerField(default=0)
    life = IntegerField(default=0)
    matter = IntegerField(default=0)
    mind = IntegerField(default=0)
    prime = IntegerField(default=0)
    spirit = IntegerField(default=0)
    time = IntegerField(default=0)
    # MAGE_RESONANCE ##########################
    dynamic = IntegerField(default=0)
    entropic = IntegerField(default=0)
    static = IntegerField(default=0)
    # DISCIPLINES #############################
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

    ################################################3

    def __str__(self) -> str:
        """Return the string representation of the model."""
        return f"""Character({self.id} {self.name})"""

    def update_modified(self) -> None:
        """Update the modified field."""
        self.modified = time_now()
        self.save()
        logger.info(f"DATABASE: Character {self.name} modified_date updated.")

    def spend_experience(self, exp: int) -> None:
        """Update the experience field."""
        if exp > self.experience:
            raise ValueError("Not enough experience to use.")
        self.experience -= exp
        self.save()
        logger.info(f"DATABASE: Character {self.name} experience updated.")
        self.update_modified()

    def spend_cool_points(self, cps: int) -> None:
        """Update the cool_points field."""
        if cps > self.cool_points:
            raise ValueError("Not enough cool_points to use.")
        self.cool_points -= cps
        self.save()
        logger.info(f"DATABASE: Character {self.name} cool_points updated.")
        self.update_modified()


class DiceBinding(BaseModel):
    """Dice Binding model for the database."""

    name = TextField()
    description = TextField(null=True)
    character = ForeignKeyField(Character, backref="dice_bindings")
    created = DateTimeField(default=time_now)
    bind_one = TextField(null=True)
    bind_two = TextField(null=True)
    bind_three = TextField(null=True)


class CustomTrait(BaseModel):
    """Custom Trait model for the database."""

    name = TextField()
    description = TextField(null=True)
    trait_area = TextField(null=True)
    character = ForeignKeyField(Character, backref="custom_traits")
    value = IntegerField(default=0)
    created = DateTimeField(default=time_now)


class User(BaseModel):
    """User model for the database."""

    id = IntegerField(primary_key=True)  # noqa: A003
    avatar_url = TextField(null=True)
    first_seen = DateTimeField(default=time_now)
    is_admin = BooleanField(default=False)
    is_banned = BooleanField(default=False)
    last_connected = DateTimeField(default=time_now)
    username = TextField(null=True)


class GuildUser(BaseModel):
    """Join table for Guild and User."""

    guild = ForeignKeyField(Guild, backref="users")
    user = ForeignKeyField(User, backref="guilds")


class UserCharacter(BaseModel):
    """Join table for User and Character."""

    user = ForeignKeyField(User, backref="characters")
    character = ForeignKeyField(Character, backref="users")
