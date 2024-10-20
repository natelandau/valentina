"""Controller for displaying a character sheet."""

from dataclasses import dataclass, field

from valentina.constants import CharSheetSection, TraitCategory
from valentina.models import Character, CharacterTrait


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

    def fetch_sheet_data(self, show_zeros: bool = False) -> list[SheetSection]:
        """Constructs the character sheet by organizing traits into their respective sections.  These can be called by the view to display the character sheet.

            for section in self.fetch_sheet_data(show_zeros=False):
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
