"""Models for the database."""

from loguru import logger
from peewee import DateTimeField, ForeignKeyField, IntegerField, Model, TextField

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
    courage = IntegerField(null=True)
    cool_points = IntegerField(null=True)
    cool_points_total = IntegerField(null=True)
    demeanor = TextField(null=True)
    desperation = IntegerField(null=True)
    experience = IntegerField(null=True)
    experience_total = IntegerField(null=True)
    gender = TextField(null=True)
    humanity = IntegerField(null=True)
    nature = TextField(null=True)
    player = IntegerField(null=True)
    self_control = IntegerField(null=True)
    willpower = IntegerField(null=True)

    def update_modified(self) -> None:
        """Update the modified field."""
        self.modified = time_now()
        self.save()
        logger.info(f"DATABASE: Character {self.first_name} modified_date updated.")

    def update_experience(self, experience: int) -> None:
        """Update the experience field."""
        self.experience += experience
        self.experience_total += experience
        self.save()
        logger.info(f"DATABASE: Character {self.first_name} experience updated.")

    def update_cool_points(self, cool_points: int) -> None:
        """Update the cool_points field."""
        self.cool_points += cool_points
        self.cool_points_total += cool_points
        self.save()
        logger.info(f"DATABASE: Character {self.first_name} cool_points updated.")
