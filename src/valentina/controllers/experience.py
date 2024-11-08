"""Controllers for experience."""

from valentina.models import Campaign, User


async def total_campaign_experience(campaign: Campaign) -> tuple[int, int, int]:
    """Return the total experience for the campaign."""
    user_id_list = {character.user_owner for character in await campaign.fetch_player_characters()}
    available_xp = 0
    total_xp = 0
    cool_points = 0

    for user_id in user_id_list:
        user = await User.get(int(user_id))
        user_available_xp, user_total_xp, user_cool_points = user.fetch_campaign_xp(campaign)

        available_xp += user_available_xp
        total_xp += user_total_xp
        cool_points += user_cool_points

    return available_xp, total_xp, cool_points
