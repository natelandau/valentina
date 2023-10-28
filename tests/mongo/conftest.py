# type: ignore
"""Shared fixtures for tests."""
import asyncio
import os
from pathlib import Path
from random import randint
from unittest.mock import MagicMock

import discord
import pytest
from beanie import init_beanie
from discord.ext import commands
from dotenv import dotenv_values
from faker import Faker

# from mongomock_motor import AsyncMongoMockClient
from motor.motor_asyncio import AsyncIOMotorClient

from valentina.models.mongo_collections import (
    Campaign,
    CampaignChapter,
    CampaignExperience,
    CampaignNote,
    CampaignNPC,
    Character,
    CharacterTrait,
    GlobalProperty,
    Guild,
    User,
    UserMacro,
)

fake = Faker()

# Import configuration from environment variables
DIR = Path(__file__).parents[2].absolute()
CONFIG = {
    **dotenv_values(DIR / ".env"),  # load shared variables
    **dotenv_values(DIR / ".env.secrets"),  # load sensitive variables
    **os.environ,  # override loaded values with environment variables
}
for k, v in CONFIG.items():
    CONFIG[k] = v.replace('"', "").replace("'", "").replace(" ", "")


@pytest.fixture(autouse=True)
async def _init_database():
    """Initialize the database."""
    # Create Motor client
    client = AsyncIOMotorClient(
        f"{CONFIG['VALENTINA_TEST_MONGO_URI']}/{CONFIG['VALENTINA_TEST_MONGO_DATABASE_NAME']}",
        tz_aware=True,
    )

    # Initialize beanie with the Sample document class and a database
    await init_beanie(
        database=client[CONFIG["VALENTINA_TEST_MONGO_DATABASE_NAME"]],
        document_models=[
            Campaign,
            CampaignChapter,
            # CampaignExperience,
            CampaignNote,
            CampaignNPC,
            Character,
            CharacterTrait,
            GlobalProperty,
            Guild,
            User,
            UserMacro,
        ],
    )

    yield

    # Drop the database after the test
    await asyncio.sleep(0.03)  # Ensure we cleanup before running the next test
    await client.drop_database(CONFIG["VALENTINA_TEST_MONGO_DATABASE_NAME"])


@pytest.fixture()
def create_character(create_user):
    """Factory to create a character object in the database."""

    async def make(
        no_traits: bool = False,
        add_to_user: bool = False,
        guild: int = randint(1, 9999999999),
        char_class_name: str = "MORTAL",
        type_chargen: bool = False,
        type_debug: bool = False,
        type_storyteller: bool = False,
        type_player: bool = False,
        user: User = None,
    ) -> Character:
        """Create a character object in the test database.

        Args:
            add_to_user (bool, optional): If true, add the character to the user. Defaults to False.
            guild (int, optional): The guild id of the character. Defaults to randint(1, 9999999999).
            char_class_name (str, optional): The class of the character. Defaults to "MORTAL".
            type_chargen (bool, optional): If true, the character is a chargen character. Defaults to False.
            type_debug (bool, optional): If true, the character is a debug character. Defaults to False.
            type_storyteller (bool, optional): If true, the character is a storyteller character. Defaults to False.
            type_player (bool, optional): If true, the character is a player character. Defaults to False.
            user (User, optional): The user to add the character to. Defaults to None.
            no_traits (bool, optional): If true, do not add any traits to the character. Defaults to False.
        """
        if not user:
            user = await create_user()

        character = Character(
            name_first=fake.first_name(),
            name_last=fake.last_name(),
            guild=guild,
            char_class_name=char_class_name,
            type_chargen=type_chargen,
            type_debug=type_debug,
            type_storyteller=type_storyteller,
            type_player=type_player,
            user_creator=user.id,
            user_owner=user.id,
        )
        await character.insert()

        if not no_traits:
            for i in range(1, 3):
                trait = CharacterTrait(
                    category_name="PHYSICAL",
                    character=str(character.id),
                    name=fake.word(),
                    value=i,
                    max_value=5,
                )
                await trait.insert()
                character.traits.append(trait)

            await character.save()

        if add_to_user:
            user.characters.append(character)
            await user.save()

        return character

    return make


