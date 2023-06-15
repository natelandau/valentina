"""Constants for Valentina models."""
from enum import Enum

from flatdict import FlatDict


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
            "BloodSorcery",
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
