"""Route for the user profile."""

from dataclasses import dataclass
from typing import ClassVar, assert_never
from uuid import UUID

import arrow
from flask_discord import requires_authorization
from quart import abort, request, session, url_for
from quart.views import MethodView
from quart_wtf import QuartForm
from wtforms import HiddenField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length

from valentina.constants import TraitCategory
from valentina.discord.utils import get_user_from_id
from valentina.models import Character, Statistics, User, UserMacro
from valentina.webui import catalog
from valentina.webui.constants import UserEditableInfo
from valentina.webui.utils import fetch_guild
from valentina.webui.utils.discord import post_to_audit_log


class UserMacroForm(QuartForm):
    """Form for a user macro."""

    name = StringField(
        default="",
        validators=[DataRequired(), Length(min=3, message="Must be at least 3 characters")],
    )
    abbreviation = StringField(
        default="",
        description="4 characters or less",
        validators=[DataRequired(), Length(max=4, message="Must be 4 characters or less")],
    )
    description = TextAreaField(description="Markdown is supported")

    trait_one = SelectField(
        "Trait One",
        choices=[("", "-- Select --")] + [(t, t) for t in TraitCategory.get_all_trait_names()],
        validators=[DataRequired()],
    )

    trait_two = SelectField(
        "Trait Two",
        choices=[("", "-- Select --")] + [(t, t) for t in TraitCategory.get_all_trait_names()],
        validators=[DataRequired()],
    )

    uuid = HiddenField()
    user_id = HiddenField()
    submit = SubmitField("Submit")
    cancel = SubmitField("Cancel")


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
            characters=characters,
            statistics=statistics,
            roles=roles,
            created_at=created_at,
            joined_at=joined_at,
            campaign_experience=campaign_experience,
            UserEditableInfo=UserEditableInfo,
            error_msg=request.args.get("error_msg", ""),
            success_msg=request.args.get("success_msg", ""),
            info_msg=request.args.get("info_msg", ""),
            warning_msg=request.args.get("warning_msg", ""),
        )


class UserEditItem(MethodView):
    """Route for the user edit item."""

    decorators: ClassVar = [requires_authorization]

    def __init__(self, edit_type: UserEditableInfo) -> None:
        self.edit_type = edit_type

    async def _build_form(self, user: User) -> QuartForm:
        """Build the form for the user item."""
        data = {}

        match self.edit_type:
            case UserEditableInfo.MACRO:
                if request.args.get("macro_id"):
                    for macro in user.macros:
                        if macro.uuid == UUID(request.args.get("macro_id")):
                            data["name"] = macro.name
                            data["abbreviation"] = macro.abbreviation
                            data["description"] = macro.description
                            data["trait_one"] = macro.trait_one
                            data["trait_two"] = macro.trait_two
                            data["uuid"] = str(macro.uuid)
                            data["user_id"] = str(user.id)
                            break
                return await UserMacroForm().create_form(data=data)

            case _:
                assert_never(self.edit_type)

    async def _post_macro(self, user: User, form: QuartForm) -> tuple[bool, str, QuartForm]:
        """Post the macro."""
        if await form.validate_on_submit():
            if form.data.get("uuid"):
                for macro in user.macros:
                    if macro.uuid == UUID(form.data["uuid"]):
                        macro.name = form.data["name"]
                        macro.abbreviation = form.data["abbreviation"]
                        macro.description = form.data["description"]
                        macro.trait_one = form.data["trait_one"]
                        macro.trait_two = form.data["trait_two"]
                        break
                msg = "Macro Updated"
            else:
                new_macro = UserMacro(
                    name=form.data["name"],
                    abbreviation=form.data["abbreviation"],
                    description=form.data["description"],
                    trait_one=form.data["trait_one"],
                    trait_two=form.data["trait_two"],
                )
                user.macros.append(new_macro)

                msg = "Macro Added"

            await user.save()
            await post_to_audit_log(
                msg=f"{msg} by {user.name}",
                view=self.__class__.__name__,
            )

            return True, msg, None

        return False, "", form

    async def get(self, user_id: int) -> str:
        """Get the user edit item."""
        user = await User.get(user_id)
        form = await self._build_form(user)

        return catalog.render(
            "user_profile.FormPartial",
            form=form,
            post_url=url_for(self.edit_type.value.route, user_id=user_id),
            hx_target=f"#{self.edit_type.value.div_id}",
            join_label=False,
            floating_label=True,
        )

    async def post(self, user_id: int) -> str:
        """Post the user edit item."""
        user = await User.get(user_id)
        form = await self._build_form(user)

        if form.data.get("cancel"):
            return f'<script>window.location.href="{url_for("user_profile.view", user_id=user_id)}"</script>'

        match self.edit_type:
            case UserEditableInfo.MACRO:
                form_is_processed, msg, form = await self._post_macro(user=user, form=form)
            case _:
                assert_never(self.edit_type)

        if form_is_processed:
            return f'<script>window.location.href="{url_for("user_profile.view", user_id=user_id, success_msg=msg)}"</script>'

        return catalog.render(
            "user_profile.FormPartial",
            form=form,
            post_url=url_for(self.edit_type.value.route, user_id=user_id),
            hx_target=f"#{self.edit_type.value.div_id}",
            join_label=False,
            floating_label=True,
        )

    async def delete(self, user_id: int) -> str:
        """Delete the macro."""
        user = await User.get(user_id)

        match self.edit_type:
            case UserEditableInfo.MACRO:
                user.macros = [
                    macro
                    for macro in user.macros
                    if str(macro.uuid) != request.args.get("macro_id")
                ]
                await user.save()
                await post_to_audit_log(
                    msg=f"Macro Deleted by {user.name}",
                    view=self.__class__.__name__,
                )
                msg = "Macro Deleted"

            case _:
                assert_never(self.edit_type)

        return f'<script>window.location.href="{url_for("user_profile.view", user_id=user_id, success_msg=msg)}"</script>'
