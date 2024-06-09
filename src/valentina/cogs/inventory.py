# mypy: disable-error-code="valid-type"
"""Inventory cog for Valentina."""

import discord
from discord.commands import Option, OptionChoice
from discord.ext import commands

from valentina.constants import InventoryItemType
from valentina.models import InventoryItem
from valentina.models.bot import Valentina, ValentinaContext
from valentina.utils.autocomplete import select_char_inventory_item
from valentina.utils.converters import ValidInventoryItemFromID
from valentina.utils.discord_utils import character_from_channel
from valentina.utils.helpers import truncate_string
from valentina.views import InventoryItemModal, confirm_action, present_embed


class InventoryCog(commands.Cog, name="Inventory"):
    """Create, manage, and update a character's inventory."""

    def __init__(self, bot: Valentina) -> None:
        self.bot: Valentina = bot

    inventory = discord.SlashCommandGroup("inventory", "Add, remove, edit, or view inventory items")

    @inventory.command(name="list", description="List all items in a character's inventory")
    async def list_inventory(
        self,
        ctx: ValentinaContext,
    ) -> None:
        """List all items in a character's inventory."""
        character = await character_from_channel(ctx) or await ctx.fetch_active_character()
        items = await InventoryItem.find(InventoryItem.character == str(character.id)).to_list()

        description = ""
        for member in InventoryItemType:
            title = f"### {member.value}\n"
            sub_items = [i for i in items if i.type == member.name]
            item_list = ""
            for i in sub_items:
                line_begin = "- "
                name = f"**{i.name}**"
                desc = f": {i.description}" if i.description else ""
                line_end = "\n"
                item_list += f"{line_begin}{name}{desc}{line_end}"

            if sub_items:
                description += f"{title}{item_list}"

        await present_embed(
            ctx,
            title=f"{character.name}'s Inventory",
            description=description if items else "No items in inventory",
        )

    @inventory.command(name="add", description="Add an item to a character's inventory")
    async def add_inventory_item(
        self,
        ctx: ValentinaContext,
        item_type: Option(
            str,
            "Type of item to add",
            required=True,
            choices=[OptionChoice(x.value, x.name) for x in InventoryItemType],
        ),
    ) -> None:
        """Add an item to a character's inventory."""
        character = await character_from_channel(ctx) or await ctx.fetch_active_character()
        modal = InventoryItemModal(title=truncate_string(f"Add inventory to {character.name}", 45))
        await ctx.send_modal(modal)
        await modal.wait()

        if modal.confirmed:
            item_name = modal.item_name.strip().title()
            item_description = modal.item_description.strip()

            item = InventoryItem(
                name=item_name,
                description=item_description,
                character=str(character.id),
                type=item_type,
            )
            await item.save()

            character.inventory.append(item)
            await character.save()

            await ctx.post_to_audit_log(f"Add inventory item `{item_name}` to `{character.name}`")

    @inventory.command(name="edit", description="Edit an item in a character's inventory")
    async def edit_inventory_item(
        self,
        ctx: ValentinaContext,
        item: Option(
            ValidInventoryItemFromID,
            "Item to edit",
            required=True,
            autocomplete=select_char_inventory_item,
        ),
    ) -> None:
        """Edit an item in a character's inventory."""
        character = await character_from_channel(ctx) or await ctx.fetch_active_character()
        modal = InventoryItemModal(
            title=truncate_string(f"Edit {item.name}", 45),
            item_name=item.name,
            item_description=item.description,
        )
        await ctx.send_modal(modal)
        await modal.wait()

        if modal.confirmed:
            item.name = modal.item_name.strip().title()
            item.description = modal.item_description.strip()
            await item.save()

            character.inventory.append(item)
            await character.save()

            await ctx.post_to_audit_log(
                f"Update inventory item `{item.name}` for `{character.name}`"
            )

    @inventory.command(name="delete", description="Delete an item from a character's inventory")
    async def delete_inventory_item(
        self,
        ctx: ValentinaContext,
        item: Option(
            ValidInventoryItemFromID,
            "Item to delete from inventory",
            required=True,
            autocomplete=select_char_inventory_item,
        ),
    ) -> None:
        """Edit an item in a character's inventory."""
        character = await character_from_channel(ctx) or await ctx.fetch_active_character()

        title = f"Delete `{item.name}` from `{character.name}`'s inventory"
        is_confirmed, msg, confirmation_embed = await confirm_action(
            ctx,
            title,
            description="This is a destructive action that can not be undone.",
            audit=True,
        )
        if not is_confirmed:
            return

        character.inventory.remove(item)
        await character.save()

        await item.delete()

        # Send the confirmation message
        await msg.edit_original_response(embed=confirmation_embed, view=None)


def setup(bot: Valentina) -> None:
    """Add the cog to the bot."""
    bot.add_cog(InventoryCog(bot))
