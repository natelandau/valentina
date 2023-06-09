# type: ignore
"""Test the UserService class."""


import pytest

from valentina.models.database import GuildUser, Macro, User
from valentina.models.database_services import UserService


@pytest.mark.usefixtures("mock_db")
class TestUserService:
    """Test the user service."""

    user_svc = UserService()

    def test_fetch_user(self, ctx_existing):
        """Test fetching a user.

        Given a context object with a user in the database
        When a user is fetched
        Then the user object is returned and added to the cache
        """
        # Confirm user object is returned
        assert self.user_svc.fetch_user(ctx_existing) == User(id=1, name="Test User")

        # Confirm user object is in the cache
        user_one = User(id=1)
        assert self.user_svc.user_cache["1_1"] == user_one

    def test_purge_all(self):
        """Test purging all users from the cache.

        Given a cache with users
        When the cache is purged
        Then the cache is empty
        """
        assert "1_1" in self.user_svc.user_cache
        self.user_svc.purge_cache()
        assert self.user_svc.user_cache == {}

    def test_fetch_user_two(self, ctx_new_user):
        """Test creating a user that is not in the cache or db.

        Given a context object with a user not in the database
        When that user is fetched
        Then the user is added to the cache and database
        """
        assert self.user_svc.fetch_user(ctx_new_user) == User(id=2, name="Test User 2")

        # Confirm added to cache
        assert "1_2" in self.user_svc.user_cache

        # Confirm added to database
        assert User.get_by_id(2).name == "Test User 2"
        assert GuildUser.get_by_id(2).user.name == "Test User 2"

    def test_purge_by_id(self, ctx_existing, ctx_new_user):
        """Test purging a user from the cache.

        Given a cache with two users
        When one user is purged
        Then the cache contains only the other user
        """
        # Confirm two users in cache
        assert self.user_svc.fetch_user(ctx_existing) == User(id=1, name="Test User")
        assert self.user_svc.fetch_user(ctx_new_user) == User(id=2, name="Test User 2")
        assert len(self.user_svc.user_cache) == 2

        # Purge one user
        self.user_svc.purge_cache(ctx_existing)

        # Confirm one user in cache
        assert len(self.user_svc.user_cache) == 1
        assert "1_1" not in self.user_svc.user_cache
        assert "1_2" in self.user_svc.user_cache

    def test_fetch_macros(self, ctx_existing):
        """Test fetching macros.

        Given a context object with a user in the database
        When macros are fetched for that user
        Then the macros are returned and added to the cache
        """
        assert self.user_svc.macro_cache == {}
        macros = self.user_svc.fetch_macros(ctx_existing)
        assert len(macros) == 1
        assert macros[0] == Macro(id=1, name="test_macro", content="test content")
        assert "1_1" in self.user_svc.macro_cache

    def test_fetch_macro(self, ctx_existing):
        """Test fetching macros.

        Given a context object with a user in the database
        When a macro is fetched for that user
        Then the macro is returned and added to the cache
        """
        assert self.user_svc.fetch_macro(ctx_existing, "test_macro") == Macro(
            id=1, name="test_macro", content="test content"
        )

    def test_create_macro(self, ctx_existing):
        """Test creating a macro.

        Given a context object with a user in the database
        When a macro is created
        Then the macro is added to the cache and database
        """
        self.user_svc.create_macro(
            ctx_existing,
            name="testmacro3",
            description="test content",
            abbreviation="t3",
            trait_one="test_trait_one",
            trait_two="test_trait_two",
        )

        # Confirm added to database
        assert Macro.get_by_id(2).name == "testmacro3"

    def test_delete_macro(self, ctx_existing):
        """Test deleting a macro.

        Given a context object with a user in the database
        When a macro is deleted
        Then the macro is removed from the cache and database
        """
        self.user_svc.delete_macro(ctx_existing, "test_macro")

        # Confirm deleted from database
        with pytest.raises(Macro.DoesNotExist):
            Macro.get_by_id(1)
