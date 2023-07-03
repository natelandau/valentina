"""Modal windows for the application."""
import discord

from valentina.models.constants import MAX_FIELD_COUNT
from valentina.models.database import ChronicleChapter, ChronicleNote, ChronicleNPC
from valentina.views import ConfirmCancelButtons


class NoteModal(discord.ui.Modal):
    """A modal for adding chapters."""

    def __init__(self, note: ChronicleNote | None = None, *args, **kwargs) -> None:  # type: ignore [no-untyped-def]
        super().__init__(*args, **kwargs)
        self.confirmed: bool = False
        self.name: str = ""
        self.description: str = ""

        self.add_item(
            discord.ui.InputText(
                label="name",
                placeholder="Enter a name for the chapter",
                value=note.name if note else None,
                required=True,
                style=discord.InputTextStyle.short,
            )
        )
        self.add_item(
            discord.ui.InputText(
                label="description",
                placeholder="Write a description for the chapter",
                value=note.description if note else None,
                required=True,
                style=discord.InputTextStyle.long,
                max_length=1900,
            )
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        """Callback for the modal."""
        view = ConfirmCancelButtons(interaction.user)
        self.name = self.children[0].value
        self.description = self.children[1].value

        embed = discord.Embed(title="Confirm Note")
        embed.add_field(name="Note Name", value=self.name, inline=True)
        embed.add_field(
            name="Description",
            value=(self.description[:MAX_FIELD_COUNT] + " ...")
            if len(self.description) > MAX_FIELD_COUNT
            else self.description,
        )

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        await view.wait()
        if view.confirmed:
            self.confirmed = True
            await interaction.delete_original_response()
        else:
            self.confirmed = False
            await interaction.edit_original_response(embeds=[discord.Embed(title="Cancelled")])

        self.stop()


class ChapterModal(discord.ui.Modal):
    """A modal for adding chapters."""

    def __init__(self, chapter: ChronicleChapter | None = None, *args, **kwargs) -> None:  # type: ignore [no-untyped-def]
        super().__init__(*args, **kwargs)
        self.confirmed: bool = False
        self.name: str = ""
        self.short_description: str = ""
        self.description: str = ""

        self.add_item(
            discord.ui.InputText(
                label="name",
                placeholder="Enter a name for the chapter",
                value=chapter.name if chapter else None,
                required=True,
                style=discord.InputTextStyle.short,
            )
        )
        self.add_item(
            discord.ui.InputText(
                label="short_description",
                placeholder="A short description for the chapter",
                value=chapter.short_description if chapter else None,
                required=True,
                style=discord.InputTextStyle.long,
                max_length=500,
            )
        )
        self.add_item(
            discord.ui.InputText(
                label="chapter",
                placeholder="Write the chapter",
                value=chapter.description if chapter else None,
                required=True,
                style=discord.InputTextStyle.long,
                max_length=1900,
            )
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        """Callback for the modal."""
        view = ConfirmCancelButtons(interaction.user)
        self.name = self.children[0].value
        self.short_description = self.children[1].value
        self.description = self.children[2].value

        embed = discord.Embed(title="Confirm Chapter")
        embed.add_field(name="Chapter Name", value=self.name, inline=True)
        embed.add_field(name="Short Description", value=self.short_description, inline=True)
        embed.add_field(
            name="Chapter",
            value=(self.description[:MAX_FIELD_COUNT] + " ...")
            if len(self.description) > MAX_FIELD_COUNT
            else self.description,
            inline=False,
        )

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        await view.wait()
        if view.confirmed:
            self.confirmed = True
            await interaction.delete_original_response()
        else:
            self.confirmed = False
            await interaction.edit_original_response(embeds=[discord.Embed(title="Cancelled")])

        self.stop()


class NPCModal(discord.ui.Modal):
    """A modal for adding NPCs."""

    def __init__(self, npc: ChronicleNPC | None = None, *args, **kwargs) -> None:  # type: ignore [no-untyped-def]
        super().__init__(*args, **kwargs)
        self.name: str = ""
        self.description: str = ""
        self.npc_class: str = ""
        self.confirmed: bool = False

        self.add_item(
            discord.ui.InputText(
                label="name",
                placeholder="Enter a name for the NPC",
                value=npc.name if npc else None,
                required=True,
                style=discord.InputTextStyle.short,
            )
        )
        self.add_item(
            discord.ui.InputText(
                label="npc_class",
                placeholder="Enter a class for the npc (e.g. 'vampire', 'mortal')",
                value=npc.npc_class if npc else None,
                required=True,
                style=discord.InputTextStyle.short,
            )
        )
        self.add_item(
            discord.ui.InputText(
                label="description",
                placeholder="Enter a description for the NPC",
                value=npc.description if npc else None,
                required=True,
                style=discord.InputTextStyle.long,
                max_length=1900,
            )
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        """Callback for the modal."""
        view = ConfirmCancelButtons(interaction.user)
        self.name = self.children[0].value
        self.npc_class = self.children[1].value
        self.description = self.children[2].value

        embed = discord.Embed(title="Confirm NPC")
        embed.add_field(name="NPC Name", value=self.name, inline=True)
        embed.add_field(name="NPC Class", value=self.npc_class, inline=True)
        embed.add_field(
            name="Description",
            value=(self.description[:MAX_FIELD_COUNT] + " ...")
            if len(self.description) > MAX_FIELD_COUNT
            else self.description,
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        await view.wait()
        if view.confirmed:
            self.confirmed = True
            await interaction.delete_original_response()
        else:
            self.confirmed = False
            await interaction.edit_original_response(embeds=[discord.Embed(title="Cancelled")])

        self.stop()


class MacroCreateModal(discord.ui.Modal):
    """A modal for adding macros."""

    def __init__(self, trait_one: str, trait_two: str, *args, **kwargs) -> None:  # type: ignore [no-untyped-def]
        super().__init__(*args, **kwargs)
        self.name: str = None
        self.abbreviation: str = None
        self.description: str = ""
        self.confirmed: bool = False
        self.trait_one = trait_one
        self.trait_two = trait_two

        self.add_item(
            discord.ui.InputText(
                label="name",
                placeholder="Enter a name for the macro",
                required=True,
                style=discord.InputTextStyle.short,
            )
        )
        self.add_item(
            discord.ui.InputText(
                label="abbreviation",
                placeholder="Up to 4 character abbreviation",
                required=True,
                style=discord.InputTextStyle.short,
                max_length=4,
            )
        )
        self.add_item(
            discord.ui.InputText(
                label="description",
                placeholder="A brief description of what this macro does",
                required=False,
                style=discord.InputTextStyle.long,
                max_length=600,
            )
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        """Callback for the modal."""
        view = ConfirmCancelButtons(interaction.user)
        self.name = self.children[0].value
        self.abbreviation = self.children[1].value
        self.description = self.children[2].value

        embed = discord.Embed(title="Confirm macro creation")
        embed.add_field(name="Macro Name", value=self.name)
        embed.add_field(name="Abbreviation", value=self.abbreviation)
        embed.add_field(
            name="Description",
            value=(self.description[:MAX_FIELD_COUNT] + " ...")
            if len(self.description) > MAX_FIELD_COUNT
            else self.description,
        )
        embed.add_field(name="Trait One", value=self.trait_one)
        embed.add_field(name="Trait Two", value=self.trait_two)
        await interaction.response.send_message(embeds=[embed], ephemeral=True, view=view)

        await view.wait()
        if view.confirmed:
            self.confirmed = True
            await interaction.delete_original_response()
        if not view.confirmed:
            self.confirmed = False
            await interaction.edit_original_response(
                embeds=[discord.Embed(title="Macro creation cancelled")]
            )

        self.stop()
