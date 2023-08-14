# type: ignore
"""Test the TraitService class."""
import pytest

from valentina.models import TraitService
from valentina.models.db_tables import Trait
from valentina.utils import errors


@pytest.mark.usefixtures("mock_db")
class TestTraitService:
    """Test the trait service."""

    trait_svc = TraitService()

    def test_fetch_all_class_traits(self) -> None:
        """Test fetch_all_class_traits().

        GIVEN a class name
        WHEN fetching all traits for that class
        THEN return only the traits associated with that class
        """
        traits = [x.name for x in self.trait_svc.fetch_all_class_traits("Vampire")]
        assert len(traits) == 63

        for t in ["Willpower", "Strength", "Firearms", "Humanity", "Celerity", "Blood Pool"]:
            assert t in traits

        for t in ["Correspondence", "Arete", "Gnosis", "Conviction"]:
            assert t not in traits

    def test_fetch_trait_id_from_name(self) -> None:
        """Test fetch_trait_id_from_name().

        GIVEN a trait name
        WHEN fetching the trait id for that name
        THEN return the trait id or raise NoMatchingItemsError
        """
        for t in ["Willpower", "Strength", "Firearms", "Humanity", "Celerity", "Blood Pool"]:
            t_id = Trait.get(Trait.name == t).id
            assert self.trait_svc.fetch_trait_id_from_name(t) == t_id

        with pytest.raises(errors.NoMatchingItemsError):
            self.trait_svc.fetch_trait_id_from_name("Exception")

    def test_fetch_trait_category(self) -> None:
        """Test fetch_trait_category().

        GIVEN a trait name
        WHEN fetching the trait category for that name
        THEN return the trait category or raise NoMatchingItemsError
        """
        assert self.trait_svc.fetch_trait_category("Willpower") == "Other"
        assert self.trait_svc.fetch_trait_category("Strength") == "Physical"
        t_id = Trait.get(Trait.name == "Willpower").id
        assert self.trait_svc.fetch_trait_category(t_id) == "Other"
        t_id = Trait.get(Trait.name == "Strength").id
        assert self.trait_svc.fetch_trait_category(t_id) == "Physical"

        with pytest.raises(errors.NoMatchingItemsError, match=r"Trait `\w+` not found"):
            self.trait_svc.fetch_trait_category("Exception")

        with pytest.raises(errors.NoMatchingItemsError, match=r"Trait `\w+` not found"):
            self.trait_svc.fetch_trait_category(999999)

    def test_purge(self) -> None:
        """Test purge().

        GIVEN a trait name
        WHEN purging that trait
        THEN purge the cache
        """
        assert len(self.trait_svc.class_traits) > 0
        self.trait_svc.purge()
        assert len(self.trait_svc.class_traits) == 0

    def test_fetch_all_traits_one(self):
        """Test TraitService.fetch_all_traits().

        GIVEN a database with a guild
        WHEN TraitService.fetch_all_traits() is called
        THEN the traits are returned as a dictionary
        """
        returned = self.trait_svc.fetch_all_traits(guild_id=1)
        assert isinstance(returned, dict)
        assert "Test_Trait" in returned["Skills"]
        assert returned["Social"] == ["Appearance", "Charisma", "Manipulation"]

    def test_fetch_all_traits_two(self):
        """Test TraitService.fetch_all_traits().

        GIVEN a database with a guild
        WHEN TraitService.fetch_all_traits() is called with flat_list=True
        THEN the traits are returned as a list
        """
        returned = self.trait_svc.fetch_all_traits(guild_id=1, flat_list=True)
        assert isinstance(returned, list)
        for i in ["Test_Trait", "Charisma", "Manipulation", "Appearance"]:
            assert i in returned
