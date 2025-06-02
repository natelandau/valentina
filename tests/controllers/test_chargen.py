# type: ignore
"""Test the chargen module."""

from unittest.mock import AsyncMock

import pytest

from tests.conftest import GUILD_ID
from tests.factories import *
from valentina.constants import (
    CharacterConcept,
    CharClass,
    HunterCreed,
    RNGCharLevel,
    TraitCategory,
    VampireClan,
    WerewolfAuspice,
    WerewolfBreed,
    WerewolfTribe,
)
from valentina.controllers import RNGCharGen
from valentina.models import Character, CharacterTrait


@pytest.mark.drop_db
@pytest.mark.parametrize(
    ("char_class"),
    [(None), (CharClass.VAMPIRE), (CharClass.HUNTER), (CharClass.WEREWOLF)],
)
async def test_generate_full_character(
    user_factory,
    campaign_factory,
    mock_ctx1,
    mocker,
    char_class,
):
    """Test the generate_full_character method."""
    # MOCK the call the fetch_random_name
    async_mock = AsyncMock(return_value=("mock_first", "mock_last"))
    mocker.patch("valentina.controllers.rng_chargen.fetch_random_name", side_effect=async_mock)

    # GIVEN a user, campaign, and a character generator
    user = user_factory.build(characters=[])
    await user.insert()

    campaign = campaign_factory.build()
    await campaign.insert()

    char_gen = RNGCharGen(
        guild_id=mock_ctx1.guild.id,
        user=user,
        experience_level=RNGCharLevel.NEW,
        campaign=campaign,
    )

    # WHEN generate_full_character is called
    character = await char_gen.generate_full_character(
        char_class=char_class,
        storyteller_character=True,
        player_character=False,
    )

    # THEN check that the character is created correctly
    assert character.guild == GUILD_ID
    assert character.name_first == "mock_first"
    assert character.name_last == "mock_last"
    assert character.type_storyteller is True
    assert character.concept_name in CharacterConcept.__members__
    assert character.char_class_name in CharClass.__members__

    if character.char_class_name == CharClass.VAMPIRE.name:
        assert character.clan_name in VampireClan.__members__

    if character.char_class_name == CharClass.HUNTER.name:
        assert character.creed_name in HunterCreed.__members__
        assert (
            await CharacterTrait.find(
                CharacterTrait.character == str(character.id),
                CharacterTrait.name == "Conviction",
            ).count()
            == 1
        )
        assert (
            await CharacterTrait.find(
                CharacterTrait.character == str(character.id),
                CharacterTrait.name == "Willpower",
            ).count()
            == 1
        )

    if character.char_class_name == CharClass.WEREWOLF.name:
        assert character.tribe in WerewolfTribe.__members__
        assert character.auspice in WerewolfAuspice.__members__
        assert character.breed in WerewolfBreed.__members__
        for trait in ("Rage", "Gnosis", "Willpower", "Rank", "Glory", "Honor", "Wisdom"):
            assert (
                await CharacterTrait.find(
                    CharacterTrait.character == str(character.id),
                    CharacterTrait.name == trait,
                ).count()
                == 1
            )

    assert await Character.get(character.id, fetch_links=True) == character


