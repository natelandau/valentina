"""Modal windows for the application."""
import discord
from discord.ui import InputText, Modal

from valentina.constants import MAX_FIELD_COUNT, EmbedColor
from valentina.models.db_tables import CampaignChapter, CampaignNote, CampaignNPC, Character
from valentina.views import ConfirmCancelButtons


class ChangeNameModal(Modal):
    """A modal for changing the name of a character."""

    def __init__(self, ctx: discord.ApplicationContext, character: Character, *args, **kwargs) -> None:  # type: ignore [no-untyped-def]
        super().__init__(*args, **kwargs)
        self.character = character
        self.name = None
        self.ctx = ctx

        self.add_item(
            InputText(
                label="first name",
                placeholder="Enter a first name for the character",
                value=self.character.data.get("first_name", None),
                style=discord.InputTextStyle.short,
                required=True,
            )
        )
        self.add_item(
            InputText(
                label="last name",
                placeholder="Enter a last name for the character",
                value=self.character.data.get("last_name", None),
                style=discord.InputTextStyle.short,
                required=True,
            )
        )
        self.add_item(
            InputText(
                label="nickname",
                placeholder="Enter a nickname for the character",
                value=self.character.data.get("nickname", None),
                style=discord.InputTextStyle.short,
                required=False,
            )
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        """Callback for the modal."""
        self.first_name = self.children[0].value
        self.last_name = self.children[1].value
        self.nickname = self.children[2].value
        data = {}
        if self.first_name:
            data["first_name"] = self.first_name
        if self.last_name:
            data["last_name"] = self.last_name
        if self.nickname:
            data["nickname"] = self.nickname

        self.character = await self.ctx.bot.char_svc.update_or_add(  # type: ignore [attr-defined]
            self.ctx, character=self.character, data=data
        )

        embed = discord.Embed(title="Name Updated", color=EmbedColor.SUCCESS.value)
        await interaction.response.send_message(embeds=[embed], ephemeral=True, delete_after=0)

        self.stop()


class BioModal(Modal):
    """A modal for entering a biography."""

    def __init__(self, current_bio: str, *args, **kwargs) -> None:  # type: ignore [no-untyped-def]
        super().__init__(*args, **kwargs)
        self.bio: str = None
        self.current_bio = current_bio

        self.add_item(
            InputText(
                label="bio",
                placeholder="Enter a biography",
                value=self.current_bio if self.current_bio else None,
                required=True,
                style=discord.InputTextStyle.long,
                max_length=1900,
            )
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        """Callback for the modal."""
        embed = discord.Embed(title="Biography Updated", color=EmbedColor.SUCCESS.value)
        self.bio = self.children[0].value
        embed.add_field(name="Bio", value=self.children[0].value)

        await interaction.response.send_message(embeds=[embed], ephemeral=True, delete_after=0)
        self.stop()


class ChapterModal(Modal):
    """A modal for adding chapters."""

    def __init__(self, chapter: CampaignChapter | None = None, *args, **kwargs) -> None:  # type: ignore [no-untyped-def]
        super().__init__(*args, **kwargs)
        self.confirmed: bool = False
        self.name: str = ""
        self.short_description: str = ""
        self.description: str = ""

        self.add_item(
            InputText(
                label="name",
                placeholder="Enter a name for the chapter",
                value=chapter.name if chapter else None,
                required=True,
                style=discord.InputTextStyle.short,
            )
        )
        self.add_item(
            InputText(
                label="short_description",
                placeholder="A short description for the chapter",
                value=chapter.short_description if chapter else None,
                required=True,
                style=discord.InputTextStyle.long,
                max_length=500,
            )
        )
        self.add_item(
            InputText(
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

        embed = discord.Embed(title="Confirm Chapter", color=EmbedColor.INFO.value)
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
            await interaction.edit_original_response(
                embeds=[discord.Embed(title="Cancelled", color=EmbedColor.ERROR.value)]
            )

        self.stop()


class CustomSectionModal(Modal):
    """A modal for adding or editing a custom section."""

    def __init__(self, section_title: str | None = None, section_description: str | None = None, *args, **kwargs) -> None:  # type: ignore [no-untyped-def]
        super().__init__(*args, **kwargs)
        self.section_title = section_title
        self.section_description = section_description
        self.update_existing = bool(section_title)

        self.add_item(
            InputText(
                label="name",
                placeholder="Name of the section",
                value=self.section_title if self.section_title else None,
                required=True,
                style=discord.InputTextStyle.short,
            )
        )
        self.add_item(
            InputText(
                label="description",
                placeholder="Description of the section",
                value=self.section_description if self.section_description else None,
                required=True,
                style=discord.InputTextStyle.long,
                max_length=1900,
            )
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        """Callback for the modal."""
        self.section_title = self.children[0].value
        self.section_description = self.children[1].value

        embed_title = "Custom Section Updated" if self.update_existing else "Custom Section Added"
        embed = discord.Embed(title=embed_title, color=EmbedColor.SUCCESS.value)
        embed.add_field(name="Name", value=self.section_title)
        embed.add_field(name="Description", value=self.section_description)
        await interaction.response.send_message(embeds=[embed], ephemeral=True, delete_after=0)
        self.stop()


class MacroCreateModal(Modal):
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
            InputText(
                label="name",
                placeholder="Enter a name for the macro",
                value=self.name if self.name else None,
                required=True,
                style=discord.InputTextStyle.short,
            )
        )
        self.add_item(
            InputText(
                label="abbreviation",
                placeholder="Up to 4 character abbreviation",
                value=self.abbreviation if self.abbreviation else None,
                required=True,
                style=discord.InputTextStyle.short,
                max_length=4,
            )
        )
        self.add_item(
            InputText(
                label="description",
                placeholder="A brief description of what this macro does",
                value=self.description if self.description else None,
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

        embed = discord.Embed(title="Confirm macro creation", color=EmbedColor.INFO.value)
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
                embeds=[
                    discord.Embed(title="Macro creation cancelled", color=EmbedColor.ERROR.value)
                ]
            )

        self.stop()


class NoteModal(Modal):
    """A modal for adding chapters."""

    def __init__(self, note: CampaignNote | None = None, *args, **kwargs) -> None:  # type: ignore [no-untyped-def]
        super().__init__(*args, **kwargs)
        self.confirmed: bool = False
        self.name: str = ""
        self.description: str = ""

        self.add_item(
            InputText(
                label="name",
                placeholder="Enter a name for the chapter",
                value=note.name if note else None,
                required=True,
                style=discord.InputTextStyle.short,
            )
        )
        self.add_item(
            InputText(
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

        embed = discord.Embed(title="Confirm Note", color=EmbedColor.INFO.value)
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
            await interaction.edit_original_response(
                embeds=[discord.Embed(title="Cancelled", color=EmbedColor.ERROR.value)]
            )

        self.stop()


class NPCModal(Modal):
    """A modal for adding NPCs."""

    def __init__(self, npc: CampaignNPC | None = None, *args, **kwargs) -> None:  # type: ignore [no-untyped-def]
        super().__init__(*args, **kwargs)
        self.name: str = ""
        self.description: str = ""
        self.npc_class: str = ""
        self.confirmed: bool = False

        self.add_item(
            InputText(
                label="name",
                placeholder="Enter a name for the NPC",
                value=npc.name if npc else None,
                required=True,
                style=discord.InputTextStyle.short,
            )
        )
        self.add_item(
            InputText(
                label="npc_class",
                placeholder="Enter a class for the npc (e.g. 'vampire', 'mortal')",
                value=npc.npc_class if npc else None,
                required=True,
                style=discord.InputTextStyle.short,
            )
        )
        self.add_item(
            InputText(
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

        embed = discord.Embed(title="Confirm NPC", color=EmbedColor.INFO.value)
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
            await interaction.edit_original_response(
                embeds=[discord.Embed(title="Cancelled", color=EmbedColor.ERROR.value)]
            )

        self.stop()


class ProfileModal(Modal):
    """Update a character's profile."""

    def __init__(self, character: Character, *args, **kwargs) -> None:  # type: ignore [no-untyped-def]
        super().__init__(*args, **kwargs)
        self.confirmed: bool = False
        self.character: Character = character
        self.results: dict[str, str] = {
            "concept": "",
            "demeanor": "",
            "nature": "",
            "generation": "",
            "sire": "",
            "essence": "",
            "tradition": "",
            "breed": "",
            "tribe": "",
            "auspice": "",
        }

        self.add_item(
            InputText(
                label="concept",
                value=self.character.data.get("concept", None),
                placeholder="Enter a concept",
                required=False,
                style=discord.InputTextStyle.short,
                custom_id="concept",
            )
        )

        if self.character.char_class.name == "Vampire":
            self.add_item(
                InputText(
                    label="generation",
                    value=self.character.data.get("generation", None),
                    placeholder="Enter a generation (integer, e.g. 13 or 3)",
                    required=False,
                    style=discord.InputTextStyle.short,
                    custom_id="generation",
                )
            )

            self.add_item(
                InputText(
                    label="sire",
                    value=self.character.data.get("sire", None),
                    placeholder="Name of your sire",
                    required=False,
                    style=discord.InputTextStyle.short,
                    custom_id="sire",
                )
            )

        if self.character.char_class.name == "Mage":
            self.add_item(
                InputText(
                    label="essence",
                    value=self.character.data.get("essence", None),
                    placeholder="Your essence",
                    required=False,
                    style=discord.InputTextStyle.short,
                    custom_id="essence",
                )
            )
            self.add_item(
                InputText(
                    label="tradition",
                    value=self.character.data.get("tradition", None),
                    placeholder="Your tradition",
                    required=False,
                    style=discord.InputTextStyle.short,
                    custom_id="tradition",
                )
            )

        if self.character.char_class.name == "Werewolf":
            self.add_item(
                InputText(
                    label="breed",
                    value=self.character.data.get("breed", None),
                    placeholder="Your breed",
                    required=False,
                    style=discord.InputTextStyle.short,
                    custom_id="breed",
                )
            )
            self.add_item(
                InputText(
                    label="tribe",
                    value=self.character.data.get("tribe", None),
                    placeholder="Your tribe",
                    required=False,
                    style=discord.InputTextStyle.short,
                    custom_id="tribe",
                )
            )
            self.add_item(
                InputText(
                    label="auspice",
                    value=self.character.data.get("auspice", None),
                    placeholder="Your auspice",
                    required=False,
                    style=discord.InputTextStyle.short,
                    custom_id="auspice",
                )
            )

    async def callback(self, interaction: discord.Interaction) -> None:
        """Callback for the modal."""
        view = ConfirmCancelButtons(interaction.user)
        for c in self.children:
            self.results[c.custom_id] = c.value

        embed = discord.Embed(title="Confirm Profile", color=EmbedColor.INFO.value)
        for k, v in self.results.items():
            if v:
                embed.add_field(name=k.capitalize(), value=v, inline=True)

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        await view.wait()
        if view.confirmed:
            self.confirmed = True
            await interaction.delete_original_response()
        else:
            self.confirmed = False
            await interaction.edit_original_response(
                embeds=[discord.Embed(title="Cancelled", color=EmbedColor.ERROR.value)]
            )

        self.stop()
