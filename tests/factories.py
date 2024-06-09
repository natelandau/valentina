# type: ignore
"""Factories for beanie models.

Import into tests which need the fixtures with `from tests.factories import *`.

Read more at https://polyfactory.litestar.dev/latest/index.html
"""

from faker import Faker
from polyfactory.factories.beanie_odm_factory import BeanieDocumentFactory
from polyfactory.pytest_plugin import register_fixture
from rich import print

from valentina.constants import CharacterConcept, CharClass, HunterCreed, TraitCategory, VampireClan
from valentina.models import (
    Campaign,
    CampaignChapter,
    CampaignExperience,
    CampaignNote,
    CampaignNPC,
    Character,
    CharacterTrait,
    Guild,
    GuildChannels,
    GuildPermissions,
    RollStatistic,
    User,
    UserMacro,
)


@register_fixture
class RollStatFactory(BeanieDocumentFactory[CharacterTrait]):
    """Factory to create a character trait object in the database."""

    __model__ = RollStatistic
    __set_as_default_factory_for_type__ = True
    __faker__ = Faker(locale="en_US")

    @classmethod
    def traits(cls) -> list[str]:
        return ["Strength", "Dexterity"]

    @classmethod
    def difficulty(cls) -> int:
        return cls.__random__.choice([4, 5, 6, 7, 8, 9, 10])

    @classmethod
    def pool(cls) -> int:
        return cls.__random__.choice([2, 3, 4, 5, 6, 7, 8])


@register_fixture
class CampaignFactory(BeanieDocumentFactory[Campaign]):
    """Factory to create a campaign object in the database."""

    __model__ = Campaign
    __set_as_default_factory_for_type__ = True
    __faker__ = Faker(locale="en_US")
    __min_collection_length__ = 1
    __max_collection_length__ = 3
    __randomize_collection_length__ = True

    @classmethod
    def name(cls) -> str:
        return cls.__faker__.sentence(nb_words=3).rstrip(".")

    @classmethod
    def description(cls) -> str:
        return cls.__faker__.paragraph(nb_sentences=3)


@register_fixture
class UserFactory(BeanieDocumentFactory[User]):
    """Factory to create a user object in the database."""

    __model__ = User
    __faker__ = Faker(locale="en_US")
    __set_as_default_factory_for_type__ = True
    __min_collection_length__ = 1
    __max_collection_length__ = 3
    __randomize_collection_length__ = True


@register_fixture
class GuildFactory(BeanieDocumentFactory[Guild]):
    """Factory to create a guild object in the database."""

    __model__ = Guild
    __faker__ = Faker(locale="en_US")
    __set_as_default_factory_for_type__ = True
    __min_collection_length__ = 1
    __max_collection_length__ = 3
    __randomize_collection_length__ = True


@register_fixture
class TraitFactory(BeanieDocumentFactory[CharacterTrait]):
    """Factory to create a character object in the database."""

    __model__ = CharacterTrait
    __faker__ = Faker(locale="en_US")
    __set_as_default_factory_for_type__ = True
    __min_collection_length__ = 1
    __max_collection_length__ = 3
    __randomize_collection_length__ = True

    @classmethod
    def name(cls) -> str:
        return cls.__random__.choice(["Strength", "Dexterity", "Stamina"])

    @classmethod
    def value(cls) -> int:
        return cls.__random__.choice([0, 1, 2, 3, 4, 5])

    @classmethod
    def max_value(cls) -> int:
        return 5

    @classmethod
    def category_name(cls) -> str:
        return cls.__random__.choice([x.name for x in TraitCategory])


@register_fixture
class CharacterFactory(BeanieDocumentFactory[Character]):
    """Factory to create a character object in the database."""

    __model__ = Character
    __faker__ = Faker(locale="en_US")
    __min_collection_length__ = 1
    __max_collection_length__ = 3
    __randomize_collection_length__ = True
    __set_as_default_factory_for_type__ = True

    @classmethod
    def char_class_name(cls) -> str:
        return cls.__random__.choice([x.name for x in CharClass.playable_classes()])

    @classmethod
    def concept_name(cls) -> str:
        return cls.__random__.choice([x.name for x in CharacterConcept])

    @classmethod
    def clan_name(cls) -> str:
        return cls.__random__.choice([x.name for x in VampireClan])

    @classmethod
    def creed_name(cls) -> str:
        return cls.__random__.choice([x.name for x in HunterCreed])

    @classmethod
    def name_first(cls) -> str:
        return cls.__faker__.last_name()

    @classmethod
    def name_last(cls) -> str:
        return cls.__faker__.last_name()

    @classmethod
    def inventory(cls) -> list:
        return []

    # async def insert(self) -> None:
    #     await self.insert(link_rule=WriteRules.WRITE)
