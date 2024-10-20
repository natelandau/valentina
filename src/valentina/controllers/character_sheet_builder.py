"""Controller for displaying a character sheet."""

from dataclasses import dataclass, field
from typing import assert_never

from valentina.constants import CharClass, CharSheetSection, Emoji, TraitCategory
from valentina.models import Character, CharacterTrait, User


@dataclass
class SectionCategory:
    """A list of traits for a specific category."""

    category: TraitCategory
    traits: list[CharacterTrait]


@dataclass
class SheetSection:
    """A section of the character sheet."""

    section: CharSheetSection
    category: list[SectionCategory] = field(default_factory=list)


class CharacterSheetBuilder:
    """Controller for displaying a character sheet."""

    def __init__(self, character: Character):
        """Initialize the character sheet controller.

        Args:
            character (Character): The character to display.
        """
        self.character = character

    def fetch_sheet_character_traits(self, show_zeros: bool = False) -> list[SheetSection]:
        """Constructs the character sheet by organizing traits into their respective sections.  These can be called by the view to display the character sheet.

            for section in self.fetch_sheet_character_traits(show_zeros=False):
                print(f"Section: {section.section.name}")
                for category in section.category:
                    print(f"Category: {category.category.name}")
                    for trait in category.traits:
                        print(f"Trait: {trait.name}")

        Args:
            show_zeros (bool): If True, include traits with zero values. Defaults to False.

        Returns:
            list[SheetSection]: A list of SheetSection objects representing the organized character sheet.
        """
        sheet: list[SheetSection] = []

        for section in CharSheetSection.get_members_in_order():
            if section == CharSheetSection.NONE:
                continue

            # Get the traits for the section
            category = [
                SectionCategory(category=cat, traits=traits)
                for cat in TraitCategory.get_members_in_order(section=section)
                if (
                    traits := self.character.fetch_traits_by_section(
                        category=cat, show_zeros=show_zeros
                    )
                )
            ]

            # Add the section with its groups to the sheet
            sheet.append(SheetSection(section=section, category=category))

        return sheet

    async def fetch_sheet_profile(self, storyteller_view: bool = False) -> dict:
        """Fetches the character's profile information for the character sheet.

        Returns:
            dict: A dictionary containing the character's profile information.
        """
        profile = {
            "class": self.character.char_class_name.title(),
            "alive": Emoji.ALIVE.value if self.character.is_alive else Emoji.DEAD.value,
            "concept": self.character.concept_name.title() if self.character.concept_name else "-",
            "demeanor": self.character.demeanor.title() if self.character.demeanor else "-",
            "nature": self.character.nature.title() if self.character.nature else "-",
            "dob": self.character.dob.strftime("%Y-%m-%d") if self.character.dob else "",
            "age": self.character.age if self.character.age else "",
        }

        match self.character.char_class:
            case CharClass.WEREWOLF | CharClass.CHANGELING:
                profile["tribe"] = self.character.tribe.title() if self.character.tribe else "-"
                profile["auspice"] = (
                    self.character.auspice.title() if self.character.auspice else "-"
                )
                profile["breed"] = self.character.breed.title() if self.character.breed else "-"
                profile["totem"] = self.character.totem.title() if self.character.totem else "-"
            case CharClass.VAMPIRE:
                profile["clan"] = self.character.clan.name.title() if self.character.clan else "-"
                profile["generation"] = (
                    self.character.generation.title() if self.character.generation else "-"
                )
                profile["sire"] = self.character.sire.title() if self.character.sire else "-"
            case CharClass.MAGE:
                profile["tradition"] = (
                    self.character.tradition.title() if self.character.tradition else "-"
                )
                profile["essence"] = (
                    self.character.essence.title() if self.character.essence else "-"
                )
            case CharClass.HUNTER:
                profile["creed"] = (
                    self.character.creed_name.title() if self.character.creed_name else "-"
                )
            case CharClass.MORTAL | CharClass.GHOUL | CharClass.SPECIAL:
                pass
            case CharClass.COMMON | CharClass.NONE | CharClass.OTHER:
                pass
            case _:
                assert_never(self.character.char_class)

        if storyteller_view:
            character_owner = await User.get(self.character.user_owner, fetch_links=False)
            profile["player"] = character_owner.name
            profile["character type"] = (
                "Player Character"
                if self.character.type_player
                else "Storyteller Character"
                if self.character.type_storyteller
                else ""
            )

        return {
            k.title(): str(v).title().replace("_", " ")
            for k, v in profile.items()
            if v and v != "None"
        }
