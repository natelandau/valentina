"""Manage channels within a Guild."""

import asyncio
from typing import Optional

import discord
from loguru import logger

from valentina.constants import CHANNEL_PERMISSIONS, CampaignChannelName, ChannelPermission, Emoji
from valentina.models import Campaign, CampaignBook, Character

from valentina.discord.utils.discord_utils import set_channel_perms  # isort:skip

CAMPAIGN_COMMON_CHANNELS = {  # channel_db_key: channel_name
    "channel_storyteller": CampaignChannelName.STORYTELLER.value,
    "channel_general": CampaignChannelName.GENERAL.value,
}


class ChannelManager:
    """Manage channels within a Guild."""

    def __init__(self, guild: discord.Guild, user: discord.User | discord.Member):
        self.guild = guild
        self.user = user

    @staticmethod
    def _channel_sort_order(channel: discord.TextChannel) -> tuple[int, str]:  # pragma: no cover
        """Generate a custom sorting key for campaign channels.

        Prioritize channels based on their names, assigning a numeric value for sorting order.

        Args:
            channel (discord.TextChannel): The Discord text channel to generate the sort key for.

        Returns:
            tuple[int, str]: A tuple containing the sort priority (int) and the channel name (str).
        """
        if channel.name.startswith(Emoji.CHANNEL_GENERAL.value):
            return (0, channel.name)

        if channel.name.startswith(Emoji.BOOK.value):
            return (1, channel.name)

        if channel.name.startswith(Emoji.CHANNEL_PRIVATE.value):
            return (2, channel.name)

        if channel.name.startswith(Emoji.CHANNEL_PLAYER.value):
            return (3, channel.name)

        if channel.name.startswith(Emoji.CHANNEL_PLAYER_DEAD.value):
            return (4, channel.name)

        return (5, channel.name)

    async def _remove_unused_campaign_channels(
        self, campaign: Campaign, channels: list[discord.TextChannel]
    ) -> None:
        """Remove any unused campaign channels."""
        for channel in channels:
            if channel.name.startswith(Emoji.BOOK.value) and not any(
                book.channel == channel.id for book in await campaign.fetch_books()
            ):
                await self.delete_channel(channel)
                await asyncio.sleep(1)

            if (
                channel.name.startswith(Emoji.CHANNEL_PLAYER.value)
                or channel.name.startswith(Emoji.CHANNEL_PLAYER_DEAD.value)
            ) and not any(
                character.channel == channel.id
                for character in await campaign.fetch_player_characters()
            ):
                await self.delete_channel(channel)
                await asyncio.sleep(1)

            if (
                channel.name.startswith(
                    f"{Emoji.CHANNEL_PRIVATE.value}{Emoji.CHANNEL_PLAYER.value}"
                )
                or channel.name.startswith(
                    f"{Emoji.CHANNEL_PRIVATE.value}{Emoji.CHANNEL_PLAYER_DEAD.value}"
                )
                and not any(
                    character.channel == channel.id
                    for character in await campaign.fetch_storyteller_characters()
                )
            ):
                await self.delete_channel(channel)
                await asyncio.sleep(1)

            if (
                channel.name.startswith(f"{Emoji.CHANNEL_PRIVATE.value}-")
                or channel.name.startswith(f"{Emoji.CHANNEL_GENERAL.value}-")
                and not (
                    campaign.channel_storyteller != channel.id
                    or campaign.channel_general != channel.id
                )
            ):
                await self.delete_channel(channel)
                await asyncio.sleep(1)

    async def _confirm_campaign_common_channels(
        self,
        campaign: Campaign,
        category: discord.CategoryChannel,
        channels: list[discord.TextChannel],
    ) -> None:
        """Ensure common campaign channels exist and are up-to-date.

        This method checks for the existence of common campaign channels within the specified category.
        If a channel does not exist, it creates it. If a channel exists but its ID does not match the
        database, it updates the database with the correct ID.

        Args:
            campaign (Campaign): The campaign object containing channel information.
            category (discord.CategoryChannel): The category under which the channels should exist.
            channels (list[discord.TextChannel]): The list of existing channels in the category.
        """
        for channel_db_key, channel_name in CAMPAIGN_COMMON_CHANNELS.items():
            await asyncio.sleep(1)  # Keep the rate limit happy
            channel_db_id = getattr(campaign, channel_db_key, None)
            channel = await self.confirm_channel_in_category(
                existing_category=category,
                existing_channels=channels,
                channel_name=channel_name,
                channel_db_id=channel_db_id,
            )

            if not channel_db_id or channel_db_id != channel.id:
                setattr(campaign, channel_db_key, channel.id)
                await campaign.save()

    def _determine_channel_permissions(
        self, channel_name: str
    ) -> tuple[ChannelPermission, ChannelPermission, ChannelPermission]:
        """Determine the permissions for the specified channel based on its name.

        Args:
            channel_name (str): The name of the channel to determine permissions for.

        Returns:
            tuple[ChannelPermission, ChannelPermission, ChannelPermission]: A tuple containing:
                - The default role permissions (ChannelPermission)
                - The player role permissions (ChannelPermission)
                - The storyteller role permissions (ChannelPermission)
        """
        if channel_name.startswith(Emoji.CHANNEL_PRIVATE.value):
            return CHANNEL_PERMISSIONS["storyteller_channel"]

        if channel_name.startswith((Emoji.CHANNEL_PLAYER.value, Emoji.CHANNEL_PLAYER_DEAD.value)):
            return CHANNEL_PERMISSIONS["campaign_character_channel"]

        return CHANNEL_PERMISSIONS["default"]

    async def confirm_channel_in_category(
        self,
        existing_category: discord.CategoryChannel,
        existing_channels: list[discord.TextChannel],
        channel_name: str,
        channel_db_id: int | None = None,
        owned_by_user: discord.User | discord.Member | None = None,
        topic: str | None = None,
    ) -> discord.TextChannel:
        """Confirm the channel exists in the category.

        Confirm that the channel exists within the category. If the channel does not exist, create it.

        Args:
            existing_category (discord.CategoryChannel): The category to check for the channel in.
            existing_channels (list[discord.TextChannel]): The list of channels existing in the category.
            channel_name (str): The name of the channel to check for.
            channel_db_id (optional, int): The ID of the channel in the database.
            owned_by_user (discord.User | discord.Member, optional): The user who owns the channel. Defaults to None.
            topic (str, optional): The topic description for the channel. Defaults to None.

        Returns:
            discord.TextChannel: The channel object.
        """
        channel_name_is_in_category = any(
            channel_name == channel.name for channel in existing_channels
        )
        channel_db_id_is_in_category = (
            any(channel_db_id == channel.id for channel in existing_channels)
            if channel_db_id
            else False
        )

        # If the channel exists in the category, return it
        if channel_name_is_in_category:
            logger.info(
                f"Channel {channel_name} exists in {existing_category} but not in database. Add channel id to database."
            )
            await asyncio.sleep(1)  # Keep the rate limit happy
            preexisting_channel = next(
                (channel for channel in existing_channels if channel.name == channel_name),
                None,
            )
            # update channel permissions
            await asyncio.sleep(1)  # Keep the rate limit happy
            return await self.channel_update_or_add(
                channel=preexisting_channel,
                name=channel_name,
                category=existing_category,
                permissions=self._determine_channel_permissions(channel_name),
                permissions_user_post=owned_by_user,
                topic=topic,
            )

        # If the channel id exists but the name is different, rename the existing channel
        if channel_db_id and channel_db_id_is_in_category and not channel_name_is_in_category:
            existing_channel_object = next(
                (channel for channel in existing_channels if channel_db_id == channel.id), None
            )
            logger.info(
                f"Channel {channel_name} exists in database and {existing_category} but name is different. Renamed channel."
            )

            await asyncio.sleep(1)  # Keep the rate limit happy
            return await self.channel_update_or_add(
                channel=existing_channel_object,
                name=channel_name,
                category=existing_category,
                permissions=self._determine_channel_permissions(channel_name),
                permissions_user_post=owned_by_user,
                topic=topic,
            )

        # Finally, if the channel does not exist in the category, create it

        await asyncio.sleep(1)  # Keep the rate limit happy
        logger.info(
            f"Channel {channel_name} does not exist in {existing_category}. Create channel."
        )
        await asyncio.sleep(1)  # Keep the rate limit happy
        return await self.channel_update_or_add(
            name=channel_name,
            category=existing_category,
            permissions=self._determine_channel_permissions(channel_name),
            permissions_user_post=owned_by_user,
            topic=topic,
        )

    async def channel_update_or_add(
        self,
        permissions: tuple[ChannelPermission, ChannelPermission, ChannelPermission],
        channel: discord.TextChannel | None = None,
        name: str | None = None,
        topic: str | None = None,
        category: discord.CategoryChannel | None = None,
        permissions_user_post: discord.User | discord.Member | None = None,
    ) -> discord.TextChannel:  # pragma: no cover
        """Create or update a channel in the guild with specified permissions and attributes.

        Create a new text channel or update an existing one based on the provided name. Set permissions for default role, player role, and storyteller role. Automatically grant manage permissions to bot members. If specified, set posting permissions for a specific user.

        Args:
            permissions (tuple[ChannelPermission, ChannelPermission, ChannelPermission]): Permissions for default role, player role, and storyteller role respectively.
            channel (discord.TextChannel, optional): Existing channel to update. Defaults to None.
            name (str, optional): Name for the channel. Defaults to None.
            topic (str, optional): Topic description for the channel. Defaults to None.
            category (discord.CategoryChannel, optional): Category to place the channel in. Defaults to None.
            permissions_user_post (discord.User | discord.Member, optional): User to grant posting permissions. Defaults to None.

        Returns:
            discord.TextChannel: The newly created or updated text channel.
        """
        # Fetch roles from the guild
        player_role = discord.utils.get(self.guild.roles, name="Player")
        storyteller_role = discord.utils.get(self.guild.roles, name="Storyteller")

        # Initialize permission overwrites. Always grant manage permissions to bots.
        overwrites = {  # type: ignore[misc]
            self.guild.default_role: set_channel_perms(permissions[0]),
            player_role: set_channel_perms(permissions[1]),
            storyteller_role: set_channel_perms(permissions[2]),
            **{
                user: set_channel_perms(ChannelPermission.MANAGE)
                for user in self.guild.members
                if user.bot
            },
        }

        if permissions_user_post:
            overwrites[permissions_user_post] = set_channel_perms(ChannelPermission.POST)

        formatted_name = name.lower().strip().replace(" ", "-") if name else None

        if name and not channel:
            for existing_channel in self.guild.text_channels:
                # If channel already exists in a specified category, edit it
                if (
                    category
                    and existing_channel.category == category
                    and existing_channel.name == formatted_name
                ) or (not category and existing_channel.name == formatted_name):
                    logger.debug(f"GUILD: Update channel '{channel.name}' on '{self.guild.name}'")
                    await existing_channel.edit(
                        name=formatted_name or channel.name,
                        overwrites=overwrites,
                        topic=topic or channel.topic,
                        category=category or channel.category,
                    )
                    return existing_channel

            # Create the channel if it doesn't exist
            logger.debug(f"GUILD: Create channel '{name}' on '{self.guild.name}'")
            return await self.guild.create_text_channel(
                name=formatted_name,
                overwrites=overwrites,
                topic=topic,
                category=category,
            )

        # Update existing channel
        logger.debug(f"GUILD: Update channel '{channel.name}' on '{self.guild.name}'")
        await channel.edit(
            name=name or channel.name,
            overwrites=overwrites,
            topic=topic or channel.topic,
            category=category or channel.category,
        )

        return channel

    async def confirm_book_channel(
        self, book: CampaignBook, campaign: Optional[Campaign]
    ) -> discord.TextChannel | None:
        """Confirm and retrieve the Discord text channel associated with a given campaign book.

        This method ensures that the specified campaign book has an associated text channel
        within the campaign's category. If the campaign is not provided, it fetches the campaign
        using the book's campaign ID. It then verifies the existence of the campaign's category
        and channels, creating or confirming the required text channel for the book.

        Args:
            book (CampaignBook): The campaign book for which the text channel is to be confirmed.
            campaign (Optional[Campaign]): The campaign associated with the book. If not provided,
                                           it will be fetched using the book's campaign ID.

        Returns:
            discord.TextChannel | None: The confirmed or newly created Discord text channel for the book, or None if the campaign category does not exist.
        """
        logger.debug(f"Confirming channel for book {book.number}. {book.name}")
        if not campaign:
            campaign = await Campaign.get(book.campaign)

        category, channels = await self.fetch_campaign_category_channels(campaign=campaign)

        # If the campaign category channel does not exist, return None
        if not category:
            return None

        channel_db_id = book.channel

        channel = await self.confirm_channel_in_category(
            existing_category=category,
            existing_channels=channels,
            channel_name=book.channel_name,
            channel_db_id=channel_db_id,
            topic=f"Channel for book {book.number}. {book.name}",
        )
        await book.update_channel_id(channel)
        await asyncio.sleep(1)  # Keep the rate limit happy
        return channel

    async def confirm_campaign_channels(self, campaign: Campaign) -> None:
        """Confirm and manage the channels for a given campaign.

        This method ensures that the necessary category and channels for the campaign exist,
        are correctly named, and are recorded in the database.

        Args:
            campaign (Campaign): The campaign object containing details about the campaign.
        """
        # Confirm the campaign category channel exists and is recorded in the database
        campaign_category_channel_name = (
            f"{Emoji.BOOKS.value}-{campaign.name.lower().replace(' ', '-')}"
        )
        if campaign.channel_campaign_category:
            existing_campaign_channel_object = self.guild.get_channel(
                campaign.channel_campaign_category
            )

            if not existing_campaign_channel_object:
                category = await self.guild.create_category(campaign_category_channel_name)
                campaign.channel_campaign_category = category.id
                await campaign.save()
                logger.debug(
                    f"Campaign category '{campaign_category_channel_name}' created in '{self.guild.name}'"
                )

            elif existing_campaign_channel_object.name != campaign_category_channel_name:
                await existing_campaign_channel_object.edit(name=campaign_category_channel_name)
                logger.debug(
                    f"Campaign category '{campaign_category_channel_name}' renamed in '{self.guild.name}'"
                )

            else:
                logger.debug(
                    f"Category {campaign_category_channel_name} already exists in {self.guild.name}"
                )
        else:
            category = await self.guild.create_category(campaign_category_channel_name)
            campaign.channel_campaign_category = category.id
            await campaign.save()
            logger.debug(
                f"Campaign category '{campaign_category_channel_name}' created in '{self.guild.name}'"
            )

        category, channels = await self.fetch_campaign_category_channels(campaign=campaign)

        # Confirm common channels exist
        await self._confirm_campaign_common_channels(
            campaign=campaign, category=category, channels=channels
        )

        for book in await campaign.fetch_books():
            await self.confirm_book_channel(book=book, campaign=campaign)
            await asyncio.sleep(1)

        for character in await campaign.fetch_player_characters():
            await self.confirm_character_channel(character=character, campaign=campaign)
            await asyncio.sleep(1)

        for character in await campaign.fetch_storyteller_characters():
            await self.confirm_character_channel(character=character, campaign=campaign)
            await asyncio.sleep(1)

        # Remove any channels that should not exist
        await self._remove_unused_campaign_channels(campaign, channels)

        await self.sort_campaign_channels(campaign)

        logger.info(f"All channels confirmed for campaign '{campaign.name}' in '{self.guild.name}'")

    async def confirm_character_channel(
        self, character: Character, campaign: Optional[Campaign]
    ) -> discord.TextChannel | None:
        """Confirm the existence of a character-specific text channel within a campaign category.

        This method checks if a text channel for a given character exists within the specified campaign's category. If the campaign or category does not exist, it returns None. Otherwise, it ensures the channel exists, updates the character's channel ID, and returns the channel.

        Args:
            character (Character): The character for whom the channel is being confirmed.
            campaign (Optional[Campaign]): The campaign within which to confirm the character's channel.

        Returns:
            discord.TextChannel | None: The confirmed text channel for the character, or None if the campaign or category does not exist.
        """
        logger.debug(f"Confirming channel for character {character.name}")

        if not campaign:
            return None

        category, channels = await self.fetch_campaign_category_channels(campaign=campaign)

        # If the campaign category channel does not exist, return None
        if not category:
            return None

        owned_by_user = discord.utils.get(self.guild.members, id=character.user_owner)
        channel_name = character.channel_name
        channel_db_id = character.channel

        channel = await self.confirm_channel_in_category(
            existing_category=category,
            existing_channels=channels,
            channel_name=channel_name,
            channel_db_id=channel_db_id,
            owned_by_user=owned_by_user,
            topic=f"Character channel for {character.name}",
        )
        await character.update_channel_id(channel)

        await asyncio.sleep(1)  # Keep the rate limit happy
        return channel

    async def delete_book_channel(self, book: CampaignBook) -> None:
        """Delete the Discord channel associated with the given book.

        Args:
            book (CampaignBook): The book object containing the channel information.
        """
        if not book.channel:
            return

        channel = self.guild.get_channel(book.channel)
        if channel:
            await self.delete_channel(channel)

        book.channel = None
        await book.save()

    async def delete_campaign_channels(self, campaign: Campaign) -> None:
        """Delete all Discord channels associated with the given campaign.

        Args:
            campaign (Campaign): The campaign object whose channels are to be deleted.
        """
        for book in await campaign.fetch_books():
            await self.delete_book_channel(book)

        for character in await campaign.fetch_player_characters():
            await self.delete_character_channel(character)

        for character in await campaign.fetch_storyteller_characters():
            await self.delete_character_channel(character)

        for channel_db_key in CAMPAIGN_COMMON_CHANNELS:
            if getattr(campaign, channel_db_key, None):
                await self.delete_channel(getattr(campaign, channel_db_key))
                setattr(campaign, channel_db_key, None)
                await campaign.save()
                await asyncio.sleep(1)  # Keep the rate limit happy

        if campaign.channel_campaign_category:
            await self.delete_channel(campaign.channel_campaign_category)
            campaign.channel_campaign_category = None
            await campaign.save()
            await asyncio.sleep(1)

    async def delete_channel(
        self,
        channel: discord.TextChannel
        | discord.CategoryChannel
        | discord.VoiceChannel
        | discord.ForumChannel
        | discord.StageChannel
        | int,
    ) -> None:
        """Delete a specified channel from the guild.

        This method deletes a given channel from the guild. The channel can be specified
        as a discord.TextChannel, discord.CategoryChannel, discord.VoiceChannel,
        discord.ForumChannel, discord.StageChannel, or an integer representing the channel ID.

        Args:
            channel (discord.TextChannel | int): The channel to delete.
        """
        if isinstance(channel, int):
            channel = self.guild.get_channel(channel)

        if not channel:
            return

        logger.debug(f"GUILD: Delete channel '{channel.name}' on '{self.guild.name}'")
        await channel.delete()
        await asyncio.sleep(1)  # Keep the rate limit happy

    async def delete_character_channel(self, character: Character) -> None:
        """Delete the channel associated with the character.

        Args:
            character (Character): The character object containing the channel information.
        """
        if not character.channel:
            return

        channel = self.guild.get_channel(character.channel)
        if channel:
            await self.delete_channel(channel)

        character.channel = None
        await character.save()

    async def fetch_campaign_category_channels(
        self, campaign: Campaign
    ) -> tuple[discord.CategoryChannel, list[discord.TextChannel]]:
        """Fetch the campaign's channels in the guild.

        Retrieve the category channel and its child text channels for the current campaign
        from the Discord guild.

        Args:
            campaign (Campaign): The campaign to fetch the channels for.

        Returns:
            tuple[discord.CategoryChannel, list[discord.TextChannel]]: A tuple containing:
                - The campaign category channel (discord.CategoryChannel or None if not found)
                - A list of text channels within that category (empty list if category not found)
        """
        for category, channels in self.guild.by_category():
            if category and category.id == campaign.channel_campaign_category:
                return category, [x for x in channels if isinstance(x, discord.TextChannel)]

        return None, []

    async def sort_campaign_channels(self, campaign: Campaign) -> None:
        """Sort the campaign's channels within its category.

        This method sorts the channels within the campaign's category based on a custom sorting order.
        It ensures that the channels are positioned correctly according to the defined sort order.

        Args:
            campaign (Campaign): The campaign object containing details about the campaign.
        """
        for category, channels in self.guild.by_category():
            if category and category.id == campaign.channel_campaign_category:
                sorted_channels = sorted(channels, key=self._channel_sort_order)  # type: ignore[arg-type]
                for i, channel in enumerate(sorted_channels):
                    if channel.position and channel.position == i:
                        continue
                    await channel.edit(position=i)
                    await asyncio.sleep(2)  # Keep the rate limit happy

                logger.debug(f"Sorted channels: {[channel.name for channel in sorted_channels]}")
                break

        logger.info(f"Channels sorted for campaign '{campaign.name}' in '{self.guild.name}'")