@pytest.mark.parametrize(
    ("primary_values", "non_primary_values"),
    [
        ([1, 2, 5], [1, 1, 5, 4, 1, 1]),
        ([2, 2, 2], [2, 2, 2, 2, 2, 2]),
        ([3, 3, 3], [1, 3, 2, 3, 4, 3]),
        ([2, 2, 2], [1, 1, 1, 1, 1, 1]),
        ([5, 5, 4], [1, 0, 0, 0, 0, 0]),
    ],
)
def test__redistribute_trait_values(primary_values, non_primary_values):
    """Test the _redistribute_trait_values method."""
    # Given a number of traits
    # We use BERSERKER b/c it doesn't matter which concept we use
    primary_traits = [
        CharacterTrait(
            name=CharacterConcept.BERSERKER.value.specific_abilities[i],
            value=primary_values[i],
            category_name="test",
            character="1",
            max_value=5,
        )
        for i in range(len(primary_values))
    ]
    non_primary_traits = [
        CharacterTrait(
            name=f"junk_{i}",
            value=non_primary_values[i],
            category_name="test",
            character="1",
            max_value=5,
        )
        for i in range(len(non_primary_values))
    ]

    # WHEN _redistribute_trait_values is called
    results = RNGCharGen._redistribute_trait_values(
        primary_traits + non_primary_traits,
        CharacterConcept.BERSERKER,
    )

    # THEN ensure the traits are redistributed correctly
    assert len(results) == len(primary_traits) + len(non_primary_traits)

    for x in results:
        assert 0 <= x.value <= 5
        if x.name in CharacterConcept.BERSERKER.value.specific_abilities:
            assert 3 <= x.value <= 5


@pytest.mark.parametrize(
    ("char_class", "concept", "clan", "creed", "nick_is_class"),
    [
        (None, None, None, None, None),
        (CharClass.VAMPIRE, None, None, None, True),
        (CharClass.VAMPIRE, None, VampireClan.BRUJAH, None, True),
        (CharClass.HUNTER, None, None, None, True),
    ],
)
async def test_rngchargen_generate_base_character(
    user_factory,
    mock_ctx1,
    char_class,
    concept,
    clan,
    creed,
    nick_is_class,
    mocker,
):
    """Test the generate_base_character method."""
    # MOCK the call the fetch_random_name
    async_mock = AsyncMock(return_value=("mock_first", "mock_last"))
    mocker.patch("valentina.controllers.rng_chargen.fetch_random_name", side_effect=async_mock)

    # GIVEN a user and a character generator

    user = user_factory.build()
    char_gen = RNGCharGen(guild_id=mock_ctx1.guild.id, user=user)

    # WHEN generate_base is called
    character = await char_gen.generate_base_character(
        char_class=char_class,
        concept=concept,
        clan=clan,
        creed=creed,
        nickname_is_class=nick_is_class if nick_is_class is not None else False,
    )

    # THEN check that the character is created correctly
    assert character.guild == GUILD_ID
    assert character.name_first == "mock_first"
    assert character.name_last == "mock_last"
    assert character.concept_name in CharacterConcept.__members__
    assert character.char_class_name in CharClass.__members__

    if CharClass[character.char_class_name] == CharClass.VAMPIRE:
        if not clan:
            assert character.clan_name in VampireClan.__members__
        if clan:
            assert character.clan_name == clan.name
    else:
        assert character.clan_name is None

    if nick_is_class:
        assert character.name_nick == CharClass[character.char_class_name].value.name
    else:
        assert character.name_nick is None

    if CharClass[character.char_class_name] == CharClass.HUNTER:
        if not creed:
            assert character.creed_name in HunterCreed.__members__
    else:
        assert character.creed_name is None


@pytest.mark.parametrize(
    ("char_class", "concept", "level", "primary_dots", "non_primary_dots"),
    [
        (
            CharClass.MORTAL,
            CharacterConcept.PERFORMER,
            RNGCharLevel.NEW,
            9,
            14,
        ),
        (
            CharClass.VAMPIRE,
            CharacterConcept.BUSINESSMAN,
            RNGCharLevel.INTERMEDIATE,
            11,
            14,
        ),
        (
            CharClass.MORTAL,
            CharacterConcept.URBAN_TRACKER,
            RNGCharLevel.ADVANCED,
            11,
            15,
        ),
        (
            CharClass.WEREWOLF,
            CharacterConcept.SOLDIER,
            RNGCharLevel.ELITE,
            13,
            17,
        ),
    ],
)
async def test_random_attributes(
    user_factory,
    mock_ctx1,
    char_class,
    concept,
    level,
    primary_dots,
    non_primary_dots,
    mocker,
):
    """Test the random_abilities method."""
    # MOCK the call the fetch_random_name
    async_mock = AsyncMock(return_value=("mock_first", "mock_last"))
    mocker.patch("valentina.controllers.rng_chargen.fetch_random_name", side_effect=async_mock)

    # GIVEN a character and a character generator
    user = user_factory.build()
    char_gen = RNGCharGen(guild_id=mock_ctx1.guild.id, user=user, experience_level=level)
    character = await char_gen.generate_base_character(char_class=char_class, concept=concept)

    # WHEN random_abilities is called with a character
    await char_gen.random_attributes(character)

    # THEN check that the character has attributes
    assert len(character.traits) == 9

    for trait in character.traits:
        assert trait.value != 0
        assert trait.value <= 5

    assert sum([trait.value for trait in character.traits][:3]) == primary_dots
    assert sum([trait.value for trait in character.traits][-6:]) == non_primary_dots


