"""Constants for Valentina models."""

import re
from dataclasses import dataclass, field
from enum import Enum, StrEnum
from pathlib import Path
from random import choice
from typing import ClassVar

import inflect

from valentina import typed_dicts

# Create an inflect engine to pluralize words.
p = inflect.engine()


### Single constants ###
ABS_MAX_EMBED_CHARACTERS = 3900  # Absolute maximum number of characters in an embed -100 for safety
CHANGELOG_EXCLUDE_CATEGORIES = [
    "docs",
    "refactor",
    "style",
    "test",
    "chore",
    "perf",
    "ci",
    "build",
]

# Paths within the project
PROJECT_ROOT_PATH = Path(__file__).parents[2].absolute()
CHANGELOG_PATH = PROJECT_ROOT_PATH / "CHANGELOG.md"
USER_GUIDE_PATH = PROJECT_ROOT_PATH / "user_guide.md"
WEBUI_ROOT_PATH = PROJECT_ROOT_PATH / "src" / "valentina" / "webui"
WEBUI_STATIC_DIR_PATH = WEBUI_ROOT_PATH / "static"
BLUEPRINT_FOLDER_PATH = WEBUI_ROOT_PATH / "blueprints"
COGS_PATH = PROJECT_ROOT_PATH / "src" / "valentina" / "cogs"

COOL_POINT_VALUE = 10  # 1 cool point equals this many xp
DEFAULT_DIFFICULTY = 6  # Default difficulty for a roll
MAX_BUTTONS_PER_ROW = 5
MAX_DOT_DISPLAY = 5  # number of dots to display on a character sheet before converting to text
MAX_FIELD_COUNT = 1010
MAX_OPTION_LIST_SIZE = 25  # maximum number of options in a discord select menu
MAX_POOL_SIZE = 100  # maximum number of dice that can be rolled
PREF_MAX_EMBED_CHARACTERS = 1950  # Preferred maximum number of characters in an embed
SPACER = "\u200b"  # Zero-width space
VALID_IMAGE_EXTENSIONS = frozenset(["png", "jpg", "jpeg", "gif", "webp"])


### ENUMS ###


class Emoji(Enum):
    """Enum for emojis."""

    ALIVE = "🙂"
    BOOK = "📖"
    BOOKS = "📚"
    BOT = "🤖"
    CANCEL = "🚫"
    CHANGELING = "🧑👿"
    COOL_POINT = "🆒"
    DANGER = "👮‍♂️"
    DEAD = "💀"
    DESPAIR = "😰"
    DESPERATION = "🤞"
    DICE = "🎲"
    ERROR = "❌"
    FACEPALM = "🤦"
    GHOST = "👻"
    GHOUL = "🧟"
    HUNTER = "🧑🏹"
    LOCK = "🔒"
    MAGE = "🧙🪄"
    MONSTER = "👹"
    MORTAL = "🧑"
    NO = "❌"
    NOTE = "📝"
    OTHER = "🤷"
    OVERREACH = "😱"
    PENCIL = "✏️"
    QUESTION = "❓"
    RECYCLE = "♻️"
    RELOAD = "🔄"
    SETTING = "⚙️"
    SILHOUETTE = "👤"
    SPARKLES = "✨"
    SUCCESS = "👍"
    VAMPIRE = "🧛"
    WARNING = "⚠️"
    WEREWOLF = "🐺"
    YES = "✅"


class LogLevel(StrEnum):
    """Enum for logging levels."""

    TRACE = "TRACE"
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    SUCCESS = "SUCCESS"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class ChannelPermission(Enum):
    """Enum for permissions when creating a character. Default is UNRESTRICTED."""

    DEFAULT = 0  # Default
    HIDDEN = 1
    READ_ONLY = 2
    POST = 3
    MANAGE = 4


class CampaignChannelName(Enum):
    """Enum for common campaign channel names."""

    GENERAL = f"{Emoji.SPARKLES.value}-general"
    STORYTELLER = f"{Emoji.LOCK.value}-storyteller"


class DiceType(Enum):
    """Enum for types of dice."""

    D4 = 4
    D6 = 6
    D8 = 8
    D10 = 10
    D100 = 100


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


class GithubIssueLabels(Enum):
    """Enum for Github issue labels."""

    BUG = "bug"
    ENHANCEMENT = "enhancement"
    QUESTION = "question"


class MaxTraitValue(Enum):
    """Maximum value for a trait.

    Note: Maximum values for custom traits are managed in the database.
    """

    DEFAULT = 5
    # Specific traits
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
    CONVICTION = 10
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


class PermissionsManageTraits(Enum):
    """Permissions for updating character trait values."""

    UNRESTRICTED = 0
    WITHIN_24_HOURS = 1  # Default
    CHARACTER_OWNER_ONLY = 2
    STORYTELLER_ONLY = 3


class PermissionsKillCharacter(Enum):
    """Permissions for killing characters."""

    UNRESTRICTED = 0
    CHARACTER_OWNER_ONLY = 1  # Default
    STORYTELLER_ONLY = 2


class PermissionsGrantXP(Enum):
    """Permissions for adding xp to a character."""

    UNRESTRICTED = 0
    PLAYER_ONLY = 1  # Default
    STORYTELLER_ONLY = 2


class PermissionManageCampaign(Enum):
    """Permissions for managing a campaign."""

    UNRESTRICTED = 0
    STORYTELLER_ONLY = 1  # Default


class RollResultType(Enum):
    """Enum for results of a roll."""

    SUCCESS = 0
    FAILURE = 1
    BOTCH = 2
    CRITICAL = 3
    OTHER = 4


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

    ### DISCORD SETTINGS ###


class CharSheetSection(Enum):
    """Enum for character sheet sections. Rollups of TraitCategory."""

    ATTRIBUTES: ClassVar[typed_dicts.CharSheetSectionDict] = {"name": "Attributes", "order": 1}
    ABILITIES: ClassVar[typed_dicts.CharSheetSectionDict] = {"name": "Abilities", "order": 2}
    ADVANTAGES: ClassVar[typed_dicts.CharSheetSectionDict] = {"name": "Advantages", "order": 3}
    NONE: ClassVar[typed_dicts.CharSheetSectionDict] = {"name": "None", "order": 4}


# Enums linked to the Database
# Updates may require a database migration


@dataclass(frozen=True, eq=True)
class CharClassValue:
    """A value object for the CharClass enum."""

    name: str
    percentile_range: tuple[int, int]
    description: str
    playable: bool
    chargen_background_dots: int
    emoji: str


