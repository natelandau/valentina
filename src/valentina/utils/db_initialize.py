"""When a new database is created, this file is used to populate it with the initial data.

IMPORTANT: If you change the data in this file, you must add/delete/migrate the corresponding in any existing databases!
"""
from loguru import logger
from playhouse.sqlite_ext import CSqliteExtDatabase
from semver import Version

from valentina.models.database import (
    Character,
    CharacterClass,
    CustomSection,
    CustomTrait,
    Macro,
    Trait,
    TraitCategory,
    TraitCategoryClass,
    TraitClass,
    TraitValue,
    VampireClan,
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
        "Streetwise",
        "Subterfuge",
    ],
    "Skills": [
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
    "Knowledges": [
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
    "Other": ["Willpower", "Desperation", "Reputation"],
}
mage_traits = {
    "Other": ["Humanity", "Arete", "Quintessence"],
    "Knowledges": ["Cosmology", "Enigmas"],
    "Skills": ["Technology"],
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
    "Resonance": ["Dynamic", "Entropic", "Static"],
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
    "Talents": ["Primal-Urge"],
    "Knowledges": ["Rituals", "Enigmas"],
    "Other": ["Gnosis", "Rage"],
    "Renown": ["Glory", "Honor", "Wisdom"],
}
hunter_traits = {
    "Skills": ["Crafts", "Demolitions", "Technology"],
    "Other": ["Conviction", "Faith", "Humanity"],
    "Virtues": ["Conscience", "Self-Control", "Courage"],
}
mortal_traits = {
    "Skills": ["Crafts", "Larceny"],
    "Other": ["Humanity"],
    "Virtues": ["Conscience", "Self-Control", "Courage"],
}


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

    def get_tables(self) -> list[str]:
        """Get all tables in the Database."""
        with self.db:
            cursor = self.db.execute_sql("SELECT name FROM sqlite_master WHERE type='table';")
            return [row[0] for row in cursor.fetchall()]

    def __0_8_2(self) -> None:
        """Migrate from database from v0.8.2."""
        logger.info("DATABASE: Migrate database to v0.8.2")
        self.db.execute_sql("ALTER TABLE characters ADD COLUMN security INTEGER DEFAULT 0;")

    def __0_12_0(self) -> None:  # noqa: C901, PLR0912
        """Migration from db v0.12.0."""
        logger.info("DATABASE: Migrate database from v0.12.0")

        # Update Trait values
        if "character_traits" in self.get_tables():
            logger.debug("DATABASE: Migrate trait values")
            tvs = {}
            for row in TraitValue.select():
                tvs[row.id] = {
                    "char": row.character_id,
                    "trait": row.trait_id,
                    "value": row.value,
                    "modified": row.modified,
                }
                row.delete_instance()

            for key, value in tvs.items():
                old_name = self.db.execute_sql(
                    "SELECT name FROM character_traits WHERE id =  ?;", (value["trait"],)
                ).fetchone()[0]

                if old_name.lower() == "larceny":
                    tvs[key]["new_id"] = "DROP"
                    continue

                new_trait = Trait.get_or_none(name=old_name)
                if not new_trait:
                    logger.debug(f"Trait {old_name} no longer exists. Dropping.")
                    tvs[key]["new_id"] = "DROP"
                    continue

                tvs[key]["new_id"] = new_trait.id

            self.db.execute_sql("DROP TABLE character_traits;")
            self.db.execute_sql("DROP TABLE trait_values;")

            # Now we can create the new table and insert the values
            with self.db:
                self.db.create_tables([TraitValue])

            for value in sorted(tvs.values(), key=lambda x: x["char"]):
                if value["new_id"] == "DROP":
                    continue

                character_class = Character.get(id=value["char"]).char_class
                if (
                    not TraitClass.get_or_none(
                        trait_id=value["new_id"], character_class=character_class
                    )
                    and value["value"] == 0
                ):
                    continue

                if not TraitValue.get_or_none(
                    character=value["char"], trait=value["new_id"], value=value["value"]
                ):
                    TraitValue.create(
                        character=value["char"],
                        trait=value["new_id"],
                        value=value["value"],
                        modified=value["modified"],
                    )
                else:
                    logger.debug(
                        f"Skip duplicate trait value for {Trait.get(id=value['new_id']).name} on {Character.get(id=value['char']).name}"
                    )

        # Update Custom Sections
        if self._column_exists("custom_sections", "guild_id"):
            logger.debug("DATABASE: Migrate custom sections")

            cursor = self.db.execute_sql("SELECT * FROM custom_sections;").fetchall()

            self.db.execute_sql("DROP TABLE custom_sections;")

            with self.db:
                self.db.create_tables([CustomSection])

            for _id, char, created, modified, description, _guild, title in cursor:
                CustomSection.create(
                    character=Character.get(id=char),
                    created=created,
                    modified=modified,
                    description=description,
                    title=title,
                )

        # Update Custom Traits
        if self._column_exists("custom_traits", "category"):
            logger.debug("DATABASE: Migrate custom traits")

            cursor = self.db.execute_sql("SELECT * FROM custom_traits;").fetchall()

            self.db.execute_sql("DROP TABLE custom_traits;")
            with self.db:
                self.db.create_tables([CustomTrait])

            for (
                _id,
                char,
                created,
                modified,
                description,
                _guild,
                name,
                category,
                value,
                max_value,
            ) in cursor:
                CustomTrait.create(
                    character=Character.get(id=char),
                    created=created,
                    modified=modified,
                    description=description,
                    name=name,
                    category=TraitCategory.get(name=category),
                    value=value,
                    max_value=max_value,
                )

        if self._column_exists("macros", "trait_one"):
            logger.debug("DATABASE: Migrate macros")
            self.db.execute_sql("DROP TABLE macros;")
            with self.db:
                self.db.create_tables([Macro])


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
            "Numina": ["Mage", "Mortal", "Hunter"],
            "Resonance": ["Mage"],
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