@pytest.mark.parametrize(
    (
        "char_class",
        "concept",
        "level",
        "primary_dots",
        "non_primary_dots",
    ),
    [
        (
            CharClass.WEREWOLF,
            CharacterConcept.SOLDIER,
            RNGCharLevel.NEW,
            13,
            14,
        ),
        (
            CharClass.MORTAL,
            CharacterConcept.SHAMAN,
            RNGCharLevel.INTERMEDIATE,
            18,
            18,
        ),
        (
            CharClass.GHOUL,
            CharacterConcept.CRUSADER,
            RNGCharLevel.ADVANCED,
            23,
            23,
        ),
        (
            CharClass.VAMPIRE,
            CharacterConcept.UNDER_WORLDER,
            RNGCharLevel.ELITE,
            28,
            28,
        ),
    ],
)
async def test_random_abilities(
    user_factory,
    mock_ctx1,
    char_class,
    concept,
    level,
    primary_dots,
    non_primary_dots,
    mocker,
):
    """Test the random_abilities method."""
    # MOCK the call the fetch_random_name
    async_mock = AsyncMock(return_value=("mock_first", "mock_last"))
    mocker.patch("valentina.controllers.rng_chargen.fetch_random_name", side_effect=async_mock)

    # GIVEN a character and a character generator
    user = user_factory.build()
    char_gen = RNGCharGen(guild_id=mock_ctx1.guild.id, user=user, experience_level=level)
    character = await char_gen.generate_base_character(char_class=char_class, concept=concept)

    # WHEN random_abilities is called with a character
    results = await char_gen.random_abilities(character)

    # THEN check that the character has abilities
    for trait in results.traits:
        assert 0 <= trait.value <= 5

    assert (
        sum(
            [
                x.value
                for x in results.traits
                if x.category_name == concept.value.ability_specialty.name
            ],
        )
        == primary_dots
    )

    assert (
        sum(
            [
                x.value
                for x in results.traits
                if x.category_name != concept.value.ability_specialty.name
            ],
        )
        == non_primary_dots
    )


@pytest.mark.parametrize(
    ("char_class", "clan", "level", "num_disciplines"),
    [
        (CharClass.VAMPIRE, VampireClan.BRUJAH, RNGCharLevel.NEW, 3),
        (CharClass.MORTAL, None, RNGCharLevel.NEW, 0),
        (CharClass.VAMPIRE, VampireClan.GIOVANNI, RNGCharLevel.INTERMEDIATE, 4),
        (CharClass.VAMPIRE, VampireClan.MALKAVIAN, RNGCharLevel.ADVANCED, 5),
        (CharClass.VAMPIRE, VampireClan.VENTRUE, RNGCharLevel.ELITE, 6),
    ],
)
async def test_random_disciplines(
    user_factory,
    mock_ctx1,
    char_class,
    clan,
    level,
    num_disciplines,
    mocker,
):
    """Test the random_disciplines method."""
    # MOCK the call the fetch_random_name
    async_mock = AsyncMock(return_value=("mock_first", "mock_last"))
    mocker.patch("valentina.controllers.rng_chargen.fetch_random_name", side_effect=async_mock)

    # GIVEN a character and a character generator
    user = user_factory.build()
    char_gen = RNGCharGen(guild_id=mock_ctx1.guild.id, user=user, experience_level=level)
    character = await char_gen.generate_base_character(char_class=char_class, clan=clan)

    # WHEN random_disciplines is called with a character
    result = await char_gen.random_disciplines(character)

    # THEN check disciplines are set correctly
    disciplines = [x for x in result.traits if x.category_name == "DISCIPLINES"]
    assert len(disciplines) == num_disciplines

    if character.clan_name:
        for vc in VampireClan[character.clan_name].value.disciplines:
            assert vc in [x.name for x in disciplines]

    for d in disciplines:
        assert 0 <= d.value <= 5


