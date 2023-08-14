"""Constants for Valentina models."""
from enum import Enum, IntEnum

# maximum number of options in a discord select menu
MAX_OPTION_LIST_SIZE = 25
MAX_CHARACTER_COUNT = 1990
MAX_FIELD_COUNT = 1010
MAX_PAGE_CHARACTER_COUNT = 1950
MAX_BUTTONS_PER_ROW = 5


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

    # TODO: Need ability to charge 10points for 1st dot of a discipline

    DEFAULT = 2  # TODO: Is this the right value?
    # Attributes
    # TODO: Mage/Mortal attributes are 5 vampires are 4
    PHYSICAL = 5
    SOCIAL = 5
    MENTAL = 5
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

    SUCCESS = 0x00FF00  # GREEN
    ERROR = 0xFF0000  # RED
    WARNING = 0xFF5F00  # ORANGE
    INFO = 0x00FFFF  # CYAN
    DEBUG = 0x0000FF  # BLUE
    DEFAULT = 0x6082B6  # GRAY
    GRAY = 0x808080
    YELLOW = 0xFFFF00


class XPPermissions(Enum):
    """Permissions for adding xp to a character."""

    UNRESTRICTED = 0
    WITHIN_24_HOURS = 1  # Default
    CHARACTER_OWNER_ONLY = 2
    ADMIN_ONLY = 3


class TraitPermissions(Enum):
    """Permissions for updating character trait values."""

    UNRESTRICTED = 0
    WITHIN_24_HOURS = 1  # Default
    CHARACTER_OWNER_ONLY = 2
    ADMIN_ONLY = 3


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
    OTHER = "n/a"


class ChannelPermission(Enum):
    """Enum for permissions when creating a character. Default is UNRESTRICTED."""

    DEFAULT = 0  # Default
    HIDDEN = 1
    READ_ONLY = 2
    POST = 3
    MANAGE = 4


class TraitCategoryOrder(IntEnum):
    """The order of trait categories to mimic character sheets."""

    Physical = 1
    Social = 2
    Mental = 3
    Talents = 4
    Skills = 5
    Knowledges = 6
    Spheres = 7
    Disciplines = 8
    Numina = 9
    Backgrounds = 10
    Merits = 12
    Flaws = 13
    Virtues = 14
    Resonance = 16
    Gifts = 17
    Renown = 18
    Paths = 19
    Edges = 20
    Other = 21


COOL_POINT_VALUE = 10  # 1 cool point equals this many xp
DEFAULT_DIFFICULTY = 6  # Default difficulty for a roll

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