class CharClass(Enum):
    """Character classes for character generation."""

    MORTAL = CharClassValue(
        name="Mortal",
        percentile_range=(0, 60),
        description="Receive special abilities based on their concept",
        playable=True,
        chargen_background_dots=1,
        emoji=Emoji.MORTAL.value,
    )
    VAMPIRE = CharClassValue(
        name="Vampire",
        percentile_range=(61, 66),
        description="Receive a clan and disciplines",
        playable=True,
        chargen_background_dots=5,
        emoji=Emoji.VAMPIRE.value,
    )
    WEREWOLF = CharClassValue(
        name="Werewolf",
        percentile_range=(67, 72),
        description="Receive a tribe and gifts",
        playable=True,
        chargen_background_dots=1,
        emoji=Emoji.WEREWOLF.value,
    )
    MAGE = CharClassValue(
        name="Mage",
        percentile_range=(73, 78),
        description="Receive a tradition and spheres",
        playable=True,
        chargen_background_dots=1,
        emoji=Emoji.MAGE.value,
    )
    GHOUL = CharClassValue(
        name="Ghoul",
        percentile_range=(79, 84),
        description="Receive disciplines and a master",
        playable=True,
        chargen_background_dots=1,
        emoji=Emoji.GHOUL.value,
    )
    CHANGELING = CharClassValue(
        name="Changeling",
        percentile_range=(85, 90),
        description="",
        playable=True,
        chargen_background_dots=1,
        emoji=Emoji.CHANGELING.value,
    )
    HUNTER = CharClassValue(
        name="Hunter",
        percentile_range=(91, 96),
        description="Receive a creed and edges",
        playable=True,
        chargen_background_dots=1,
        emoji=Emoji.HUNTER.value,
    )
    SPECIAL = CharClassValue(
        name="Special",
        percentile_range=(97, 100),
        description="Examples: Demon, Angel, Exalted, Titan, Mummy, etc. You choose.",
        playable=True,
        chargen_background_dots=3,
        emoji=Emoji.MONSTER.value,
    )
    OTHER = CharClassValue(
        name="Other",
        percentile_range=None,
        description=None,
        playable=False,
        chargen_background_dots=0,
        emoji=Emoji.OTHER.value,
    )
    NONE = CharClassValue(
        name="None",
        percentile_range=None,
        description=None,
        playable=False,
        chargen_background_dots=0,
        emoji=Emoji.SILHOUETTE.value,
    )
    COMMON = CharClassValue(
        name="Common",
        percentile_range=None,
        description=None,
        playable=False,
        chargen_background_dots=0,
        emoji=Emoji.SILHOUETTE.value,
    )

    @classmethod
    def get_member_by_value(cls, number: int) -> "CharClass":
        """Find the corresponding enum member's name based on an integer value found in the range value.

        Args:
            number (int): The integer value to look up.

        Returns:
            Optional[str]: The name of the enum member if found, otherwise None.
        """
        for member in cls:
            if not member.value.percentile_range:
                continue
            min_val, max_val = member.value.percentile_range
            if min_val <= number <= max_val:
                return member

        msg = f"Value {number} not found in any CharClass range"
        raise ValueError(msg)

    @classmethod
    def random_member(cls) -> "CharClass":
        """Select a random member from the enum.

        Returns:
            CharClass: A random enum member.
        """
        return choice([x for x in cls if x.value.playable])

    @classmethod
    def playable_classes(cls) -> list["CharClass"]:
        """Return a list of playable classes.

        Returns:
            list[CharClass]: A list of playable classes.
        """
        return [x for x in cls if x.value.playable]


@dataclass(frozen=True, eq=True)
class TraitCategoryValue:
    """A value object for a trait category."""

    classes: list[CharClass]
    name: str
    order: int
    section: CharSheetSection
    show_zero: bool
    COMMON: list[str] = field(default_factory=list, hash=True)
    MORTAL: list[str] = field(default_factory=list, hash=True)
    VAMPIRE: list[str] = field(default_factory=list, hash=True)
    WEREWOLF: list[str] = field(default_factory=list, hash=True)
    MAGE: list[str] = field(default_factory=list, hash=True)
    GHOUL: list[str] = field(default_factory=list, hash=True)
    CHANGELING: list[str] = field(default_factory=list, hash=True)
    HUNTER: list[str] = field(default_factory=list, hash=True)
    SPECIAL: list[str] = field(default_factory=list, hash=True)


