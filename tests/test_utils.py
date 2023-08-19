# type: ignore
"""Tests for helper utilities."""
import discord
import pytest
from dirty_equals import IsStr

from valentina.models.db_tables import RollProbability
from valentina.utils.probability import Probability


@pytest.mark.usefixtures("mock_db")
class TestProbability:
    """Test the probability helper."""

    def test_calculate(self, mock_ctx):
        """Test the calculate method."""
        # GIVEN an empty RollProbability table
        for i in RollProbability.select():
            i.delete_instance()

        # WHEN calculating the probability of a roll
        pool = 5
        difficulty = 6
        instance = Probability(mock_ctx, pool=pool, difficulty=difficulty, dice_size=10)

        # THEN confirm the probability is correct and the result is saved to the database
        assert instance.probabilities == RollProbability.get_by_id(1).data

        # WHEN calculating the probability of a roll that has already been calculated
        instance = Probability(mock_ctx, pool=pool, difficulty=difficulty, dice_size=10)

        # THEN confirm the result is retrieved from the database
        assert instance.probabilities == RollProbability.get_by_id(1).data
        assert RollProbability.select().count() == 1

    @pytest.mark.asyncio()
    async def test_get_embed(self, mock_ctx):
        """Test the get_embed method."""
        # GIVEN a probability instance
        pool = 5
        difficulty = 6
        instance = Probability(mock_ctx, pool=pool, difficulty=difficulty, dice_size=10)

        # WHEN getting the embed
        embed = await instance.get_embed()

        # THEN confirm the embed is correct
        assert isinstance(embed, discord.Embed)
        result = embed.to_dict()
        from rich import print

        assert result["footer"]["text"] == IsStr(regex=r"Based on [0-9,]+ trials")
        assert result["description"] == IsStr()
        assert isinstance(result["fields"], list)
