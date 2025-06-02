"""Controller for displaying a character sheet."""

from dataclasses import dataclass, field
from typing import assert_never

from valentina.constants import CharClass, CharSheetSection, EmojiDict, TraitCategory
from valentina.models import Campaign, Character, CharacterTrait, User
from valentina.utils.helpers import get_max_trait_value


@dataclass
class TraitForCreation:
    """A trait for editing on the character sheet. Data is used for creating a form for editing trait values and adding them to the character."""

    name: str
    max_value: int
    category: TraitCategory

    def __lt__(self, other: "TraitForCreation") -> bool:
        """Sort by name."""
        return self.name < other.name


@dataclass
class SectionCategory:
    """A list of traits for a specific category."""

    category: TraitCategory
    traits: list[CharacterTrait] = field(default_factory=list)
    traits_for_creation: list[TraitForCreation] = field(default_factory=list)

    @property
    def all_traits(self) -> list[CharacterTrait | TraitForCreation]:
        """All traits for the category."""
        return sorted(self.traits + self.traits_for_creation)


@dataclass
class SheetSection:
    """A section of the character sheet."""

    section: CharSheetSection
    categories: list[SectionCategory] = field(default_factory=list)


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
            categories = [
                SectionCategory(category=cat, traits=traits)
                for cat in TraitCategory.get_members_in_order(section=section)
                if (
                    traits := self.character.fetch_traits_by_section(
                        category=cat,
                        show_zeros=show_zeros,
                    )
                )
            ]

            # Add the section with its groups to the sheet
            sheet.append(SheetSection(section=section, categories=categories))

        return sheet

    def fetch_all_class_traits(self) -> list[SheetSection]:
        """Fetches all possible traits for a character's class.  This method best suited for character creation where a form needs to be presented to the user for entering initial trait values.

        Returns:
            list[SheetSection]: A list of SheetSection objects representing the organized character sheet.
        """
        sheet: list[SheetSection] = []
        for section in CharSheetSection.get_members_in_order():
            if section == CharSheetSection.NONE:
                continue

            categories = []
            for trait_cat in TraitCategory.get_members_in_order(
                section=section,
                char_class=self.character.char_class,
            ):
                traits_to_create = []
                for trait_name in trait_cat.get_all_class_trait_names(
                    char_class=self.character.char_class,
                ):
                    trait_to_create = TraitForCreation(
                        name=trait_name,
                        category=trait_cat,
                        max_value=get_max_trait_value(trait_name, trait_cat.name),
                    )
                    traits_to_create.append(trait_to_create)

                categories.append(
                    SectionCategory(category=trait_cat, traits_for_creation=traits_to_create),
                )

            sheet.append(SheetSection(section=section, categories=categories))

        return sheet

    def fetch_all_class_traits_unorganized(self) -> list[TraitForCreation]:
        """Fetches all possible traits for a character's class in a flat list.  This method best suited for character creation where a form needs to be presented to the user for entering initial trait values.

        Returns:
            list[TraitForCreation]: A flat list of TraitForCreation objects.
        """
        unorganised_traits = []
        for s in self.fetch_all_class_traits():
            for category in s.categories:
                unorganised_traits.extend(list(category.traits_for_creation))
        return unorganised_traits

    async def fetch_sheet_profile(  # noqa: C901, PLR0912
        self,
        storyteller_view: bool = False,
        is_web_ui: bool = False,
    ) -> dict:
        """Fetches the character's profile information for the character sheet.

        Args:
            storyteller_view (bool): If True, include storyteller specific information. Defaults to False.
            is_web_ui (bool): If True, include web ui specific information. Defaults to False.

        Returns:
            dict: A dictionary containing the character's profile information.
        """
        if is_web_ui:
            alive_value = (
                '<i class="fa-regular fa-face-smile"></i>'
                if self.character.is_alive
                else '<i class="fa-solid fa-skull-crossbones"></i>'
            )
        else:
            alive_value = EmojiDict.ALIVE if self.character.is_alive else EmojiDict.DEAD

        profile = {
            "class": self.character.char_class_name.title(),
            "alive": alive_value,
            "concept": self.character.concept_name.title() if self.character.concept_name else "-",
            "demeanor": self.character.demeanor.title() if self.character.demeanor else "-",
            "nature": self.character.nature.title() if self.character.nature else "-",
            "dob": self.character.dob.strftime("%Y-%m-%d") if self.character.dob else "",
            "age": self.character.age if self.character.age else "",
        }

        match self.character.char_class:
            case CharClass.WEREWOLF | CharClass.CHANGELING:
                profile["tribe"] = (
                    self.character.tribe.title().replace("_", " ") if self.character.tribe else "-"
                )
                profile["auspice"] = (
                    self.character.auspice.title().replace("_", " ")
                    if self.character.auspice
                    else "-"
                )
                profile["breed"] = (
                    self.character.breed.title().replace("_", " ") if self.character.breed else "-"
                )
                profile["totem"] = (
                    self.character.totem.title().replace("_", " ") if self.character.totem else ""
                )
            case CharClass.VAMPIRE:
                profile["clan"] = (
                    self.character.clan.name.title().replace("_", " ")
                    if self.character.clan
                    else "-"
                )
                profile["generation"] = (
                    self.character.generation.title().replace("_", " ")
                    if self.character.generation
                    else "-"
                )
                profile["sire"] = (
                    self.character.sire.title().replace("_", " ") if self.character.sire else "-"
                )
            case CharClass.MAGE:
                profile["tradition"] = (
                    self.character.tradition.title().replace("_", " ")
                    if self.character.tradition
                    else "-"
                )
                profile["essence"] = (
                    self.character.essence.title().replace("_", " ")
                    if self.character.essence
                    else "-"
                )
            case CharClass.HUNTER:
                profile["creed"] = (
                    self.character.creed_name.title().replace("_", " ")
                    if self.character.creed_name
                    else "-"
                )
            case CharClass.MORTAL | CharClass.GHOUL | CharClass.SPECIAL:
                pass
            case CharClass.COMMON | CharClass.NONE | CharClass.OTHER:
                pass
            case _:
                assert_never(self.character.char_class)

        if character_owner := await User.get(int(self.character.user_owner), fetch_links=False):
            if is_web_ui:
                profile["owner"] = (
                    f"<a href='/user/{character_owner.id}'>{character_owner.name.title().replace('_', ' ')}</a>"
                )
            else:
                profile["owner"] = character_owner.name.title().replace("_", " ")

        if storyteller_view:
            profile["character type"] = (
                "Player Character"
                if self.character.type_player
                else "Storyteller Character"
                if self.character.type_storyteller
                else ""
            )

        if campaign := await Campaign.get(self.character.campaign, fetch_links=False):
            profile["campaign"] = (
                f"<a href='/campaign/{campaign.id}'>{campaign.name.title()}</a>"
                if is_web_ui
                else campaign.name.title()
            )

        return {k.title(): str(v) for k, v in profile.items() if v and v != "None"}

    def fetch_character_plus_all_class_traits(self) -> list[SheetSection]:
        """Fetches all a character's traits and suppliments them with all available traits for their character's class. This is useful for spending freebie points or experience points where players may want to assign points to traits their characters do not currently posses.

            Merge the traits and traits_for_creation lists for each category to get a full list of possible traits for the character sheet.

        Returns:
            list[SheetSection]: A list of SheetSection objects representing the organized character sheet.
        """
        all_character_traits = self.fetch_sheet_character_traits(show_zeros=True)
        all_class_traits = self.fetch_all_class_traits_unorganized()

        for section in all_character_traits:
            for category in section.categories:
                all_class_category_traits = [
                    t for t in all_class_traits if t.category == category.category
                ]
                for trait in all_class_category_traits:
                    if trait.name not in [x.name for x in category.traits]:
                        category.traits_for_creation.append(trait)

        return all_character_traits