@pytest.mark.parametrize(
    ("char_class", "level", "modifier"),
    [
        (CharClass.WEREWOLF, RNGCharLevel.NEW, 0),
        (CharClass.MORTAL, RNGCharLevel.NEW, 0),
        (CharClass.VAMPIRE, RNGCharLevel.INTERMEDIATE, 0),
        (CharClass.HUNTER, RNGCharLevel.ADVANCED, 1),
        (CharClass.VAMPIRE, RNGCharLevel.ELITE, 2),
    ],
)
async def test_random_virtues(user_factory, mock_ctx1, char_class, level, modifier, mocker):
    """Test the andom_virtues method."""
    # MOCK the call the fetch_random_name
    async_mock = AsyncMock(return_value=("mock_first", "mock_last"))
    mocker.patch("valentina.controllers.rng_chargen.fetch_random_name", side_effect=async_mock)

    # GIVEN a character and a character generator
    user = user_factory.build()
    char_gen = RNGCharGen(guild_id=mock_ctx1.guild.id, user=user, experience_level=level)
    character = await char_gen.generate_base_character(char_class=char_class)

    # WHEN random_virtues is called with a character
    result = await char_gen.random_virtues(character)

    # THEN check virtues are set correctly
    virtues_names = TraitCategory.VIRTUES.get_all_class_trait_names(char_class)
    virtues = result.traits
    assert len(virtues) == len(virtues_names)

    for v in virtues:
        assert 1 <= v.value <= 5
        assert v.name in virtues_names

    if virtues:
        assert sum([x.value for x in virtues]) == 7 + modifier


@pytest.mark.parametrize(
    ("char_class", "concept", "section_titles", "trait_names"),
    [
        (CharClass.MORTAL, CharacterConcept.BERSERKER, ["Frenzy"], ["Potence"]),
        (CharClass.WEREWOLF, CharacterConcept.BERSERKER, ["n/a"], ["n/a"]),
        (CharClass.MORTAL, CharacterConcept.PERFORMER, ["Fast Talk"], []),
        (CharClass.MORTAL, CharacterConcept.HEALER, ["Heal", "True Faith"], []),
    ],
)
async def test_concept_special_abilities(
    user_factory,
    mock_ctx1,
    char_class,
    concept,
    section_titles,
    trait_names,
    mocker,
):
    """Test the concept_special_abilities method."""
    # MOCK the call the fetch_random_name
    async_mock = AsyncMock(return_value=("mock_first", "mock_last"))
    mocker.patch("valentina.controllers.rng_chargen.fetch_random_name", side_effect=async_mock)

    # GIVEN a character and a character generator
    user = user_factory.build()
    char_gen = RNGCharGen(guild_id=mock_ctx1.guild.id, user=user)
    character = await char_gen.generate_base_character(char_class=char_class, concept=concept)

    # WHEN concept_special_abilities is called with a character
    result = await char_gen.concept_special_abilities(character)

    # THEN check that the character has abilities
    if char_class == CharClass.MORTAL:
        for trait_name in trait_names:
            assert any(x.name == trait_name for x in result.traits)

        if not trait_names:
            assert not result.traits

        for section_title in section_titles:
            assert any(x.title == section_title for x in result.sheet_sections)

        if not section_titles:
            assert not result.sheet_sections

    else:
        assert not result.traits
        assert not result.sheet_sections
