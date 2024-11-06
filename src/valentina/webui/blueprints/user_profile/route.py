"""Route for the user profile."""

from dataclasses import dataclass
from typing import ClassVar

import arrow
from flask_discord import requires_authorization
from quart import abort, request, session
from quart.views import MethodView

from valentina.constants import Emoji
from valentina.discord.utils import get_user_from_id
from valentina.models import Character, Statistics, User
from valentina.webui import catalog
from valentina.webui.constants import TableType
from valentina.webui.utils import fetch_guild


class UserProfile(MethodView):
    """Route for the user profile."""

    decorators: ClassVar = [requires_authorization]

    async def get(self, user_id: int) -> str:
        """Get the user profile.

        Args:
            user_id: The ID of the user to get the profile for.
        """
        from valentina.bot import bot

        user = await User.get(user_id)
        if not user:
            abort(404)

        characters = await Character.find(
            Character.user_owner == user_id, Character.guild == int(session["GUILD_ID"])
        ).to_list()

        discord_guild = await bot.get_guild_from_id(session["GUILD_ID"])
        discord_member = get_user_from_id(discord_guild, user_id)

        stats_engine = Statistics(guild_id=session["GUILD_ID"])
        statistics = await stats_engine.user_statistics(user, as_json=True)

        roles = [
            f"@{r.name}" if not r.name.startswith("@") else r.name
            for r in discord_member.roles[::-1][:-1]
            if not r.is_integration()
        ] or ["No roles"]
        created_at = f"{arrow.get(discord_member.created_at).humanize()}"
        joined_at = (
            f"{arrow.get(discord_member.joined_at).humanize()}" if discord_member.joined_at else ""
        )

        guild = await fetch_guild(fetch_links=True)

        @dataclass
        class UserCampaignExperience:
            """Experience for a user in a campaign."""

            name: str
            xp: int
            total_xp: int
            cp: int

        campaign_experience = []
        for campaign in guild.campaigns:
            campaign_xp, campaign_total_xp, campaign_cp = user.fetch_campaign_xp(campaign)
            campaign_experience.append(
                UserCampaignExperience(campaign.name, campaign_xp, campaign_total_xp, campaign_cp)  # type: ignore [attr-defined]
            )

        return catalog.render(
            "user_profile.UserProfile",
            user=user,
            discord_member=discord_member,
            discord_guild=discord_guild,
            characters=characters,
            statistics=statistics,
            roles=roles,
            created_at=created_at,
            joined_at=joined_at,
            campaign_experience=campaign_experience,
            emoji=Emoji,
            table_type_macro=TableType.MACRO,
            error_msg=request.args.get("error_msg", ""),
            success_msg=request.args.get("success_msg", ""),
            info_msg=request.args.get("info_msg", ""),
            warning_msg=request.args.get("warning_msg", ""),
        )
