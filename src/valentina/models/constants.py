"""Constants for Valentina models."""
from enum import Enum
from functools import cache

from loguru import logger

from valentina.models.database import (
    CharacterClass,
    Trait,
    TraitCategory,
    TraitCategoryClass,
    VampireClan,
)

# maximum number of options in a discord select menu
MAX_OPTION_LIST_SIZE = 25
MAX_CHARACTER_COUNT = 1990
MAX_FIELD_COUNT = 1010
MAX_PAGE_CHARACTER_COUNT = 1950
MAX_BUTTONS_PER_ROW = 5


class DBConstants:
    """Constants from the database."""

    @staticmethod
    @cache
    def char_classes() -> list[CharacterClass]:
        """Fetch the character classes from the database."""
        logger.debug("DATABASE: Fetch character classes")
        return [x for x in CharacterClass.select().order_by(CharacterClass.name.asc())]

    @staticmethod
    @cache
    def vampire_clans() -> list[VampireClan]:
        """Fetch the vampire clans from the database."""
        logger.debug("DATABASE: Fetch vampire clans")
        return [x for x in VampireClan.select().order_by(VampireClan.name.asc())]

    @staticmethod
    @cache
    def trait_categories() -> list[TraitCategory]:
        """Fetch the trait categories from the database."""
        logger.debug("DATABASE: Fetch trait categories")
        return [x for x in TraitCategory.select().order_by(TraitCategory.name.asc())]

    @staticmethod
    @cache
    def trait_categories_by_class() -> dict[CharacterClass, list[TraitCategory]]:
        """Fetch the trait categories by class from the database."""
        logger.debug("DATABASE: Fetch trait categories by class")
        return {
            char_class: [
                x
                for x in TraitCategory.select()
                .join(TraitCategoryClass)
                .where(TraitCategoryClass.character_class == char_class)
            ]
            for char_class in DBConstants.char_classes()
        }

    @staticmethod
    @cache
    def traits_by_category() -> dict[str, list[str]]:
        """Fetch the traits by category from the database.

        Returns:
            dict[str, list[Trait]]: A dictionary of trait names by category name.
        """
        logger.debug("DATABASE: Fetch traits by category")
        return {
            category.name: [
                x.name
                for x in Trait.select().where(Trait.category == category).order_by(Trait.name.asc())
            ]
            for category in DBConstants.trait_categories()
        }

    @staticmethod
    @cache
    def all_traits() -> list[Trait]:
        """Fetch all traits from the database.

        Returns:
            list[Trait]: A list of all traits.
        """
        logger.debug("DATABASE: Fetch all traits")
        return [x for x in Trait.select().order_by(Trait.name.asc())]


### ENUMS ###
class MaxTraitValue(Enum):
    """Maximum value for a trait.

    Note: Maximum values for custom traits are managed in the database.
    """

    DEFAULT = 5
    # Specific values
    ARETE = 10
    BLOOD_POOL = 20
    GLORY = 10
    GNOSIS = 10
    HONOR = 10
    HUMANITY = 10
    QUINTESSENCE = 20
    RAGE = 10
    WILLPOWER = 10
    WISDOM = 10
    # Category values
    PHYSICAL = 5
    SOCIAL = 5
    MENTAL = 5
    TALENTS = 5
    SKILLS = 5
    KNOWLEDGES = 5
    DISCIPLINES = 5
    SPHERES = 5
    GIFTS = 5
    MERITS = 5
    FLAWS = 5
    BACKGROUNDS = 5
    VIRTUES = 5
    RENOWN = 5


class XPNew(Enum):
    """Experience cost for gaining a wholly new trait. Values are the cost in xp."""

    DEFAULT = 1
    # Category values
    DISCIPLINES = 10
    SPHERES = 10
    BACKGROUNDS = 3
    TALENTS = 3
    SKILLS = 3
    KNOWLEDGES = 3


class XPMultiplier(Enum):
    """Experience costs for raising character traits. Values are the multiplier against current rating."""

    DEFAULT = 2  # TODO: Is this the right value?
    # Attributes
    PHYSICAL = 4
    SOCIAL = 4
    MENTAL = 4
    # Abilities
    TALENTS = 2
    SKILLS = 2
    KNOWLEDGES = 2
    # Other
    VIRTUES = 2
    SPHERES = 7
    CLAN_DISCIPLINE = 5
    DISCIPLINES = 7
    MERITS = 2
    FLAWS = 2
    BACKGROUNDS = 2
    GIFTS = 3
    ## Specific Values #######################
    WILLPOWER = 1
    ARETE = 10
    QUINTESSENCE = 1  # TODO: Get the actual number for this
    RAGE = 1
    GNOSIS = 2
    HUMANITY = 2
    RESONANCE = 2  # TODO: Get the actual number for this
    CONVICTION = 2  # TODO: Get the actual number for this


class EmbedColor(Enum):
    """Enum for colors of embeds."""

    SUCCESS = 0x00FF00
    ERROR = 0xFF0000
    WARNING = 0xFFFF00
    INFO = 0x00FFFF
    DEBUG = 0x0000FF
    DEFAULT = 0x6082B6


class DiceType(Enum):
    """Enum for types of dice."""

    D4 = 4
    D6 = 6
    D8 = 8
    D10 = 10
    D100 = 100


class RollResultType(Enum):
    """Enum for results of a roll."""

    SUCCESS = "Success"
    FAILURE = "Failure"
    BOTCH = "Botch"
    CRITICAL = "Critical Success"
    OTHER = "Other"


CLAN_DISCIPLINES = {
    "Assamite": ["Celerity", "Obfuscate", "Quietus"],
    "Brujah": ["Celerity", "Potence", "Presence"],
    "Followers of Set": ["Obfuscate", "Presence", "Serpentis"],
    "Gangrel": ["Animalism", "Fortitude", "Protean"],
    "Giovanni": ["Dominate", "Necromancy", "Potence"],
    "Lasombra": ["Dominate", "Obfuscate", "Potence"],
    "Malkavian": ["Auspex", "Dominate", "Obfuscate"],
    "Nosferatu": ["Animalism", "Obfuscate", "Potence"],
    "Ravnos": ["Animalism", "Chimerstry", "Fortitude"],
    "Toreador": ["Auspex", "Celerity", "Presence"],
    "Tremere": ["Auspex", "Dominate", "Thaumaturgy"],
    "Tzimisce": ["Animalism", "Auspex", "Vicissitude"],
    "Ventrue": ["Dominate", "Fortitude", "Presence"],
}


DICEROLL_THUBMS = {
    "BOTCH": [
        "https://em-content.zobj.net/source/animated-noto-color-emoji/356/face-vomiting_1f92e.gif",
    ],
    "CRITICAL": [
        "https://em-content.zobj.net/source/animated-noto-color-emoji/356/rocket_1f680.gif",
    ],
    "OTHER": [
        "https://i.giphy.com/media/ygzkZPxmh6HgUzbYFz/giphy.gif",
        "https://em-content.zobj.net/thumbs/240/google/350/game-die_1f3b2.png",
        "https://i.giphy.com/media/ugNDcwUAydqjCPEMR1/giphy.gif",
    ],
    "FAILURE": [
        "https://i.giphy.com/media/aCwWc9CyTisF2/giphy.gif",
        "https://em-content.zobj.net/source/animated-noto-color-emoji/356/crying-face_1f622.gif",
        "https://i.giphy.com/media/xRyIsRCVTN70tBZPP1/giphy.gif",
    ],
    "SUCCESS": [
        "https://em-content.zobj.net/thumbs/240/apple/354/thumbs-up_1f44d.png",
    ],
}
