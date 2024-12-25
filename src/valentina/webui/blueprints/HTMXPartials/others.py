"""Assorted forms using HTMXPartials."""

from dataclasses import dataclass

from quart import abort, request, session, url_for
from quart.utils import run_sync
from quart.views import MethodView
from werkzeug.utils import secure_filename

from valentina.constants import HTTPStatus
from valentina.controllers import PermissionManager
from valentina.models import AWSService, Campaign, Character, User
from valentina.utils import random_string
from valentina.webui import catalog
from valentina.webui.utils import fetch_active_campaign, fetch_guild
from valentina.webui.utils.discord import post_to_audit_log

from .forms import AddExperienceForm, CharacterImageUploadForm, DesperationForm


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
            # Only update and log if values actually changed to avoid unnecessary DB writes
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

            # Use client-side redirect to ensure proper page reload with success message
            return f'<script>window.location.href="{url_for("campaign.view", campaign_id=campaign_id, success_msg=f"{msg}")}"</script>'

        # Run template rendering in sync context since Jinja is not async-safe
        return await run_sync(
            lambda: catalog.render(
                "HTMXPartials.Other.DesperationForm",
                form=form,
                campaign_id=campaign_id,
            )
        )()


class CharacterImageView(MethodView):
    """Handle adding experience to a user."""

    def __init__(self) -> None:
        self.aws_svc = AWSService()

    async def _get_character_object(self, character_id: str) -> Character:
        """Fetch and validate a character object from the database.

        Retrieve a character by ID and ensure it exists. This helper method centralizes character
        lookup logic and error handling for the CharacterImageView class. Use this method when
        you need to safely fetch a character before performing image-related operations.

        Args:
            character_id (str): Unique identifier for the character to fetch from database

        Returns:
            Character: Fully populated character object with all linked relationships

        Raises:
            ValueError: If character_id format is invalid (e.g. not a valid ObjectId)
            HTTPException: If character not found in database, aborts with 400 Bad Request

        Example:
            character = await self._get_character_object("507f1f77bcf86cd799439011")
        """
        try:
            character = await Character.get(character_id, fetch_links=True)
        except ValueError:
            abort(HTTPStatus.BAD_REQUEST.value)

        if not character:
            abort(HTTPStatus.BAD_REQUEST.value)

        return character

    async def get(self, character_id: str, success_msg: str = "") -> str:
        """Render an HTML partial containing a character's image gallery.

        Fetch a character's images from the database and generate signed URLs for each one.
        Use this endpoint to display all images associated with a character in a responsive
        gallery format. The gallery includes edit controls if the current user has appropriate
        permissions.

        Args:
            character_id (str): Unique identifier for the character to display images for
            success_msg (str, optional): Message to show in success toast notification.
                Defaults to empty string.

        Returns:
            str: Rendered HTML partial containing the character's image gallery with
                signed AWS URLs and edit controls if permitted

        Raises:
            HTTPException: If character_id format is invalid or character not found (400)

        Example:
            html = await character_image_view.get("507f1f77bcf86cd799439011")
        """
        character = await self._get_character_object(character_id)
        images = [self.aws_svc.get_url(x) for x in character.images]
        can_edit = session["IS_STORYTELLER"] or session["USER_ID"] == character.user_owner

        return catalog.render(
            "HTMXPartials.CharacterImages.ImagesDisplay",
            character=character,
            images=images,
            can_edit=can_edit,
            success_msg=success_msg,
        )

    async def post(self, character_id: str) -> str:
        """Add an image to a character.

        Process uploaded image file and attach it to the specified character. Validate form data
        and handle cancellation. Return updated character images view.

        Args:
            character_id (str): ID of the character to add image to

        Returns:
            str: HTML partial containing either the upload form (on validation failure)
                 or updated character images (on success)
        """
        form = await CharacterImageUploadForm().create_form()

        if await form.validate_on_submit():
            if form.data["cancel"] or not form.image.data:
                return await self.get(character_id)

            image = form.image.data
            filename = secure_filename(image.filename)
            extension = filename.split(".")[-1].lower()
            character = await self._get_character_object(character_id)
            await character.add_image(extension=extension, data=image.stream.read())

            await post_to_audit_log(
                msg=f"Add image to `{character.name}`", view=self.__class__.__name__
            )

            return await self.get(character_id, success_msg="Image added")

        return catalog.render(
            "HTMXPartials.CharacterImages.ImageUploadForm",
            form=form,
            character_id=character_id,
        )

    async def delete(self, character_id: str) -> str:
        """Delete an image from a character and return updated image list.

        Delete the specified image from a character's image collection and return an HTML partial
        showing the remaining images.

        Args:
            character_id (str): ID of the character to modify
            url (str): URL of the image to remove, passed as query parameter

        Returns:
            str: HTML partial containing the character's remaining images after deletion

        Raises:
            NotFound: If character_id is invalid
            Forbidden: If user lacks permission to modify character
        """
        character = await self._get_character_object(character_id)
        key_prefix = f"{session['GUILD_ID']}/characters/{character.id}"
        image_name = request.args.get("url").split("/")[-1]

        image_key = f"{key_prefix}/{image_name}"
        await character.delete_image(image_key)

        await post_to_audit_log(
            msg=f"Delete image from `{character.name}`", view=self.__class__.__name__
        )

        return await self.get(character_id, success_msg="Image deleted")


