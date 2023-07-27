# type: ignore
"""Test the MacroService class."""
import pytest

from valentina.models import Macro, MacroService
from valentina.models.database import Trait


@pytest.mark.usefixtures("mock_db")
class TestMacroService:
    """Test the macro service."""

    macro_svc = MacroService()

    def test_fetch_macros_one(self, caplog):
        """Test fetching macros.

        GIVEN a macro service
        WHEN the macro cache is empty
        THEN the database is queried
        """
        macro = Macro.get_by_id(1)
        assert self.macro_svc._macro_cache == {}

        result = self.macro_svc.fetch_macros(1, 1)

        captured = caplog.text
        assert "DATABASE: Fetch macros for 1" in captured
        assert result == [macro]
        assert self.macro_svc._macro_cache == {"1_1": [macro]}

    def test_fetch_macros_two(self, caplog):
        """Test fetching macros.

        GIVEN a macro service
        WHEN the macro cache is full
        THEN pull from the cache, not the database
        """
        macro = Macro.get_by_id(1)
        assert self.macro_svc._macro_cache == {"1_1": [macro]}

        result = self.macro_svc.fetch_macros(1, 1)

        captured = caplog.text
        assert "CACHE: Fetch macros for 1" in captured
        assert result == [macro]
        assert self.macro_svc._macro_cache == {"1_1": [macro]}

    def test_create_macro_one(self, mocker, ctx_existing, caplog):
        """Test creating a macro.

        GIVEN a macro service
        WHEN a macro is created
        THEN the database is updated
        """
        # Mock the MacroTrait.create_from_trait_name method
        mocker.patch("valentina.models.MacroTrait.create_from_trait_name", return_value=None)

        # Grab a Trait object to use
        trait = Trait.get_by_id(1)

        # Verify the new macro is not already in the cache
        assert len(self.macro_svc._macro_cache) == 1

        # Create the new macro
        result = self.macro_svc.create_macro(
            ctx_existing, "new_macro", trait, trait, "nm", "new macro"
        )
        captured = caplog.text
        assert "DATABASE: Create macro new_macro for Test User" in captured

        # Verify the macro was created
        assert result.name == "new_macro"

        # Verify the cache is purged
        assert len(self.macro_svc._macro_cache) == 0

    def test_create_macro_two(self, mocker, ctx_existing):
        """Test creating a macro.

        GIVEN a macro service
        WHEN a macro already exists with the same name
        THEN raise a ValueError
        """
        # Mock the MacroTrait.create_from_trait_name method
        mocker.patch("valentina.models.MacroTrait.create_from_trait_name", return_value=None)

        # Grab a Trait object to use
        trait = Trait.get_by_id(1)

        # Create the new macro
        with pytest.raises(ValueError, match="Macro already exists"):
            self.macro_svc.create_macro(ctx_existing, "test_macro", trait, trait, "nm", "new macro")

    def test_create_macro_three(self, mocker, ctx_existing):
        """Test creating a macro.

        GIVEN a macro service
        WHEN a macro already exists with the same abbreviation
        THEN raise a ValueError
        """
        # Mock the MacroTrait.create_from_trait_name method
        mocker.patch("valentina.models.MacroTrait.create_from_trait_name", return_value=None)

        # Grab a Trait object to use
        trait = Trait.get_by_id(1)

        # Create the new macro
        with pytest.raises(ValueError, match="Macro already exists"):
            self.macro_svc.create_macro(ctx_existing, "new_macro", trait, trait, "tm", "new macro")

    def test_delete_macro_one(self, ctx_existing, caplog):
        """Test deleting a macro.

        GIVEN a macro service
        WHEN a macro is deleted
        THEN the database is updated and the cache is purged
        """
        # Create a macro to delete
        macro_to_delete = Macro.create(
            name="throwaway_name",
            abbreviation="abbreviation",
            description="description",
            user=1,
            guild=1,
        )

        num_macros = len(Macro.select())

        # Delete the macro
        self.macro_svc.delete_macro(ctx_existing, macro_to_delete)

        # Verify it was deleted
        captured = caplog.text
        assert "DATABASE: Delete macro throwaway_name" in captured

        # Verify the cache is purged
        assert len(self.macro_svc._macro_cache) == 0

        # Verify the macro is no longer in the database
        assert len(Macro.select()) == num_macros - 1