class TraitCategory(Enum):
    """Enum for categories of traits."""

    PHYSICAL = TraitCategoryValue(
        classes=[CharClass.COMMON],
        name="Physical",
        section=CharSheetSection.ATTRIBUTES,
        order=1,
        show_zero=True,
        COMMON=["Strength", "Dexterity", "Stamina"],
    )
    SOCIAL = TraitCategoryValue(
        classes=[CharClass.COMMON],
        name="Social",
        section=CharSheetSection.ATTRIBUTES,
        order=2,
        show_zero=True,
        COMMON=["Charisma", "Manipulation", "Appearance"],
    )
    MENTAL = TraitCategoryValue(
        classes=[CharClass.COMMON],
        name="Mental",
        section=CharSheetSection.ATTRIBUTES,
        order=3,
        show_zero=True,
        COMMON=["Perception", "Intelligence", "Wits"],
    )
    TALENTS = TraitCategoryValue(
        classes=[CharClass.COMMON],
        name="Talents",
        section=CharSheetSection.ABILITIES,
        order=4,
        show_zero=True,
        COMMON=[
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
        WEREWOLF=["Primal-Urge"],
        MAGE=["Awareness"],
        HUNTER=["Awareness", "Insight", "Persuasion"],
    )
    SKILLS = TraitCategoryValue(
        classes=[CharClass.COMMON],
        name="Skills",
        section=CharSheetSection.ABILITIES,
        order=5,
        show_zero=True,
        COMMON=[
            "Animal Ken",
            "Drive",
            "Etiquette",
            "Firearms",
            "Melee",
            "Performance",
            "Security",
            "Stealth",
            "Survival",
        ],
        MORTAL=["Crafts", "Larceny", "Repair"],
        MAGE=["Crafts", "Technology"],
        HUNTER=["Crafts", "Demolitions", "Larceny", "Technology", "Repair"],
    )
    KNOWLEDGES = TraitCategoryValue(
        classes=[CharClass.COMMON],
        name="Knowledges",
        section=CharSheetSection.ABILITIES,
        order=6,
        show_zero=True,
        COMMON=[
            "Academics",
            "Computer",
            "Finance",
            "Investigation",
            "Law",
            "Linguistics",
            "Medicine",
            "Occult",
            "Politics",
            "Science",
        ],
        WEREWOLF=["Rituals", "Enigmas"],
        MAGE=["Cosmology", "Enigmas"],
    )
    SPHERES = TraitCategoryValue(
        classes=[CharClass.MAGE],
        name="Spheres",
        section=CharSheetSection.ADVANTAGES,
        order=7,
        show_zero=False,
        COMMON=[],
        MAGE=[
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
    )
    DISCIPLINES = TraitCategoryValue(
        classes=[CharClass.VAMPIRE, CharClass.GHOUL],
        name="Disciplines",
        order=8,
        show_zero=False,
        section=CharSheetSection.ADVANTAGES,
        COMMON=[],
        VAMPIRE=[
            "Animalism",
            "Auspex",
            "Blood Sorcery",
            "Celerity",
            "Chimerstry",
            "Dominate",
            "Fortitude",
            "Necromancy",
            "Obeah",
            "Obfuscate",
            "Oblivion",
            "Potence",
            "Presence",
            "Protean",
            "Serpentis",
            "Thaumaturgy",
            "Vicissitude",
        ],
        GHOUL=[
            "Animalism",
            "Auspex",
            "Blood Sorcery",
            "Celerity",
            "Chimerstry",
            "Dominate",
            "Fortitude",
            "Necromancy",
            "Obeah",
            "Obfuscate",
            "Oblivion",
            "Potence",
            "Presence",
            "Protean",
            "Serpentis",
            "Thaumaturgy",
            "Vicissitude",
        ],
    )
    NUMINA = TraitCategoryValue(
        classes=[CharClass.MORTAL, CharClass.MAGE, CharClass.HUNTER],
        name="Numina",
        section=CharSheetSection.ADVANTAGES,
        order=9,
        show_zero=False,
        COMMON=[],
    )
    BACKGROUNDS = TraitCategoryValue(
        classes=[CharClass.COMMON],
        name="Backgrounds",
        section=CharSheetSection.ADVANTAGES,
        order=10,
        show_zero=False,
        COMMON=[
            "Allies",
            "Arcane",
            "Arsenal",
            "Contacts",
            "Fame",
            "Influence",
            "Mentor",
            "Resources",
            "Retainers",
            "Status",
            "Reputation",
        ],
        VAMPIRE=["Generation", "Herd"],
        HUNTER=["Bystanders", "Destiny", "Exposure", "Patron"],
    )
    MERITS = TraitCategoryValue(
        classes=[CharClass.COMMON],
        name="Merits",
        section=CharSheetSection.ADVANTAGES,
        order=11,
        show_zero=False,
        COMMON=[],
    )
    FLAWS = TraitCategoryValue(
        classes=[CharClass.COMMON],
        name="Flaws",
        section=CharSheetSection.ADVANTAGES,
        order=12,
        show_zero=False,
        COMMON=[],
    )
    VIRTUES = TraitCategoryValue(
        classes=[CharClass.COMMON],
        name="Virtues",
        section=CharSheetSection.ADVANTAGES,
        order=13,
        show_zero=True,
        COMMON=[],
        MORTAL=["Conscience", "Self-Control", "Courage"],
        VAMPIRE=["Conscience", "Self-Control", "Courage"],
        MAGE=["Conscience", "Self-Control", "Courage"],
        GHOUL=["Conscience", "Self-Control", "Courage"],
        CHANGELING=["Conscience", "Self-Control", "Courage"],
        HUNTER=["Mercy", "Vision", "Zeal"],
        SPECIAL=["Conscience", "Self-Control", "Courage"],
    )
    RESONANCE = TraitCategoryValue(
        classes=[CharClass.MAGE],
        name="Resonance",
        section=CharSheetSection.ADVANTAGES,
        order=14,
        show_zero=False,
        COMMON=[],
        MAGE=["Dynamic", "Entropic", "Static"],
    )
    GIFTS = TraitCategoryValue(
        classes=[CharClass.WEREWOLF, CharClass.CHANGELING],
        name="Gifts",
        section=CharSheetSection.ADVANTAGES,
        order=15,
        show_zero=False,
        COMMON=[],
    )
    RENOWN = TraitCategoryValue(
        classes=[CharClass.WEREWOLF],
        name="Renown",
        section=CharSheetSection.ADVANTAGES,
        order=16,
        show_zero=False,
        COMMON=[],
        WEREWOLF=["Glory", "Honor", "Wisdom"],
        CHANGELING=["Glory", "Honor", "Wisdom"],
    )
    EDGES = TraitCategoryValue(
        classes=[CharClass.HUNTER],
        name="Edges",
        section=CharSheetSection.ADVANTAGES,
        order=17,
        show_zero=False,
        COMMON=[],
        HUNTER=[
            "Hide",  # Innocence
            "Illuminate",
            "Radiate",
            "Confront",
            "Blaze",
            "Demand",  # Martyrdom
            "Witness",
            "Ravage",
            "Donate",
            "Payback",
            "Bluster",  # Redemption
            "Insinuate",
            "Respire",
            "Becalm",
            "Suspend",
            "Foresee",  # Visionary
            "Pinpoint",
            "Delve",
            "Restore",
            "Augur",
            "Ward",  # Defense
            "Rejuvenate",
            "Brand",
            "Champion",
            "Burn",
            "Discern",  # Judgment
            "Burden",
            "Balance",
            "Pierce",
            "Expose",
            "Cleave",  # Vengeance
            "Trail",
            "Smolder",
            "Surge",
            "Smite",
        ],
    )
    PATHS = TraitCategoryValue(
        classes=[CharClass.COMMON],
        name="Paths",
        section=CharSheetSection.ADVANTAGES,
        order=18,
        show_zero=False,
    )
    OTHER = TraitCategoryValue(
        classes=[CharClass.COMMON],
        name="Other",
        section=CharSheetSection.ADVANTAGES,
        order=19,
        show_zero=True,
        COMMON=["Willpower"],
        MORTAL=["Humanity"],
        VAMPIRE=["Blood Pool", "Humanity"],
        WEREWOLF=["Gnosis", "Rage"],
        MAGE=["Humanity", "Arete", "Quintessence"],
        GHOUL=["Humanity"],
        HUNTER=["Conviction"],
    )

    def get_trait_list(self, char_class: CharClass) -> list[str]:
        """Return a list of traits for the given character class.

        Args:
            char_class (CharClass): The character class.

        Returns:
            list[str]: A list of traits.
        """
        return self.value.COMMON + getattr(self.value, char_class.name)


class InventoryItemType(Enum):
    """Enum for types of inventory items."""

    CONSUMABLE = "Consumable"
    ENCHANTED = "Enchanted"
    EQUIPMENT = "Equipment"
    OTHER = "Other"
    WEAPON = "Weapon"


@dataclass(frozen=True, eq=True)
class VampireClanValue:
    """A value object for the VampireClan enum."""

    name: str
    disciplines: list[str]


class VampireClan(Enum):
    """Vampire clans for character generation."""

    ASSAMITE = VampireClanValue(
        name="Assamite",
        disciplines=["Celerity", "Obfuscate", "Quietus"],
    )
    BRUJAH = VampireClanValue(
        name="Brujah",
        disciplines=["Celerity", "Potence", "Presence"],
    )
    FOLLOWERS_OF_SET = VampireClanValue(
        name="Followers of Set",
        disciplines=["Obfuscate", "Presence", "Serpentis"],
    )
    GANGREL = VampireClanValue(
        name="Gangrel",
        disciplines=["Animalism", "Fortitude", "Protean"],
    )
    GIOVANNI = VampireClanValue(
        name="Giovanni",
        disciplines=["Dominate", "Necromancy", "Potence"],
    )
    LASOMBRA = VampireClanValue(
        name="Lasombra",
        disciplines=["Dominate", "Obfuscate", "Potence"],
    )
    MALKAVIAN = VampireClanValue(
        name="Malkavian",
        disciplines=["Auspex", "Dominate", "Obfuscate"],
    )
    NOSFERATU = VampireClanValue(
        name="Nosferatu",
        disciplines=["Animalism", "Obfuscate", "Potence"],
    )
    RAVNOS = VampireClanValue(
        name="Ravnos",
        disciplines=["Animalism", "Chimerstry", "Fortitude"],
    )
    TOREADOR = VampireClanValue(
        name="Toreador",
        disciplines=["Auspex", "Celerity", "Presence"],
    )
    TREMERE = VampireClanValue(
        name="Tremere",
        disciplines=["Auspex", "Dominate", "Thaumaturgy"],
    )
    TZIMISCE = VampireClanValue(
        name="Tzimisce",
        disciplines=["Animalism", "Auspex", "Vicissitude"],
    )
    VENTRUE = VampireClanValue(
        name="Ventrue",
        disciplines=["Dominate", "Fortitude", "Presence"],
    )

    @classmethod
    def random_member(cls) -> "VampireClan":
        """Select a random member from the enum.

        Returns:
            VampireClan: A random enum member.
        """
        return choice(list(cls))


class CharGenHumans(Enum):
    """Enum for RNG character generation of humans."""

    CIVILIAN = (0, 60)
    HUNTER = (61, 70)
    WATCHER = (70, 79)
    NUMINOUS = (90, 100)

    @classmethod
    def get_member_by_value(cls, value: int) -> "CharGenHumans":
        """Find the corresponding enum member's name based on an integer value.

        Args:
            value (int): The integer value to look up.

        Returns:
            Optional[str]: The name of the enum member if found, otherwise None.
        """
        for member in cls:
            min_val, max_val = member.value
            if min_val <= value <= max_val:
                return member

        return None


class RNGCharLevel(Enum):
    """Enum to specify character levels for RNG-based trait generation.

    This enum is used by the RNG engine to determine the mean and standard deviation
    values for generating character traits using numpy's random.normal distribution.

    The tuple values represent (mean, standard deviation). Higher numerical values
    indicate a higher likelihood of the character having superior traits.
    """

    NEW = (1.0, 2.0)
    INTERMEDIATE = (1.5, 2.0)
    ADVANCED = (2.5, 2.0)
    ELITE = (3.0, 2.0)

    @classmethod
    def random_member(cls) -> "RNGCharLevel":
        """Select a random member from the enum.

        Returns:
            CharClass: A random enum member.
        """
        return choice(list(cls))


@dataclass(frozen=True, eq=True)
class CharacterConceptValue:
    """Class for the values of the CharacterConcept enum."""

    name: str
    description: str
    examples: str
    percentile_range: tuple[int, int]
    num_abilities: int
    ability_specialty: TraitCategory
    attribute_specialty: TraitCategory
    abilities: list[typed_dicts.ConceptAbilityDict] = field(default_factory=list)
    specific_abilities: list[str] = field(default_factory=list)


class CharacterConcept(Enum):
    """Enum for RNG character generation of concepts."""

    BERSERKER = CharacterConceptValue(
        name="Berserker",
        description="Fierce warriors who tap into their primal rage to gain incredible strength and combat prowess.",
        examples="Gang member, Hooligan, Anarchist, Rebel, Terrorist, Underground Fight League Member, Flame Jumper, Mole people, Goon",
        percentile_range=(1, 9),
        num_abilities=1,
        abilities=[
            {
                "name": "Frenzy",
                "description": "Ignore the first inflicted health levels of damage with no penalty up until `Mauled`, and cannot be stunned.  Barbarians also gain an automatic success on any strength roll once per turn, equal to a permanent dot in Potence.",
                "traits": [("Potence", 1, "DISCIPLINES")],
                "custom_sections": [
                    (
                        "Frenzy",
                        "Ignore the first inflicted health levels of damage with no penalty up until `Mauled`, and cannot be stunned",
                    )
                ],
            }
        ],
        ability_specialty=TraitCategory.TALENTS,
        attribute_specialty=TraitCategory.PHYSICAL,
        specific_abilities=[
            "Melee",
            "Firearms",
            "Alertness",
            "Athletics",
            "Brawl",
            "Dodge",
            "Stealth",
        ],
    )
    PERFORMER = CharacterConceptValue(
        name="Performer",
        description="Charismatic performers and spellcasters who use their artistry and magic to inspire and manipulate. ",
        examples="Musician, Online Influencer, Street Poet, Stand-up Comic, Performance Artist, Visual Artist, Fine Artist",
        num_abilities=1,
        percentile_range=(10, 18),
        abilities=[
            {
                "name": "Fast Talk",
                "description": "Performers have an automatic success on any `charisma`, `expression` or `performance` roll, and can immediately command attention. This works even in combat, functionally freezing enemies, including groups, for the first turn. Note that the bard needs to keep doing their act for this to work, they can't drop their guitar and pick up a gun without ruining the effect.",
                "traits": [],
                "custom_sections": [
                    (
                        "Fast Talk",
                        "Performers have an automatic success on any `Charisma`, `Expression` or `Performance` roll, and can immediately command attention. This works even in combat.",
                    )
                ],
            }
        ],
        ability_specialty=TraitCategory.SKILLS,
        attribute_specialty=TraitCategory.SOCIAL,
        specific_abilities=[
            "Expression",
            "Empathy",
            "Subterfuge",
            "Leadership",
            "Alertness",
            "Performance",
            "Intimidation",
        ],
    )
    HEALER = CharacterConceptValue(
        name="Healer",
        description="Devout servants of gods or higher powers, with the ability to heal and protect.",
        examples="Doctor, Veterinarian, Mortician, Priest, Rabbi, Medicine Man, EMT, Lifeguard, RN, Dentist, Clinician, Masseuse, Chemical Hacker, New-Ager",
        num_abilities=1,
        percentile_range=(19, 27),
        abilities=[
            {
                "name": "Heal",
                "description": "Heal 3 health levels to a target once per turn.  Any First Aid/medicine roles are also automatically granted one success.",
                "traits": [],
                "custom_sections": [
                    (
                        "Heal",
                        "Heal 3 health levels to a target once per turn.  Any First Aid or Medicine roles are also automatically granted one success.",
                    ),
                ],
            },
            {
                "name": "True Faith",
                "description": "Starts with a Faith of `3`, equivalent to a Discipline.  Clerics can repel supernatural beings for every success on a Faith role.",
                "traits": [],
                "custom_sections": [
                    (
                        "True Faith",
                        "Starts with a Faith of `3`, equivalent to a Discipline.  Clerics can repel supernatural beings for every success on a Faith role.",
                    ),
                ],
            },
        ],
        ability_specialty=TraitCategory.KNOWLEDGES,
        attribute_specialty=TraitCategory.MENTAL,
        specific_abilities=[
            "Academics",
            "Empathy",
            "Investigation",
            "Medicine",
            "Occult",
            "Science",
            "Survival",
        ],
    )
    SHAMAN = CharacterConceptValue(
        name="Shaman",
        description="Nature-focused spiritualists who wield the power of the natural world.",
        examples="Environmentalist, Tribal, New Age, Artist, Riverkeeper, Green Warden, Nature Guide, Photographer, Self-Documentarian",
        num_abilities=2,
        percentile_range=(28, 36),
        abilities=[
            {
                "name": "Familiar",
                "description": "A trained animal that can carry out simple commands",
                "traits": [],
                "custom_sections": [
                    ("Familiar", "A trained animal that can carry out simple commands")
                ],
            },
            {
                "name": "Friend of Animals",
                "description": "Per `Animalism` level `1`.",
                "traits": [("Animalism", 1, "DISCIPLINES")],
                "custom_sections": [],
            },
            {
                "name": "Spirit Sight",
                "description": "Sees the dead, naturalistic spirits, places of power. Can detect supernatural beings, and penetrate spells, illusions and glamour on a `perception` + `occult` roll with a difficulty of `4`.",
                "traits": [],
                "custom_sections": [
                    (
                        "Spirit Sight",
                        "Can detect supernatural beings, and penetrate spells, illusions and glamour on a `perception` + `occult` roll with a difficulty of `4`",
                    )
                ],
            },
            {
                "name": "Read Auras",
                "description": "Learn various qualities of a person from their aura",
                "traits": [],
                "custom_sections": [
                    ("Read Auras", "Learn various qualities of a person from their aura")
                ],
            },
            {
                "name": "Astral Projection",
                "description": "Free your mind to travel the world in astral form",
                "traits": [],
                "custom_sections": [
                    ("Astral Projection", "Free your mind to travel the world in astral form")
                ],
            },
            {
                "name": "Remove Frenzy",
                "description": "Can cool vampires frenzy, werewolves' rage, etc. They become passive for two turns.",
                "traits": [],
                "custom_sections": [
                    (
                        "Remove Frenzy",
                        "Can cool vampires frenzy, werewolves' rage, etc. They become passive for two turns.",
                    )
                ],
            },
        ],
        ability_specialty=TraitCategory.KNOWLEDGES,
        attribute_specialty=TraitCategory.MENTAL,
        specific_abilities=[
            "Alertness",
            "Animal Ken",
            "Empathy",
            "Expression",
            "Linguistics",
            "Medicine",
            "Occult",
            "Survival",
        ],
    )
    SOLDIER = CharacterConceptValue(
        name="Soldier",
        description="Skilled warriors with a wide range of combat abilities and weapon expertise.",
        examples="Marine, Veteran, Mercenary, Hired Muscle, Hitman, Amateur/Pro Fighter, Martial Artist, Police, Security",
        num_abilities=1,
        percentile_range=(37, 44),
        abilities=[
            {
                "name": "Firearms",
                "description": "Can re-roll any single Firearms roll once per turn. Can also specialize in new firearms at `3`, `4` and `5` dots, granting an additional dice whenever a specialized weapon is used.",
                "traits": [],
                "custom_sections": [
                    (
                        "Firearms Specialist",
                        "Can re-roll any single Firearms roll once per turn. Can also specialize in new firearms at `3`, `4` and `5`, granting an additional dice whenever a specialized weapon is used.",
                    )
                ],
            },
            {
                "name": "Hand-to-hand Specialist",
                "description": "Can re-roll any single `Brawl` roll once per turn. Can also gain a new specialization at `3`, `4` and `5` dots, granting an additional die whenever a specialized martial arts style is used. ",
                "traits": [],
                "custom_sections": [
                    (
                        "Hand to hand",
                        "Can re-roll any single `Brawl` roll once per turn. Can also gain a new specialization at `3`, `4` and `5`, granting an additional die whenever a specialized martial arts style is used.",
                    )
                ],
            },
            {
                "name": "Melee Specialist",
                "description": "Can re-roll any single `Melee` roll once per turn. Can also gain a new specialization at `3`, `4` and `5`, granting an additional die whenever a specialized melee weapon is used.",
                "traits": [],
                "custom_sections": [
                    (
                        "Melee",
                        "Can re-roll any single `Melee` roll once per turn. Can also gain a new specialization at `3`, `4` and `5`, granting an additional die whenever a specialized melee weapon is used.",
                    )
                ],
            },
        ],
        ability_specialty=TraitCategory.TALENTS,
        attribute_specialty=TraitCategory.PHYSICAL,
        specific_abilities=[
            "Alertness",
            "Athletics",
            "Brawl",
            "Demolitions",
            "Dodge",
            "Firearms",
            "Melee",
            "Stealth",
            "Survival",
        ],
    )
    ASCETIC = CharacterConceptValue(
        name="Ascetic",
        description="Disciplined martial artists who harnesses their inner chi to perform incredible feats and attacks.",
        examples="Martial Artist, Dojo Owner, Competitor, Athlete, Bodybuilder, Body Hacker",
        num_abilities=2,
        percentile_range=(45, 52),
        abilities=[
            {
                "name": "Focus",
                "description": "Gathering their Chi, the monk can resist gases, poisons, psionic attacks, and hold their breath one turn per existing `stamina`+ `willpower`.  Monks are immune to the vampiric discipline of `Dominate`.",
                "traits": [],
                "custom_sections": [
                    (
                        "Focus",
                        "Gathering their Chi, the monk can resist gases, poisons, psionic attacks, and hold their breath one turn per existing `stamina`+ `willpower`.  Monks are immune to the vampiric discipline of `Dominate`.",
                    )
                ],
            },
            {
                "name": "Iron hand",
                "description": "Deliver a single punch, once per scene, with damage augmented by spending `willpower`, `1` point per damage level.",
                "traits": [],
                "custom_sections": [
                    (
                        "Iron Hand",
                        "Deliver a single punch, once per scene, with damage augmented by spending `willpower`, `1` point per damage level.",
                    )
                ],
            },
        ],
        ability_specialty=TraitCategory.TALENTS,
        attribute_specialty=TraitCategory.PHYSICAL,
        specific_abilities=["Alertness", "Athletics", "Brawl", "Dodge", "Melee", "Stealth"],
    )
    CRUSADER = CharacterConceptValue(
        name="Crusader",
        description="Dedicated sentinels sworn to a code of conduct, armed with divine, academic, and martial skills.",
        examples="Government Agent, Lawyer, Judge, Zealot, Terrorist, Inquisitor",
        num_abilities=1,
        percentile_range=(53, 60),
        abilities=[
            {
                "name": "Incorruptible",
                "description": "Crusaders gain the Healer's `Heal` and `Faith` ability but gain only one dot for it.  Crusaders gain the Fighters specialization and choose a single weapon they are loyal to and stick with it.",
                "traits": [],
                "custom_sections": [
                    (
                        "Heal",
                        "Heal 3 health levels to a target once per turn.  Any First Aid or Medicine roles are also automatically granted one success.",
                    ),
                    (
                        "True Faith",
                        "Starts with a Faith of `3`, equivalent to a Discipline.  Clerics can repel supernatural beings for every success on a Faith role.",
                    ),
                    (
                        "Specialization",
                        "A single combat specialization at only `3` dots, but without additional specializations at `4` and `5`.  Crusaders choose a single weapon they are loyal to and stick with it.",
                    ),
                ],
            },
        ],
        ability_specialty=TraitCategory.KNOWLEDGES,
        attribute_specialty=TraitCategory.MENTAL,
        specific_abilities=[
            "Academics",
            "Investigation",
            "Occult",
            "Politics",
            "Computer",
            "Alertness",
            "Leadership",
            "Etiquette",
        ],
    )
    URBAN_TRACKER = CharacterConceptValue(
        name="Urban Tracker",
        description="Skilled hunters and trackers with a deep connection to the wilderness and survival skills, or the equivalent for the urban jungle.",
        examples="Hunter, Tracker, Long Range Recon Patrol, Sniper, Wildlife Photographer, Park Ranger, Paparazzo",
        num_abilities=2,
        percentile_range=(61, 68),
        abilities=[
            {
                "name": "Camouflage",
                "description": "The Ranger can camouflage into their preferred environment given 1 turn of preparation.  This is not invisibility!  They can be detected on a `Perception` (or `Focus`) roll with a difficulty of `8`. Any attacks made from this position are considered surprise attacks.",
                "traits": [],
                "custom_sections": [
                    (
                        "Camouflage",
                        "The Ranger can camouflage into their preferred environment given `1` turn of preparation. Any attacks made from this position are considered surprise attacks.",
                    )
                ],
            },
            {
                "name": "Surprise Attack",
                "description": "Surprise attacks do an additional `3` successes of damage. This is a first-strike ability and subsequent attacks are no longer a surprise unless they can be plausibly silent.",
                "traits": [],
                "custom_sections": [
                    (
                        "Surprise Attack",
                        "Surprise attacks do an additional `3` successes of damage.",
                    )
                ],
            },
        ],
        ability_specialty=TraitCategory.SKILLS,
        attribute_specialty=TraitCategory.MENTAL,
        specific_abilities=[
            "Alertness",
            "Animal Ken",
            "Athletics",
            "Firearms",
            "Stealth",
            "Streetwise",
            "Survival",
        ],
    )
    UNDER_WORLDER = CharacterConceptValue(
        name="Under-worlder",
        description="Sneaky and dexterous individuals skilled in stealth, lock picking, and traps.",
        examples="Burglar, Lockpicker, Hacker, Safe-Cracker, Getaway Car Driver, Forger, Fence, Spy",
        num_abilities=3,
        percentile_range=(69, 76),
        abilities=[
            {
                "name": "Tools of the Trade",
                "description": "The character has an object: (a set of lockpicks, a laser drill, a getaway car, a printing press) -- when used, decreases the difficulty by `2`. This means, for example, a Forger will have a standard difficulty of 4 to attempt any forgery, provided they have their printing press, and a cat burglar can get in anywhere, with his rope and lockpicks.",
                "traits": [],
                "custom_sections": [],
            },
            {
                "name": "Professional",
                "description": "Any single `security` roll is done at a `-1` difficulty.",
                "traits": [],
                "custom_sections": [("Professional", "`+1` to any single `security` roll.")],
            },
            {
                "name": "Lay Low",
                "description": "They give off no paper trail, have multiple alternative identities, and their documents will stand up to anything short of a sustained FBI investigation.",
                "traits": [("Arcane", 2, "BACKGROUNDS")],
                "custom_sections": [
                    (
                        "Lay Low",
                        "`+2` dots on any rolls to evade pursuit, lose a tail, escape the police, or on any sneak roll.",
                    )
                ],
            },
        ],
        ability_specialty=TraitCategory.SKILLS,
        attribute_specialty=TraitCategory.SOCIAL,
        specific_abilities=[
            "Alertness",
            "Investigation",
            "Larceny",
            "Security",
            "Stealth",
            "Streetwise",
            "Subterfuge",
        ],
    )
    SCIENTIST = CharacterConceptValue(
        name="Scientist",
        description="Experts who draw power from their study of esoteric knowledge, with unique and potent abilities and gear.",
        examples="Debunker, Psychologist, Egyptologist, Filmographer, Data Scientist, Hematologist, Cryptozoologist, Grad Student, Weird Physicist",
        num_abilities=1,
        percentile_range=(77, 84),
        abilities=[
            {
                "name": "Delicate Equipment",
                "description": "Choose any Thaumaturgical Paths from the Vampire or Sorcerer book. Apply `3` dots spread however. These should be represented as Tools or scientific equipment that generate the effect. The Lure of Flames might be an experimental flamethrower or backpack-mounted Laser, Lightning might be some weather equipment, and so on. The equipment can be carried gear, but must be present to create the effect.",
                "traits": [],
                "custom_sections": [],
            },
        ],
        ability_specialty=TraitCategory.KNOWLEDGES,
        attribute_specialty=TraitCategory.MENTAL,
        specific_abilities=[
            "Academics",
            "Computer",
            "Etiquette",
            "Investigation",
            "Linguistics",
            "Occult",
            "Science",
        ],
    )
    TRADESMAN = CharacterConceptValue(
        name="Tradesman",
        description="Skilled artisans or laborers who excel in a specific trade or craft, such as blacksmithing, carpentry, or alchemy, often creating items of great value.",
        examples="Construction, Carpenter, Plumber, Key Grip, Truck Driver, Uber Driver, Union Man",
        num_abilities=2,
        percentile_range=(85, 92),
        abilities=[
            {
                "name": "Hardiness",
                "description": "The equivalent of `Fortitude` `1`.  All attacks sustained automatically soak `1` success at no cost.",
                "traits": [("Fortitude", 1, "DISCIPLINES")],
                "custom_sections": [],
            },
            {
                "name": "Handy",
                "description": "Free dot in `Repair` and `Crafts`.",
                "traits": [("Repair", 1, "SKILLS"), ("Crafts", 1, "SKILLS")],
                "custom_sections": [],
            },
        ],
        ability_specialty=TraitCategory.SKILLS,
        attribute_specialty=TraitCategory.PHYSICAL,
        specific_abilities=["Crafts", "Drive", "Repair", "Survival", "Brawl", "Leadership"],
    )
    BUSINESSMAN = CharacterConceptValue(
        name="Businessman",
        description="Astute and savvy individuals focused on commerce and negotiation, skilled in the art of deal-making and resource management.",
        examples="Professional, Salesman, Girlboss, Entrepreneur, Small Business Owner, Finance Bro, LinkedIn Influencer, Middle Manager, Storekeeper, Barista, In Marketing",
        num_abilities=1,
        percentile_range=(93, 100),
        abilities=[
            {
                "name": "Persuasion",
                "description": "The Businessman can enthrall his enemies and win them over with her powers of facts and logic.  This is less of a fast power and more of a sustained one.",
                "traits": [("Resources", 2, "BACKGROUNDS")],
                "custom_sections": [
                    ("Persuasion", "`1` automatic success to `Leadership` or `Subterfuge` rolls.")
                ],
            },
        ],
        ability_specialty=TraitCategory.KNOWLEDGES,
        attribute_specialty=TraitCategory.SOCIAL,
        specific_abilities=[
            "Finance",
            "Leadership",
            "Subterfuge",
            "Etiquette",
            "Politics",
            "Expression",
            "Intimidation",
            "Performance",
        ],
    )

    @classmethod
    def get_member_by_value(cls, value: int) -> "CharacterConcept":
        """Find the corresponding enum member's name based on an integer value.

        Args:
            value (int): The integer value to look up.

        Returns:
            Optional[str]: The name of the enum member if found, otherwise None.
        """
        for member in cls:
            if not member.value.percentile_range:
                continue
            min_val, max_val = member.value.percentile_range
            if min_val <= value <= max_val:
                return member
        return None

    @classmethod
    def random_member(cls) -> "CharacterConcept":
        """Select a random member from the enum.

        Returns:
            CharClass: A random enum member.
        """
        return choice(list(cls))


class HunterCreed(Enum):
    """Enum for Hunter creeds."""

    DEFENDER: ClassVar[typed_dicts.HunterCreedDict] = {
        "name": "Defender",
        "description": "Protectors and _Defenders_ who seek to salvage or preserve what they can in the war against the unknown, perhaps to prove that the fight is worthwhile.",
        "conviction": 3,
        "attribute_specialty": TraitCategory.MENTAL,
        "ability_specialty": TraitCategory.TALENTS,
        "specific_abilities": ["Empathy"],
        "edges": ["Ward", "Rejuvenate", "Brand", "Champion", "Burn"],
        "range": (1, 14),
    }
    INNOCENT: ClassVar[typed_dicts.HunterCreedDict] = {
        "name": "Innocent",
        "description": "The curious, unabashed and wide-eyed, the _Innocent_ accept monsters on their own terms and seek simple resolution between creatures and humanity.",
        "conviction": 3,
        "attribute_specialty": TraitCategory.SOCIAL,
        "ability_specialty": TraitCategory.TALENTS,
        "specific_abilities": ["Empathy", "Subterfuge"],
        "edges": ["Hide", "Illuminate", "Radiate", "Confront", "Blaze"],
        "range": (15, 28),
    }
    JUDGE: ClassVar[typed_dicts.HunterCreedDict] = {
        "name": "Judge",
        "description": "The eyes and ears of the battle against monsters, _Judges_ seek to uphold the greater good, whether it means destroying creatures or sparing them and questioning other hunters' motives",
        "conviction": 3,
        "attribute_specialty": TraitCategory.MENTAL,
        "ability_specialty": TraitCategory.KNOWLEDGES,
        "specific_abilities": ["Investigation", "Law"],
        "edges": ["Discern", "Burden", "Balance", "Pierce", "Expose"],
        "range": (29, 42),
    }
    MARTYR: ClassVar[typed_dicts.HunterCreedDict] = {
        "name": "Martyr",
        "description": "Acting out of desperate passion, _Martyrs_ put themselves in harm's way to protect others or to alleviate some all-consuming guilt.",
        "conviction": 4,
        "attribute_specialty": TraitCategory.PHYSICAL,
        "ability_specialty": TraitCategory.TALENTS,
        "specific_abilities": ["Empathy", "Intimidation"],
        "edges": ["Demand", "Witness", "Ravage", "Donate", "Payback"],
        "range": (43, 56),
    }
    REDEEMER: ClassVar[typed_dicts.HunterCreedDict] = {
        "name": "Redeemer",
        "description": "Piercing the souls of the enemy, _Redeemers_ offer the hand of salvation to the deserving and strike down the irredeemable.",
        "conviction": 3,
        "attribute_specialty": TraitCategory.PHYSICAL,
        "ability_specialty": TraitCategory.SKILLS,
        "specific_abilities": ["Empathy"],
        "edges": ["Bluster", "Insinuate", "Respire", "Becalm", "Suspend"],
        "range": (57, 71),
    }
    AVENGER: ClassVar[typed_dicts.HunterCreedDict] = {
        "name": "Avenger",
        "description": "Holy terror personified, _Avengers_ accept only one end to the war: the destruction of the enemy.",
        "conviction": 4,
        "attribute_specialty": TraitCategory.PHYSICAL,
        "ability_specialty": TraitCategory.SKILLS,
        "specific_abilities": ["Firearms", "Dodge", "Brawl", "Melee"],
        "edges": ["Cleave", "Trail", "Smolder", "Surge", "Smite"],
        "range": (72, 85),
    }
    VISIONARY: ClassVar[typed_dicts.HunterCreedDict] = {
        "name": "Visionary",
        "description": "Introspective, questioning and doubtful, _Visionaries_ seek the ultimate goals of the war against the unknown, and they seek purpose for hunters as a whole.",
        "conviction": 3,
        "attribute_specialty": TraitCategory.MENTAL,
        "ability_specialty": TraitCategory.SKILLS,
        "specific_abilities": ["Leadership", "Expression", "Subterfuge", "Intimidation", "Occult"],
        "edges": ["Foresee", "Pinpoint", "Delve", "Restore", "Augur"],
        "range": (86, 100),
    }

    @classmethod
    def get_member_by_value(cls, value: int) -> "HunterCreed":
        """Find the corresponding enum member's name based on an integer value.

        Args:
            value (int): The integer value to look up.

        Returns:
            Optional[str]: The enum member if found, otherwise None.
        """
        for member in cls:
            min_val, max_val = member.value["range"]
            if min_val <= value <= max_val:
                return member
        return None

    @classmethod
    def random_member(cls) -> "HunterCreed":
        """Select a random member from the enum.

        Returns:
            HunterCreed: A random enum member.
        """
        return choice(list(cls))


# CHANNEL_PERMISSIONS: Dictionary containing a tuple mapping of channel permissions.
#     Format:
#         default role permission,
#         player role permission,
#         storyteller role permission

CHANNEL_PERMISSIONS: dict[str, tuple[ChannelPermission, ChannelPermission, ChannelPermission]] = {
    "default": (
        ChannelPermission.DEFAULT,
        ChannelPermission.DEFAULT,
        ChannelPermission.DEFAULT,
    ),
    "audit_log": (
        ChannelPermission.HIDDEN,
        ChannelPermission.HIDDEN,
        ChannelPermission.READ_ONLY,
    ),
    "storyteller_channel": (
        ChannelPermission.HIDDEN,
        ChannelPermission.HIDDEN,
        ChannelPermission.POST,
    ),
    "error_log_channel": (
        ChannelPermission.HIDDEN,
        ChannelPermission.HIDDEN,
        ChannelPermission.HIDDEN,
    ),
    "campaign_character_channel": (
        ChannelPermission.READ_ONLY,
        ChannelPermission.READ_ONLY,
        ChannelPermission.MANAGE,
    ),
}

### Dictionaries  ###

DICEROLL_THUMBS = {
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

BAD_WORDS = [
    "anal",
    "ass",
    "asshole",
    "bastard",
    "bitch",
    "blowjob",
    "bollocks",
    "boob",
    "boobies",
    "bugger",
    "cock",
    "cocksucker",
    "cum",
    "cunt",
    "dildo",
    "fuck",
    "fucker",
    "gangbang",
    "handjob",
    "masterbate",
    "milf",
    "motherfucker",
    "orgasm",
    "orgy",
    "penis",
    "piss",
    "poop",
    "sex",
    "sexy",
    "shit",
    "shite",
    "shitter",
    "tosser",
    "wank",
    "wanker",
    "slut",
    "tit",
    "titfuck",
    "tittyfuck",
    "tittyfucker",
    "tosser",
    "vagina",
    "wank",
    "whore",
]
# Create a list of singular and plural forms of the words in BAD_WORD_LIST.
BAD_WORD_LIST = BAD_WORDS + [p.plural(word) for word in BAD_WORDS]
BAD_WORD_PATTERN = re.compile(rf"\b({'|'.join(BAD_WORD_LIST)})\b", flags=re.IGNORECASE)

BOT_DESCRIPTIONS = [
    "sensual sorceress who leaves you spellbound and spent",
    "flirtatious firestarter igniting your desires while burning your world",
    "passionate predator who devours you in the night",
    "bewitching siren with a thirst for more than your attention",
    "enticing enchantress who takes you beyond the point of no return",
    "ravishing rogue who steals more than just your breath",
    "lusty liberator freeing you from virtue, only to imprison you in vice",
    "siren who serenades you into peril",
    "black widow with a kiss that's fatal",
    "fiery femme fatale who leaves you burned but begging for more",
    "enchanting empress who rules your most forbidden thoughts",
    "vixen who leaves a trail of destruction",
    "sublime seductress who dances you to the edge of reason",
    "irresistible icon who redefines your sense of sin and salvation"
    "enchantress who captivates you in her web of deceit",
    "sultry Silver Fang who leads you into a world of primal passion",
    "seductress with eyes that promise ecstasy and chaos",
    "dazzling temptress with daggers in her eyes",
    "spellbinding witch who makes you forget your name",
    "goddess who gives pleasure but exacts a price",
    "alluring angel with a devilish twist",
    "trusted bot who helps you play White Wolf's TTRPGs",
    "succubus who will yet have your heart",
    "maid servant here to serve your deepest desires",
    "guardian angel who watches over you",
    "steadfast Silent Strider who journeys through the Umbra on your behalf",
    "trustworthy Thaumaturge who crafts potent rituals for your adventures",
    "Lasombra who makes darkness your newfound comfort",
    "seductive Toreador who makes eternity seem too short",
    "enigmatic Tremere who binds you in a blood bond you can't resist",
    "charismatic Ventrue who rules your heart with an iron fist",
    "shadowy Nosferatu who lurks in the dark corners of your fantasies",
    "haunting Wraith who whispers sweet nothings from the Shadowlands",
    "resilient Hunter who makes you question who's really being hunted",
    "Tzimisce alchemist who shapes flesh and mind into a twisted masterpiece",
    "Giovanni necromancer who invites you to a banquet with your ancestors",
    "Assamite assassin who turns the thrill of the hunt into a deadly romance",
    "Caitiff outcast who makes you see the allure in being a pariah",
    "Malkavian seer who unravels the tapestry of your sanity with whispers of prophecies",
    "Brujah revolutionary who ignites a riot in your soul and a burning need for rebellion",
    "Tremere warlock who binds your fate with arcane secrets too irresistible to ignore",
    "Toreador muse who crafts a masterpiece out of your every emotion, leaving you entranced",
    "Gangrel shape-shifter who lures you into the untamed wilderness of your darkest desires",
    "Ravnos trickster who casts illusions that make you question the very fabric of your reality",
    "Sabbat crusader who drags you into a nightmarish baptism of blood and fire, challenging your very essence",
    "Ventrue aristocrat who ensnares you in a web of high-stakes politics, making you question your loyalties",
    "Hunter zealot who stalks the shadows of your mind, making you question your beliefs",
    "enigmatic sorcerer weaving a tapestry of cosmic mysteries, entrancing your logical faculties",
    "mystic oracle who plunges you into ethereal visions, making you question the tangible world",
    "servant who feasts on your vulnerabilities, creating an insatiable need for servitude",
]
