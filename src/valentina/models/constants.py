"""Constants for Valentina models."""
from enum import Enum

from flatdict import FlatDict


class MaxTraitValue(Enum):
    """Maximum value for a trait."""

    WILLPOWER = 10
    HUMANITY = 10
    RAGE = 10
    GNOSIS = 10
    ARETE = 10
    BLOOD_POOL = 20
    QUINTESSENCE = 20


class XPNew(Enum):
    """Experience cost for gaining a wholly new trait. Values are the cost."""

    ABILITIES = 3
    DISCIPLINES = 10
    SPHERES = 10
    BACKGROUNDS = 3


class XPRaise(Enum):
    """Experience costs for raising character traits. Values are the multiplier against current rating."""

    ATTRIBUTES = 4
    ABILITIES = 2
    VIRTUES = 2
    WILLPOWER = 1
    BACKGROUNDS = 2
    CLAN_DISCIPLINE = 5
    OTHER_DISCIPLINE = 7
    DISCIPLINES = 5  # TODO: Remove this and replace with clan/other
    SPHERES = 7
    ARETE = 10
    QUINTESSENCE = 1  # TODO: Get the actual number for this
    MERITS = 2
    FLAWS = 2
    RAGE = 1
    GNOSIS = 2
    GIFTS = 3
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


class CharClass(Enum):
    """Enum for types of characters."""

    MORTAL = "Mortal"
    VAMPIRE = "Vampire"
    WEREWOLF = "Werewolf"
    MAGE = "Mage"
    HUNTER = "Hunter"


GROUPED_TRAITS = {
    "ATTRIBUTES": {
        "Physical": ["Strength", "Dexterity", "Stamina"],
        "Social": ["Charisma", "Manipulation", "Appearance"],
        "Mental": ["Perception", "Intelligence", "Wits"],
    },
    "ABILITIES": {
        "Talents": [
            "Alertness",
            "Athletics",
            "Brawl",
            "Dodge",
            "Empathy",
            "Expression",
            "Intimidation",
            "Leadership",
            "Primal-Urge",
            "Streetwise",
            "Subterfuge",
        ],
        "Skills": [
            "Animal Ken",
            "Crafts",
            "Drive",
            "Etiquette",
            "Firearms",
            "Insight",
            "Larceny",
            "Meditation",
            "Melee",
            "Music",
            "Performance",
            "Persuasion",
            "Repair",
            "Stealth",
            "Survival",
            "Technology",
        ],
        "Knowledges": [
            "Academics",
            "Bureaucracy",
            "Computer",
            "Enigmas",
            "Finance",
            "Investigation",
            "Law",
            "Linguistics",
            "Medicine",
            "Occult",
            "Politics",
            "Rituals",
            "Science",
        ],
    },
    "COMMON": {
        "Virtues": ["Conscience", "Self-Control", "Courage"],
        "Universal": ["Willpower", "Humanity", "Desperation", "Reputation"],
    },
    "MAGE": {
        "Universal": ["Arete", "Quintessence"],
        "Spheres": [
            "Correspondence",
            "Entropy",
            "Forces",
            "Life",
            "Matter",
            "Mind",
            "Prime",
            "Spirit",
            "Time",
        ],
        "Resonance": ["Dynamic", "Entropic", "Static"],
    },
    "WEREWOLF": {
        "Universal": ["Gnosis", "Rage"],
        "Renown": ["Glory", "Honor", "Wisdom"],
    },
    "HUNTER": {
        "Universal": ["Conviction"],
    },
    "VAMPIRE": {
        "Universal": ["Blood Pool"],
        "Disciplines": [
            "Animalism",
            "Auspex",
            "Blood Sorcery",
            "Celerity",
            "Dominate",
            "Fortitude",
            "Obeah",
            "Obfuscate",
            "Oblivion",
            "Potence",
            "Presence",
            "Protean",
            "Vicissitude",
        ],
    },
}
ATTRIBUTES = set(sum(GROUPED_TRAITS["ATTRIBUTES"].values(), []))
ABILITIES = set(sum(GROUPED_TRAITS["ABILITIES"].values(), []))
COMMON = set(sum(GROUPED_TRAITS["COMMON"].values(), []))
MAGE = set(sum(GROUPED_TRAITS["MAGE"].values(), []))
WEREWOLF = set(sum(GROUPED_TRAITS["WEREWOLF"].values(), []))
HUNTER = set(sum(GROUPED_TRAITS["HUNTER"].values(), []))
VAMPIRE = set(sum(GROUPED_TRAITS["VAMPIRE"].values(), []))
FLAT_TRAITS: FlatDict = sum(FlatDict(GROUPED_TRAITS).values(), [])