@pytest.fixture()
def create_campaign():
    """Factory to create a campaign object in the database."""

    async def make(
        name: str = fake.name(),
        guild: int = randint(1, 9999999999),
        description: str = fake.sentence(nb_words=10),
    ) -> Campaign:
        campaign = Campaign(
            name=name,
            guild=guild,
            description=description,
        )
        await campaign.insert()
        return campaign

    # TODO: chapters: list[CampaignChapter] = Field(default_factory=list)
    # TODO: notes: list[CampaignNote] = Field(default_factory=list)
    # TODO: npcs: list[CampaignNPC] = Field(default_factory=list)

    return make


@pytest.fixture()
def create_user():
    """Factory to create a user object in the database."""

    async def make(
        new: bool = False,
        name: str = fake.name(),
        id: int = randint(1, 9999999999),
        guilds: list[int] = [randint(1, 9999999999)],
    ) -> User:
        """Create a user object in the test database.

        Args:
            new (bool, optional): If true, create's a new user with only a name and id and guild. Defaults to False.
            name (str, optional): The name of the user. Defaults to fake.name().
            id (int, optional): The id of the user. Defaults to randint(1, 9999999999).
            guilds (list[int], optional): The guilds the user is a member of. Defaults to [randint(1, 9999999999)].

        """
        if new:
            user = User(
                name=name,
                id=id,
                guilds=guilds,
            )
            await user.insert()
            return user

        user = User(
            name=name,
            id=id,
            guilds=guilds,
        )

        user.campaign_experience["1"] = CampaignExperience(
            xp_current=10, xp_total=10, cool_points=0
        )

        # TODO: Add macros
        # TODO: Add characters

        await user.insert()
        return user

    return make


### Mock discord.py objects ###
@pytest.fixture()
def mock_member(mocker):
    """A mock of a discord.Member object."""
    mock_role_one = mocker.MagicMock()
    mock_role_one.id = 1
    mock_role_one.name = "@everyone"

    mock_role_two = mocker.MagicMock()
    mock_role_two.id = 2
    mock_role_two.name = "Player"

    mock_member = mocker.MagicMock()
    mock_member.id = 1
    mock_member.display_name = "Test User"
    mock_member.name = "testuser"
    mock_member.mention = "<@1>"
    mock_member.nick = "Testy"
    mock_member.__class__ = discord.Member
    mock_member.roles = [mock_role_one, mock_role_two]

    return mock_member


@pytest.fixture()
def mock_member2(mocker):
    """A mock of a discord.Member object."""
    mock_role_one = mocker.MagicMock()
    mock_role_one.id = 1
    mock_role_one.name = "@everyone"

    mock_role_two = mocker.MagicMock()
    mock_role_two.id = 2
    mock_role_two.name = "Player"

    mock_guild = mocker.MagicMock()
    mock_guild.id = 200
    mock_guild.__class__ = discord.Guild

    mock_member = mocker.MagicMock()
    mock_member.id = 2
    mock_member.display_name = "Test User2"
    mock_member.name = "testuser2"
    mock_member.mention = "<@2>"
    mock_member.nick = "Testy2"
    mock_member.guild = mock_guild
    mock_member.__class__ = discord.Member
    mock_member.roles = [mock_role_one, mock_role_two]

    return mock_member


@pytest.fixture()
def mock_guild1(mocker):
    """A mock of a discord.Guild object."""
    # Mock the ctx.guild object matches the mock database
    mock_guild = mocker.MagicMock()
    mock_guild.id = 1
    mock_guild.name = "Test Guild"
    mock_guild.data = {"key": "value"}
    mock_guild.__class__ = discord.Guild

    return mock_guild


@pytest.fixture()
def mock_guild2(mocker):
    """A mock of a discord.Guild object."""
    # Mock the ctx.guild object matches the mock database
    mock_guild = mocker.MagicMock()
    mock_guild.id = 2
    mock_guild.name = "Test Guild2"
    mock_guild.data = {"key": "value"}
    mock_guild.__class__ = discord.Guild

    return mock_guild


@pytest.fixture()
def mock_ctx(mocker, mock_member, mock_guild1):
    """Create a mock context object with user 1."""
    # Mock the ctx.bot object
    mock_bot = mocker.MagicMock()
    mock_bot.user_svc.update_or_add = MagicMock(return_value=mock_member)
    mock_bot.__class__ = commands.Bot

    # Mock the ctx object
    mock_ctx = mocker.MagicMock()
    mock_ctx.author = mock_member
    mock_ctx.bot = mock_bot
    mock_ctx.guild = mock_guild1
    mock_ctx.__class__ = discord.ApplicationContext

    return mock_ctx
