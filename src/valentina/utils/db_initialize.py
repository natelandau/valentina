"""When a new database is created, this file is used to populate it with the initial data.

IMPORTANT: If you change the data in this file, you must add/delete/migrate the corresponding in any existing databases!
"""
from loguru import logger
from playhouse.sqlite_ext import CSqliteExtDatabase
from semver import Version

from valentina.models.database import (
    Character,
    CharacterClass,
    Trait,
    TraitCategory,
    TraitCategoryClass,
    TraitClass,
    TraitValue,
    VampireClan,
    time_now,
)

common_traits = {
    "Physical": ["Strength", "Dexterity", "Stamina"],
    "Social": ["Charisma", "Manipulation", "Appearance"],
    "Mental": ["Perception", "Intelligence", "Wits"],
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
        "Performance",
        "Persuasion",
        "Repair",
        "Security",
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
    "Other": ["Willpower", "Desperation", "Reputation"],
}
mage_traits = {
    "Other": ["Humanity", "Arete", "Quintessence"],
    "Virtues": ["Conscience", "Self-Control", "Courage"],
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
}
vampire_traits = {
    "Other": ["Blood Pool", "Humanity"],
    "Virtues": ["Conscience", "Self-Control", "Courage"],
    "Disciplines": [
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
}
werewolf_traits = {
    # TODO: Add these custom werewolf traits
    # "Talents"- Primal-Urge"
    # "Skills"- "Ranged"
    # "Knowledges"- "Legend-Lore"
    "Other": ["Gnosis", "Rage"],
    "Renown": ["Glory", "Honor", "Wisdom"],
}
hunter_traits = {
    "Other": ["Conviction", "Faith", "Humanity"],
    "Virtues": ["Conscience", "Self-Control", "Courage"],
}
mortal_traits = {"Other": ["Humanity"], "Virtues": ["Conscience", "Self-Control", "Courage"]}


class MigrateDatabase:
    """A class that handles migrating an existing database."""

    def __init__(self, db: CSqliteExtDatabase, bot_version: str, db_version: str) -> None:
        self.db = db
        self.bot_version = bot_version
        self.db_version = db_version

    def migrate(self) -> None:
        """Migrate the database to the latest version."""
        logger.debug("DATABASE: Begin migration")

        if Version.parse(self.db_version) <= Version.parse("0.8.2"):
            self.__0_8_2()

        if Version.parse(self.db_version) <= Version.parse("0.11.3"):
            self.__0_11_3()

        if Version.parse(self.db_version) <= Version.parse("0.12.0"):
            self.__0_12_0()

    def _column_exists(self, table: str, column: str) -> bool:
        """Check if a column exists in a table.

        Args:
            table (str): The table to check.
            column (str): The column to check.

        Returns:
            bool: Whether the column exists in the table.
        """
        db = self.db
        cursor = db.execute_sql(f"PRAGMA table_info({table})")
        columns = [row[1] for row in cursor.fetchall()]
        return column in columns

    def __0_8_2(self) -> None:
        """Migrate from database from v0.8.2."""
        logger.info("DATABASE: Migrate database to v0.8.2")
        self.db.execute_sql("ALTER TABLE characters ADD COLUMN security INTEGER DEFAULT 0;")

    def __0_11_3(self) -> None:
        """Migrate from database from v0.11.3."""
        logger.info("DATABASE: Migrate database to v0.11.3")

        # Populate the trait values table
        for trait in Trait.select():
            column_name = trait.name.lower().replace(" ", "_").replace("-", "_")
            if self._column_exists("characters", column_name):
                for character in Character.select():
                    logger.debug(f"DATABASE: Populate {trait.name} for {character.name}")
                    trait_value = self.db.execute_sql(
                        "SELECT "  # noqa: S608
                        + column_name
                        + " FROM characters WHERE id = "
                        + str(character.id)
                        + ";"
                    ).fetchone()[0]

                    TraitValue.create(
                        character=character,
                        trait=trait,
                        value=trait_value,
                        modified=time_now(),
                    )

        # Remove the trait columns from the character table
        for trait in Trait.select():
            column_name = trait.name.lower().replace(" ", "_").replace("-", "_")
            if self._column_exists("characters", column_name):
                self.db.execute_sql("ALTER TABLE characters DROP COLUMN " + column_name + ";")
                logger.debug(f"DATABASE: Remove {trait.name} from Character table")

    def __0_12_0(self) -> None:
        """Migration from db v0.12.0."""
        logger.warning("DATABASE: Migrate database from v0.12.0")


class PopulateDatabase:
    """A class that handles the populating a new database. This is only used when creating a new database.

    IMPORTANT: If you change the data in this file, you must add/delete/migrate the corresponding in any existing databases using the MigrateDatabase class!
    """

    def __init__(self, db: CSqliteExtDatabase) -> None:
        self.db = db

    def populate(self) -> None:
        """Populate the database with initial data."""
        self._character_classes()
        self._vampire_clans()
        self._trait_categories()
        self._traits()
        logger.info("DATABASE: Populate initial data")

    def _character_classes(self) -> None:
        """Create the initial character classes."""
        with self.db.atomic():
            for character_class in [
                "Mortal",
                "Vampire",
                "Werewolf",
                "Mage",
                "Hunter",
                "Other",
            ]:
                CharacterClass.insert(name=character_class).on_conflict_ignore().execute()
        logger.debug("DATABASE: Populate character classes")

    def _vampire_clans(self) -> None:
        """Create the initial character classes."""
        with self.db.atomic():
            for clan in [
                "Assamite",
                "Brujah",
                "Followers of Set",
                "Gangrel",
                "Giovanni",
                "Lasombra",
                "Malkavian",
                "Nosferatu",
                "Ravnos",
                "Toreador",
                "Tremere",
                "Tzimisce",
                "Ventrue",
            ]:
                VampireClan.insert(name=clan).on_conflict_ignore().execute()
        logger.debug("DATABASE: Populate vampire clans")

    def _trait_categories(self) -> None:
        """Create the initial trait categories."""
        # Dictionary of category and associated character classes
        categories = {
            "Backgrounds": ["Common"],
            "Disciplines": ["Vampire"],
            "Edges": ["Hunter"],
            "Flaws": ["Common"],
            "Gifts": ["Werewolf"],
            "Knowledges": ["Common"],
            "Mental": ["Common"],
            "Merits": ["Common"],
            "Other": ["Common"],
            "Paths": ["Common"],
            "Physical": ["Common"],
            "Renown": ["Werewolf"],
            "Skills": ["Common"],
            "Social": ["Common"],
            "Spheres": ["Mage"],
            "Talents": ["Common"],
            "Virtues": ["Common"],
        }
        with self.db.atomic():
            for category, classes in categories.items():
                cat = TraitCategory.insert(name=category).on_conflict_ignore().execute()

                if cat and "Common" in classes:
                    for c in CharacterClass.select():
                        TraitCategoryClass.insert(
                            character_class=c, category=cat
                        ).on_conflict_ignore().execute()
                elif cat:
                    for c in classes:
                        TraitCategoryClass.insert(
                            character_class=CharacterClass.get(name=c), category=cat
                        ).on_conflict_ignore().execute()

        logger.debug("DATABASE: Populate trait categories")

    def _traits(self) -> None:
        """Create the initial traits."""
        trait_dictionaries: list[dict[str, str | dict[str, list[str]]]] = [
            {"char_class": "Common", "dict": common_traits},
            {"char_class": "Mage", "dict": mage_traits},
            {"char_class": "Vampire", "dict": vampire_traits},
            {"char_class": "Werewolf", "dict": werewolf_traits},
            {"char_class": "Hunter", "dict": hunter_traits},
            {"char_class": "Mortal", "dict": mortal_traits},
        ]

        with self.db.atomic():
            for dictionary in trait_dictionaries:
                if isinstance(dictionary["dict"], dict):
                    for category, traits in dictionary["dict"].items():
                        for trait in traits:
                            t, _created = Trait.get_or_create(
                                name=trait,
                                category=TraitCategory.get_or_none(name=category),
                            )

                            if dictionary["char_class"] == "Common":
                                for c in CharacterClass.select():
                                    TraitClass.get_or_create(character_class=c, trait=t)
                            else:
                                TraitClass.get_or_create(
                                    character_class=CharacterClass.get(
                                        name=dictionary["char_class"]
                                    ),
                                    trait=t,
                                )

        logger.debug("DATABASE: Populate traits")
