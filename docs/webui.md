# Development Notes for the Web UI

Code snippets and notes to help you develop the Web UI.

## Automatic Registration of Blueprints and Routes

Pages and functionality for the web UI are managed within the `valentina/webui` directory. Each page is a separate blueprint that is imported into the Quart app.

All blueprints following the file structure below will be **automatically registered with the Quart app**.

```
webui/blueprints
  └── [blueprint_name]
      ├── __init__.py
      ├── blueprint.py
      ├── route.py
      └── templates
          └── [blue_print_name]
```

-   `__init__.py` - Empty file to mark the directory as part of the Python package.
-   `blueprint.py` - Contains the `blueprint` object to be automatically registered with the Quart app.
-   `route.py` - Contains the route definitions for the blueprint.
-   `templates/<blueprint_name>` - Contains the Jinja templates for the blueprint. These are added as a top-level folder in the JinJax catalog and can be imported into templates.
-   Any other files required for the blueprint.

## The Session Object

The session object is used to store information about each user's session. Specifically, the following keys are used:

-   `ACTIVE_CAMPAIGN_ID` - The ID of the active campaign.
-   `ACTIVE_CHARACTER_ID` - The ID of the active character.
-   `ALL_CHARACTERS` - A list of all characters in the guild. Each character is a dictionary with the following keys: `id`, `name`, `campaign_name`, `campaign_id`, `owner_name`, and `owner_id`.
-   `GUILD_CAMPAIGNS` - A dictionary of all the campaigns in the guild. This dictionary contains the campaign name as the key and the campaign id as the value.
-   `GUILD_ID` - The guild's database and Discord id
-   `GUILD_NAME` - The name of the guild
-   `IS_STORYTELLER` - A boolean indicating whether the user is a storyteller.
-   `RNG_DRAFT_CHARACTERS` - (temporary) A dictionary of characters that have been created by the RNG character creator. Used to store the characters until they are claimed by a user or deleted by the database
-   `STORYTELLER_CHARACTERS` - A list of all the storyteller character IDs in the guild. Each character is a dictionary with the following keys: `id`, `name`, `campaign_name`, `campaign_id`, `owner_name`, and `owner_id`.
-   `USER_AVATAR_URL` - The URL of the user's Discord avatar
-   `USER_CHARACTERS` - A list of all the user's characters. This dictionary contains the following keys: `id`, `name`, `campaign_name`, `campaign_id`, `owner_name`, and `owner_id`.
-   `USER_ID` - The user's database and Discord id
-   `USER_NAME` - The user's Discord name

## Global primitives

The following primitives are available within all jinja templates. These are created using [JinjaX](https://jinjax.scaletti.dev/) partials and included in templates with a similar format to HTML tags.

### Create a toast

To create a toast, use the `global.Toast` primitive.

Args:

-   `msg` - The message to display in the toast.
-   `level` - The level of the toast. Must be one of the following: `success`, `error`, `warning`, `info`.

```jinja
<global.Toast msg={{ msg }} level="success" />
```

## HTMX

[HTMX](https://htmx.org/) is a library that allows you to add interactivity to your HTML without needing to write JavaScript. It is used to handle the interaction between the client and the server. Common patterns used in Valentina are:

### Confirmation Dialogs before issuing requests

The javascript package [SweetAlert2](https://sweetalert2.github.io/) is used to create confirmation dialogs. To confirm an HTMX request before it is issued to the server, follow this pattern. Note the `hx-trigger='confirmed'` and the `onClick` event which pauses the HTMX request until the user confirms the dialog.

**NOTE:** SweetAlert2 is not loaded by default. It must be added to the individual pages that require it. Use the `{% block head %}` tag to add it to the page.

```jinja
{% block head %}
    <script src="https://cdn.jsdelivr.net/npm/sweetalert2@11"></script>
{% endblock head %}
```

To see an example of the confirmation dialog integration with HTMX, see the `Delete Image` button in the character view.

```jinja
<button class="btn btn-danger btn-sm ms-3"
    hx-delete="{{ url_for('partials.characterimages', character_id=character.id, url=img_url) }}"
    hx-trigger='confirmed'
    onClick="Swal.fire({title: 'Confirm Delete', text:'Are you sure you want to delete this image?', confirmButtonText: 'Confirm',confirmButtonColor: 'red', showCancelButton: true}).then((result)=>{ if(result.isConfirmed){ htmx.trigger(this, 'confirmed'); } })"
    hx-target="#character-images-body"
    hx-swap="innerHTML swap:0.5s">Delete Image</button>
```

### Redirecting to a page after a request

To redirect to a new page, a route can return a string containing a `<script>` tag that will redirect the user to the new page.

```python
return f'<script>window.location.href="{url_for("homepage.homepage", success_msg="MESSAGE"</script>'
```
