"""Constants for Valentina models."""
from enum import Enum

from flatdict import FlatDict


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
            "Streetwise",
            "Subterfuge",
        ],
        "Skills": [
            "Animal Ken",
            "Crafts",
            "Drive",
            "Etiquette",
            "Firearms",
            "Larceny",
            "Melee",
            "Performance",
            "Stealth",
            "Survival",
            "Technology",
        ],
        "Knowledges": [
            "Academics",
            "Computer",
            "Enigmas",
            "Finance",
            "Investigation",
            "Law",
            "Linguistics",
            "Medicine",
            "Occult",
            "Politics",
            "Science",
        ],
    },
}
ATTRIBUTES = set(sum(GROUPED_TRAITS["ATTRIBUTES"].values(), []))
ABILITIES = set(sum(GROUPED_TRAITS["ABILITIES"].values(), []))
ATTRIBUTES_AND_ABILITIES = ATTRIBUTES.union(ABILITIES)
FLAT_TRAITS: FlatDict = sum(FlatDict(GROUPED_TRAITS).values(), [])


VIRTUES = ["Conscience", "Self-Control", "Courage"]
UNIVERSAL_TRAITS = ["Willpower", "Humanity", "Desperation", "Reputation"]
MAGE_TRAITS = ["Arete", "Quintessence"]
WEREWOLF_TRAITS = ["Gnosis", "Rage"]
HUNTER_TRAITS = ["Conviction"]
VAMPIRE_TRAITS = ["Blood Pool"]

MAGE_SPHERES = [
    "Correspondence",
    "Entropy",
    "Forces",
    "Life",
    "Matter",
    "Mind",
    "Prime",
    "Spirit",
    "Time",
]
MAGE_RESONANCE = ["Dynamic", "Entropic", "Static"]


VAMPIRE_DISCIPLINES = [
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
]