class AddExperienceView(MethodView):
    """Handle adding experience to a user."""

    def __init__(self) -> None:
        self.permission_manager = PermissionManager(guild_id=session["GUILD_ID"])

    def _build_success_message(self, experience: int, cool_points: int, target_name: str) -> str:
        """Build success message for experience/cool points addition.

        Build a formatted message string indicating the experience and/or cool points
        added to a target user.

        Args:
            experience (int): Amount of experience points (XP) added
            cool_points (int): Amount of cool points (CP) added
            target_name (str): Name of the target user receiving the points

        Returns:
            str: Formatted message string describing points added to target user
        """
        xp_msg = f"{experience} XP" if experience > 0 else ""
        cp_msg = f"{cool_points} CP" if cool_points > 0 else ""

        if xp_msg and cp_msg:
            return f"Add {xp_msg} and {cp_msg} to {target_name}"

        if xp_msg:
            return f"Add {xp_msg} to {target_name}"

        return f"Add {cp_msg} to {target_name}"

    async def get(self, target_id: int, success_msg: str = "") -> str:
        """Render HTML snippet showing target user's experience table.

        Args:
            target_id (int): Database ID of target user to display experience for
            success_msg (str, optional): Message to display on successful operation. Defaults to empty string.

        Returns:
            str: Rendered HTML containing experience table with:
                - Campaign-specific experience points
                - Total experience points across all campaigns
                - Cool points earned per campaign

        Raises:
            HTTPException: If target user not found (404)
        """
        target = await User.get(target_id)
        if not target:
            abort(HTTPStatus.NOT_FOUND.value)

        guild = await fetch_guild(fetch_links=True)

        can_grant_xp = await self.permission_manager.can_grant_xp(
            author_id=session["USER_ID"], target_id=target_id
        )

        @dataclass
        class UserCampaignExperience:
            """Store campaign experience data for template rendering.

            Separate dataclass used instead of raw tuples to make the template
            code more maintainable and type-safe.
            """

            name: str
            xp: int
            total_xp: int  # Includes both direct XP and XP from cool points
            cp: int

        campaign_experience = []
        for campaign in guild.campaigns:
            campaign_xp, campaign_total_xp, campaign_cp = target.fetch_campaign_xp(campaign)
            campaign_experience.append(
                UserCampaignExperience(campaign.name, campaign_xp, campaign_total_xp, campaign_cp)  # type: ignore [attr-defined]
            )

        # Generate random ID to ensure success message shows even if same message content
        random_id = random_string(4)
        return catalog.render(
            "HTMXPartials.AddExperience.ExperienceTableView",
            user=target,
            campaign_experience=campaign_experience,
            can_grant_xp=can_grant_xp,
            success_msg=success_msg,
            random_id=random_id,
        )

    async def post(self, target_id: int) -> str:
        """Process form submission to add experience and cool points.

        Validate permissions, process form data, and update user's experience and cool points
        for the specified campaign.

        Args:
            target_id (int): Database ID of target user to receive points

        Returns:
            str: HTML snippet containing updated experience table or form with errors

        Raises:
            HTTPException: If target user not found (404)
            HTTPException: If user lacks permission to grant points (403)
            HTTPException: If invalid campaign ID provided (400)
        """
        target = await User.get(target_id)
        if not target:
            abort(HTTPStatus.NOT_FOUND.value, "Target user ID not found")

        can_grant_xp = await self.permission_manager.can_grant_xp(
            author_id=session["USER_ID"], target_id=target_id
        )

        if not can_grant_xp:
            abort(
                HTTPStatus.FORBIDDEN.value,
                "You do not have permission to add experience to this user",
            )

        # Fetch guild with links to ensure campaigns are populated for form choices
        guild = await fetch_guild(fetch_links=True)
        form = await AddExperienceForm().create_form(data={"target_id": target_id})
        # Populate campaign choices from guild campaigns to ensure user can only grant XP to campaigns they have access to
        form.campaign.choices = [(campaign.id, campaign.name) for campaign in guild.campaigns]  # type: ignore [attr-defined]

        if await form.validate_on_submit():
            if form.data["cancel"]:
                return await self.get(target_id)

            experience = int(form.data["experience"])
            cool_points = int(form.data["cool_points"])
            # Fetch active campaign to validate it exists and user has access
            campaign = await fetch_active_campaign(form.data["campaign"])

            if not campaign:
                abort(HTTPStatus.BAD_REQUEST.value, "Invalid campaign ID")

            # Only update if positive values provided to avoid unnecessary DB writes
            if experience > 0:
                await target.add_campaign_xp(campaign=campaign, amount=experience)
            if cool_points > 0:
                await target.add_campaign_cool_points(campaign=campaign, amount=cool_points)

            msg = self._build_success_message(experience, cool_points, target.name)
            await post_to_audit_log(msg=msg, view=self.__class__.__name__)
            return await self.get(target_id, success_msg=msg)

        return catalog.render(
            "HTMXPartials.AddExperience.FormPartial", form=form, target_id=target_id
        )
