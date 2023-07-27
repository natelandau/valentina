# type: ignore
"""Test the UserService class."""


import pytest

from valentina.models import Macro
from valentina.models.database import GuildUser, User
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
