"""Route for editing character info such as notes and custom sheet sections."""

from uuid import UUID

from quart import Response, abort, request, session, url_for
from quart.views import MethodView
from quart_wtf import QuartForm
from wtforms import (
    HiddenField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import DataRequired, Length

from valentina.models import Character, CharacterSheetSection, Note
from valentina.webui import catalog
from valentina.webui.utils import fetch_active_character
from valentina.webui.utils.discord import post_to_audit_log


class CustomSectionForm(QuartForm):
    """Form for a custom section."""

    title = StringField(
        "Title", validators=[DataRequired(), Length(min=3, message="Must be at least 3 characters")]
    )
    content = TextAreaField(
        "Content",
        validators=[DataRequired(), Length(min=3, message="Must be at least 3 characters")],
    )

    uuid = HiddenField()
    submit = SubmitField("Submit")


class CharacterNoteForm(QuartForm):
    """Form for a character note."""

    text = TextAreaField("Text", validators=[DataRequired()])
    note_id = HiddenField()
    submit = SubmitField("Submit")


class EditCharacterCustomSection(MethodView):
    """Edit the character's info."""

    async def _build_form(self, character: Character) -> QuartForm:
        """Build the form and populate with existing data if available."""
        data = {}

        if request.args.get("uuid", None):
            uuid = UUID(request.args.get("uuid"))
            for section in character.sheet_sections:
                if section.uuid == uuid:
                    data["title"] = str(section.title)
                    data["content"] = str(section.content)
                    data["uuid"] = str(section.uuid)
                    break

        return await CustomSectionForm().create_form(data=data)

    async def get(self, character_id: str) -> str:
        """Render the form."""
        character = await fetch_active_character(character_id, fetch_links=False)

        return catalog.render(
            "character_edit.CustomSectionForm",
            character=character,
            form=await self._build_form(character),
            join_label=False,
            floating_label=True,
            post_url=url_for("character_edit.customsection", character_id=character_id),
        )

    async def post(self, character_id: str) -> Response | str:
        """Process the form."""
        character = await fetch_active_character(character_id, fetch_links=False)

        form = await self._build_form(character)
        if await form.validate_on_submit():
            form_data = {
                k: v if v else None
                for k, v in form.data.items()
                if k not in {"submit", "character_id", "csrf_token"}
            }

            section_title = form_data["title"].strip().title()
            section_content = form_data["content"].strip()

            updated_existing = False
            if form_data.get("uuid"):
                uuid = UUID(form_data["uuid"])
                for section in character.sheet_sections:
                    if section.uuid == uuid:
                        section.title = section_title
                        section.content = section_content
                        updated_existing = True
                        break

            if not updated_existing:
                character.sheet_sections.append(
                    CharacterSheetSection(title=section_title, content=section_content)
                )

            await post_to_audit_log(
                msg=f"Character {character.name} section `{section_title}` added",
                view=self.__class__.__name__,
            )
            await character.save()

            return Response(
                headers={
                    "HX-Redirect": url_for(
                        "character_view.view",
                        character_id=character_id,
                        success_msg="Custom section updated!",
                    ),
                }
            )

        # If POST request does not validate, return errors
        return catalog.render(
            "character_edit.CustomSectionForm",
            character=character,
            form=form,
            join_label=False,
            floating_label=True,
            post_url=url_for("character_edit.customsection", character_id=character_id),
        )

    async def delete(self, character_id: str) -> Response:
        """Delete the section."""
        character = await fetch_active_character(character_id, fetch_links=False)

        uuid = request.args.get("uuid", None)
        if not uuid:
            abort(400)

        for section in character.sheet_sections:
            if section.uuid == UUID(uuid):
                character.sheet_sections.remove(section)
                break

        await post_to_audit_log(
            msg=f"Character {character.name} section `{section.title}` deleted",
            view=self.__class__.__name__,
        )
        await character.save()
        return Response(
            headers={
                "HX-Redirect": url_for(
                    "character_view.view",
                    character_id=character_id,
                    success_msg="Custom section deleted",
                ),
            }
        )


class EditCharacterNote(MethodView):
    """Edit the character's note."""

    async def _build_form(self) -> QuartForm:
        """Build the form and populate with existing data if available."""
        data = {}

        if request.args.get("note_id"):
            existing_note = await Note.get(request.args.get("note_id"))
            if existing_note:
                data["text"] = existing_note.text
                data["note_id"] = str(existing_note.id)

        return await CharacterNoteForm().create_form(data=data)

    async def get(self, character_id: str) -> str:
        """Render the form."""
        character = await fetch_active_character(character_id, fetch_links=False)
        return catalog.render(
            "character_edit.CustomSectionForm",
            character=character,
            form=await self._build_form(),
            join_label=False,
            floating_label=True,
            post_url=url_for("character_edit.note", character_id=character_id),
        )

    async def post(self, character_id: str) -> Response | str:
        """Process the form."""
        character = await fetch_active_character(character_id, fetch_links=True)
        form = await self._build_form()

        if await form.validate_on_submit():
            if not form.data.get("note_id"):
                new_note = Note(
                    text=form.data["text"].strip(),
                    parent_id=str(character.id),
                    created_by=session["USER_ID"],
                )
                await new_note.save()
                character.notes.append(new_note)
                await character.save()
                msg = "Note Added!"
            else:
                existing_note = await Note.get(form.data["note_id"])
                existing_note.text = form.data["text"]
                await existing_note.save()
                msg = "Note Updated!"

            return Response(
                headers={
                    "HX-Redirect": url_for(
                        "character_view.view",
                        character_id=character_id,
                        success_msg=msg,
                    ),
                }
            )

        # If POST request does not validate, return errors
        return catalog.render(
            "character_edit.CustomSectionForm",
            character=character,
            form=form,
            join_label=False,
            floating_label=True,
            post_url=url_for("character_edit.note", character_id=character_id),
        )

    async def delete(self, character_id: str) -> Response:
        """Delete the note."""
        character = await fetch_active_character(character_id, fetch_links=True)

        note_id = request.args.get("note_id", None)
        if not note_id:
            abort(400)

        existing_note = await Note.get(note_id)
        for note in character.notes:
            if note == existing_note:
                character.notes.remove(note)
                break

        await existing_note.delete()

        await post_to_audit_log(
            msg=f"Character {character.name} note `{existing_note.text}` deleted",
            view=self.__class__.__name__,
        )
        await character.save()
        return Response(
            headers={
                "HX-Redirect": url_for(
                    "character_view.view", character_id=character_id, success_msg="Note deleted"
                )
            }
        )
