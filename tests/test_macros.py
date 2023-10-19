# type: ignore
"""Test the MacroService class."""
from uuid import uuid4

import pytest

from valentina.models import MacroService
from valentina.models.sqlite_models import CustomTrait, GuildUser, Macro, MacroTrait, Trait
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
        user = GuildUser.get_by_id(1)
        for m in Macro.select():
            m.delete_instance()

        macro = Macro.create(
            guild=1,
            user=user,
            name=str(uuid4()).split("-")[0],
            abbreviation="tm",
            description="test description",
            content="test_content",
            trait_one="test_trait_one",
            trait_two="test_trait_two",
        )

        # WHEN the macros are fetched
        result = self.macro_svc.fetch_macros(user)

        # THEN the database is queried and the cache is updated
        captured = caplog.text
        assert "DATABASE: Fetch macros" in captured
        assert "CACHE: Fetch macros" not in captured
        assert macro in result
        assert isinstance(result, list)
        assert macro in self.macro_svc._macro_cache["1_1"]

        # WHEN the macros are fetched again
        result = self.macro_svc.fetch_macros(user)
        captured = caplog.text

        # THEN the cache is used
        assert "CACHE: Fetch macros" in captured
        assert macro in result
        assert isinstance(result, list)
        assert macro in self.macro_svc._macro_cache["1_1"]

    def test_create_macro_one(self, mock_ctx, caplog):
        """Test creating a macro.

        GIVEN a macro service
        WHEN a macro is created
        THEN the database is updated
        """
        # Grab database to use
        trait = Trait.get_by_id(1)
        custom_trait = CustomTrait.get_by_id(1)
        user = GuildUser.get_by_id(1)

        # Verify the new macro is not already in the cache
        assert len(self.macro_svc._macro_cache) == 1

        # Create the new macro
        result = self.macro_svc.create_macro(
            mock_ctx, user, "new_macro", trait, custom_trait, "nm", "new macro"
        )
        captured = caplog.text
        assert "DATABASE: Create macro new_macro for [1] test_user" in captured

        # Verify the macro was created
        assert result.name == "new_macro"
        assert (
            MacroTrait.select()
            .where(MacroTrait.macro == result.id, MacroTrait.trait == trait.id)
            .exists()
        )
        assert (
            MacroTrait.select()
            .where(MacroTrait.macro == result.id, MacroTrait.custom_trait == custom_trait.id)
            .exists()
        )

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
            "valentina.models.sqlite_models.MacroTrait.create_from_trait_name", return_value=None
        )

        # Grab a database object to use
        trait = Trait.get_by_id(1)
        user = GuildUser.get_by_id(1)

        # Create the new macro
        with pytest.raises(
            errors.ValidationError,
            match=r"Macro named `\w+` already exists",
        ):
            self.macro_svc.create_macro(
                mock_ctx, user, "new_macro", trait, trait, "nm", "new macro"
            )

    def test_create_macro_three(self, mocker, mock_ctx):
        """Test creating a macro.

        GIVEN a macro service
        WHEN a macro already exists with the same abbreviation
        THEN raise a ValidationError
        """
        # Mock the MacroTrait.create_from_trait_name method
        mocker.patch(
            "valentina.models.sqlite_models.MacroTrait.create_from_trait_name", return_value=None
        )

        # Grab a database object to use
        trait = Trait.get_by_id(1)
        user = GuildUser.get_by_id(1)

        # Create the new macro
        with pytest.raises(
            errors.ValidationError,
            match=r"Macro named `\w+` already exists",
        ):
            self.macro_svc.create_macro(
                mock_ctx, user, "new_macro", trait, trait, "nm", "new macro"
            )

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

    def test_fetch_macro_traits(self, mock_ctx, caplog):
        """Test fetching macro traits."""
        # Set up the test

        # Delete all macros
        for m in Macro.select():
            m.delete_instance()

        # Delete all MacroTraits
        for mt in MacroTrait.select():
            mt.delete_instance()

        trait = Trait.get_by_id(1)
        custom_trait = CustomTrait.get_by_id(1)

        self.macro_svc._macro_cache = {}
        self.macro_svc._trait_cache = {}

        macro = Macro.create(
            guild=mock_ctx.guild.id,
            user=mock_ctx.author.id,
            name=str(uuid4()).split("-")[0],
            abbreviation="tm",
            description="test description",
            content="test_content",
        )
        MacroTrait.create_from_trait(macro, trait)
        MacroTrait.create_from_trait(macro, custom_trait)

        # WHEN the macro traits are fetched
        result = self.macro_svc.fetch_macro_traits(macro)
        text = caplog.text

        # THEN the database is queried and the cache is updated
        assert result == [trait, custom_trait]
        assert self.macro_svc._trait_cache == {1: [trait, custom_trait]}
        assert "DATABASE: Fetch traits for" in text
        assert "CACHE: Fetch traits for" not in text

        # WHEN the macro traits are fetched again
        caplog.clear()
        result = self.macro_svc.fetch_macro_traits(macro)
        text = caplog.text

        # THEN the cache is used
        assert result == [trait, custom_trait]
        assert self.macro_svc._trait_cache == {1: [trait, custom_trait]}
        assert "DATABASE: Fetch traits for" not in text
        assert "CACHE: Fetch traits for" in text

    def test_purge_cache(self, mock_ctx, mocker):
        """Test purging the macro cache."""
        # Create mock objects
        mock_macro1 = mocker.MagicMock()
        mock_macro1.id = 1

        mock_macro2 = mocker.MagicMock()
        mock_macro2.id = 2

        mock_macro3 = mocker.MagicMock()
        mock_macro3.id = 3

        mock_macro4 = mocker.MagicMock()
        mock_macro4.id = 4

        mock_macro5 = mocker.MagicMock()
        mock_macro5.id = 5

        mock_macro6 = mocker.MagicMock()
        mock_macro6.id = 5

        # Set up the test
        self.macro_svc._macro_cache = {
            "1_1": [mock_macro1, mock_macro2, mock_macro3],
            "1_2": [mock_macro4, mock_macro5, mock_macro6],
        }
        self.macro_svc._trait_cache = {
            1: [1, 2, 3],
            2: [4, 5, 6],
            3: [7, 8, 9],
            4: [10, 11, 12],
            5: [13, 14, 15],
            6: [16, 17, 18],
        }

        # WHEN the cache is purged with a guild
        self.macro_svc.purge_cache(mock_ctx)

        # THEN the cache is purged for that guild
        assert self.macro_svc._macro_cache == {
            "1_2": [mock_macro4, mock_macro5, mock_macro6],
        }
        assert self.macro_svc._trait_cache == {
            4: [10, 11, 12],
            5: [13, 14, 15],
            6: [16, 17, 18],
        }

        # WHEN the cache is purged without a guild
        self.macro_svc.purge_cache()

        # THEN the cache is purged for all guilds
        assert self.macro_svc._macro_cache == {}
        assert self.macro_svc._trait_cache == {}

    def test_does_macro_exist(self, mock_ctx):
        """Test checking if a macro exists."""
        # Set up the test
        for m in Macro.select():
            m.delete_instance()

        # Delete all MacroTraits
        for mt in MacroTrait.select():
            mt.delete_instance()

        trait1 = Trait.get_by_id(1)
        trait2 = CustomTrait.get_by_id(1)
        trait3 = Trait.get_by_id(2)

        self.macro_svc._macro_cache = {}
        self.macro_svc._trait_cache = {}

        macro = Macro.create(
            guild=mock_ctx.guild.id,
            user=mock_ctx.author.id,
            name=str(uuid4()).split("-")[0],
            abbreviation="tm",
            description="test description",
            content="test_content",
        )
        MacroTrait.create_from_trait(macro, trait1)
        MacroTrait.create_from_trait(macro, trait2)

        # GIVEN traits which exist in the macro
        # WHEN the macro is checked
        result = self.macro_svc.fetch_macro_from_traits(mock_ctx, trait1, trait2)

        # THEN the macro is returned
        assert result == macro

        # GIVEN traits which do not exist in the macro
        # WHEN the macro is checked
        result = self.macro_svc.fetch_macro_from_traits(mock_ctx, trait1, trait3)

        # THEN None is returned
        assert result is None
