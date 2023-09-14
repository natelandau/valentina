# type: ignore
"""Test the MacroService class."""
from uuid import uuid4

import pytest

from valentina.models import MacroService
from valentina.models.db_tables import Macro, Trait
from valentina.utils import errors


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
        # Given an empty cache and no macros for a user
        self.macro_svc._macro_cache = {}
        for m in Macro.select():
            m.delete_instance()

        macro = Macro.create(
            guild=1,
            user=1,
            name=str(uuid4()).split("-")[0],
            abbreviation="tm",
            description="test description",
            content="test_content",
            trait_one="test_trait_one",
            trait_two="test_trait_two",
        )

        # WHEN the macros are fetched
        result = self.macro_svc.fetch_macros(1, 1)

        # THEN the database is queried and the cache is updated
        captured = caplog.text
        assert "DATABASE: Fetch macros" in captured
        assert "CACHE: Fetch macros" not in captured
        assert macro in result
        assert isinstance(result, list)
        assert macro in self.macro_svc._macro_cache["1_1"]

        # WHEN the macros are fetched again
        result = self.macro_svc.fetch_macros(1, 1)
        captured = caplog.text

        # THEN the cache is used
        assert "CACHE: Fetch macros" in captured
        assert macro in result
        assert isinstance(result, list)
        assert macro in self.macro_svc._macro_cache["1_1"]

    def test_create_macro_one(self, mocker, mock_ctx, caplog):
        """Test creating a macro.

        GIVEN a macro service
        WHEN a macro is created
        THEN the database is updated
        """
        # Mock the MacroTrait.create_from_trait_name method
        mocker.patch(
            "valentina.models.db_tables.MacroTrait.create_from_trait_name", return_value=None
        )

        # Grab a Trait object to use
        trait = Trait.get_by_id(1)

        # Verify the new macro is not already in the cache
        assert len(self.macro_svc._macro_cache) == 1

        # Create the new macro
        result = self.macro_svc.create_macro(mock_ctx, "new_macro", trait, trait, "nm", "new macro")
        captured = caplog.text
        assert "DATABASE: Create macro new_macro for Test User" in captured

        # Verify the macro was created
        assert result.name == "new_macro"

        # Verify the cache is purged
        assert len(self.macro_svc._macro_cache) == 0

    def test_create_macro_two(self, mocker, mock_ctx):
        """Test creating a macro.

        GIVEN a macro service
        WHEN a macro already exists with the same name
        THEN raise a ValidationError
        """
        # Mock the MacroTrait.create_from_trait_name method
        mocker.patch(
            "valentina.models.db_tables.MacroTrait.create_from_trait_name", return_value=None
        )

        # Grab a Trait object to use
        trait = Trait.get_by_id(1)

        # Create the new macro
        with pytest.raises(
            errors.ValidationError,
            match=r"Macro named `\w+` already exists",
        ):
            self.macro_svc.create_macro(mock_ctx, "new_macro", trait, trait, "nm", "new macro")

    def test_create_macro_three(self, mocker, mock_ctx):
        """Test creating a macro.

        GIVEN a macro service
        WHEN a macro already exists with the same abbreviation
        THEN raise a ValidationError
        """
        # Mock the MacroTrait.create_from_trait_name method
        mocker.patch(
            "valentina.models.db_tables.MacroTrait.create_from_trait_name", return_value=None
        )

        # Grab a Trait object to use
        trait = Trait.get_by_id(1)

        # Create the new macro
        with pytest.raises(
            errors.ValidationError,
            match=r"Macro named `\w+` already exists",
        ):
            self.macro_svc.create_macro(mock_ctx, "new_macro", trait, trait, "nm", "new macro")

    def test_delete_macro_one(self, mock_ctx, caplog):
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
        self.macro_svc.delete_macro(mock_ctx, macro_to_delete)

        # Verify it was deleted
        captured = caplog.text
        assert "DATABASE: Delete macro throwaway_name" in captured

        # Verify the cache is purged
        assert len(self.macro_svc._macro_cache) == 0

        # Verify the macro is no longer in the database
        assert len(Macro.select()) == num_macros - 1
