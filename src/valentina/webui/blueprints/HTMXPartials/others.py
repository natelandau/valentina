"""Assorted forms using HTMXPartials."""

from quart import abort, url_for
from quart.utils import run_sync
from quart.views import MethodView

from valentina.constants import HTTPStatus
from valentina.models import Campaign
from valentina.webui import catalog
from valentina.webui.utils.discord import post_to_audit_log

from .forms import DesperationForm


class SetDesperationOrDanger(MethodView):
    """Edit the setting for desperation or danger."""

    async def get(self, campaign_id: str) -> str:
        """Render form for modifying campaign desperation and danger levels.

        Args:
            campaign_id (str): Unique identifier for the campaign to modify

        Returns:
            str: HTML partial containing the desperation/danger form

        Raises:
            HTTPException: If campaign_id is invalid or campaign not found
        """
        campaign = await Campaign.get(campaign_id)
        if not campaign:
            abort(HTTPStatus.NOT_FOUND.value, f"Campaign {campaign_id} not found")

        form = await DesperationForm.create_form(
            data={"desperation": campaign.desperation, "danger": campaign.danger}
        )

        return await run_sync(
            lambda: catalog.render(
                "HTMXPartials.Other.DesperationForm",
                form=form,
                campaign_id=campaign_id,
            )
        )()

    async def post(self, campaign_id: str) -> str:
        """Process form submission to update campaign desperation and danger levels.

        Args:
            campaign_id (str): Unique identifier for the campaign to update

        Returns:
            str: HTML script tag for redirecting to campaign view on success, or rendered form with validation errors

        Raises:
            HTTPException: If campaign_id is invalid or campaign not found
        """
        campaign = await Campaign.get(campaign_id)
        form = await DesperationForm.create_form(
            data={"desperation": campaign.desperation, "danger": campaign.danger}
        )
        msg = ""

        if await form.validate_on_submit():
            if form.data["submit"] and (
                int(form.desperation.data) != campaign.desperation
                or int(form.danger.data) != campaign.danger
            ):
                msg = "Updated Desperation and Danger"
                campaign.desperation = int(form.desperation.data)
                campaign.danger = int(form.danger.data)
                await campaign.save()
                await post_to_audit_log(
                    f"Campaign {campaign_id} desperation or danger set to {form.desperation.data} and {form.danger.data}"
                )

            return f'<script>window.location.href="{url_for("campaign.view", campaign_id=campaign_id, success_msg=f"{msg}")}"</script>'

        return await run_sync(
            lambda: catalog.render(
                "HTMXPartials.Other.DesperationForm",
                form=form,
                campaign_id=campaign_id,
            )
        )()
