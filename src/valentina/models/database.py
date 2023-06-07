"""Models for the database."""

from loguru import logger
from peewee import BooleanField, DateTimeField, ForeignKeyField, IntegerField, Model, TextField

from valentina import DATABASE
from valentina.utils.helpers import time_now


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

    guild_id = IntegerField(unique=True)
    name = TextField()
    first_seen = DateTimeField(default=time_now)
    last_connected = DateTimeField(default=time_now)


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
    bio = TextField(null=True)
    concept = TextField(null=True)
    cool_points = IntegerField(null=True)
    cool_points_total = IntegerField(null=True)
    experience = IntegerField(null=True)
    experience_total = IntegerField(null=True)
    gender = TextField(null=True)
    player_id = IntegerField(null=True)
    nature = TextField(null=True)
    demeanor = TextField(null=True)
    archived = BooleanField(default=False)
    notes = TextField(null=True)
    # ATTRIBUTES #################################
    strength = IntegerField(null=True)
    dexterity = IntegerField(null=True)
    stamina = IntegerField(null=True)
    charisma = IntegerField(null=True)
    manipulation = IntegerField(null=True)
    appearance = IntegerField(null=True)
    perception = IntegerField(null=True)
    intelligence = IntegerField(null=True)
    wits = IntegerField(null=True)
    # ABILITIES ##################################
    athletics = IntegerField(null=True)
    brawl = IntegerField(null=True)
    dodge = IntegerField(null=True)
    drive = IntegerField(null=True)
    empathy = IntegerField(null=True)
    expression = IntegerField(null=True)
    intimidation = IntegerField(null=True)
    leadership = IntegerField(null=True)
    streetwise = IntegerField(null=True)
    subterfuge = IntegerField(null=True)
    alertness = IntegerField(null=True)
    animal_ken = IntegerField(null=True)
    crafts = IntegerField(null=True)
    drive = IntegerField(null=True)
    etiquette = IntegerField(null=True)
    firearms = IntegerField(null=True)
    larceny = IntegerField(null=True)
    melee = IntegerField(null=True)
    performance = IntegerField(null=True)
    stealth = IntegerField(null=True)
    survival = IntegerField(null=True)
    technology = IntegerField(null=True)
    academics = IntegerField(null=True)
    computer = IntegerField(null=True)
    finance = IntegerField(null=True)
    investigation = IntegerField(null=True)
    law = IntegerField(null=True)
    linguistics = IntegerField(null=True)
    medicine = IntegerField(null=True)
    occult = IntegerField(null=True)
    politics = IntegerField(null=True)
    science = IntegerField(null=True)
    # VIRTUES #################################
    conscience = IntegerField(null=True)
    self_control = IntegerField(null=True)
    courage = IntegerField(null=True)
    # UNIVERSAL ################################
    humanity = IntegerField(null=True)
    willpower = IntegerField(null=True)
    desperation = IntegerField(null=True)
    reputation = IntegerField(null=True)
    # MAGE #####################################
    arete = IntegerField(null=True)
    quintessence = IntegerField(null=True)
    # WEREWOLF #################################
    rage = IntegerField(null=True)
    gnosis = IntegerField(null=True)
    # VAMPIRE ##################################
    blood_pool = IntegerField(null=True)
    # HUNTER ###################################
    conviction = IntegerField(null=True)
    # MAGE_SPHERES #############################
    correspondence = IntegerField(null=True)
    entropy = IntegerField(null=True)
    forces = IntegerField(null=True)
    life = IntegerField(null=True)
    matter = IntegerField(null=True)
    mind = IntegerField(null=True)
    prime = IntegerField(null=True)
    spirit = IntegerField(null=True)
    time = IntegerField(null=True)
    # MAGE_RESONANCE ##########################
    dynamic = IntegerField(null=True)
    static = IntegerField(null=True)
    entropic = IntegerField(null=True)
    # DISCIPLINES #############################
    animalism = IntegerField(null=True)
    auspex = IntegerField(null=True)
    blood_sorcery = IntegerField(null=True)
    celerity = IntegerField(null=True)
    dominate = IntegerField(null=True)
    fortitude = IntegerField(null=True)
    obeah = IntegerField(null=True)
    obfuscate = IntegerField(null=True)
    oblivion = IntegerField(null=True)
    potence = IntegerField(null=True)
    presence = IntegerField(null=True)
    protean = IntegerField(null=True)
    vicissitude = IntegerField(null=True)

    ################################################3

    def __str__(self) -> str:
        """Return the string representation of the model."""
        return f"""Character(
    first_name={self.first_name},
    last_name={self.last_name},
    nickname={self.nickname},
    char_class={self.char_class.name},
    guild={self.guild.name},
    created={self.created},
    modified={self.modified},
    age={self.age},
    bio={self.bio},
    concept={self.concept},
    cool_points={self.cool_points},
    cool_points_total={self.cool_points_total},
    experience={self.experience},
    experience_total={self.experience_total},
    player_id={self.player_id},
    strength={self.strength},
    dexterity={self.dexterity},
    stamina={self.stamina},
    charisma={self.charisma},
    manipulation={self.manipulation},
    appearance={self.appearance},
    perception={self.perception},
    intelligence={self.intelligence},
    wits={self.wits},
        )
        """

    def update_modified(self) -> None:
        """Update the modified field."""
        self.modified = time_now()
        self.save()
        logger.info(f"DATABASE: Character {self.first_name} modified_date updated.")

    def add_experience(self, experience: int) -> None:
        """Update the experience field."""
        self.experience += experience
        self.experience_total += experience
        self.save()
        logger.info(f"DATABASE: Character {self.first_name} experience updated.")

    def spend_experience(self, experience: int) -> None:
        """Update the experience field."""
        if experience > self.experience:
            raise ValueError("Not enough experience to use.")
        self.experience -= experience
        self.save()
        logger.info(f"DATABASE: Character {self.first_name} experience updated.")

    def add_cool_points(self, cool_points: int) -> None:
        """Update the cool_points field."""
        self.cool_points += cool_points
        self.cool_points_total += cool_points
        self.save()
        logger.info(f"DATABASE: Character {self.first_name} cool_points updated.")

    def spend_cool_points(self, cool_points: int) -> None:
        """Update the cool_points field."""
        if cool_points > self.cool_points:
            raise ValueError("Not enough cool_points to use.")
        self.cool_points -= cool_points
        self.save()
        logger.info(f"DATABASE: Character {self.first_name} cool_points updated.")


class CustomTrait(BaseModel):
    """Custom Trait model for the database."""

    name = TextField()
    description = TextField(null=True)
    trait_type = TextField(null=True)
    character = ForeignKeyField(Character, backref="custom_traits")
    value = IntegerField(null=True)
    created = DateTimeField(default=time_now)
