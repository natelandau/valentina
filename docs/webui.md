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

Possible levels are: `success`, `error`, `warning`, `info`. There are two ways to create a toast message:

1.  Use the `flash` function in the route. This is the most common and easiest way to create a toast message.

```python
await flash(msg, "success")

return f'<script>window.location.href="{url_for("homepage.homepage")}"</script>'

# or

return await catalog.render("homepage.homepage",)
```

2.  Include the `global.Toast` primitive in the template. This will create a toast message in the next response. This is commonly used when HTMX partials are returned from a route which does not reload an entire template.

```jinja
{% if something %}
<global.Toast msg={{ msg }} level="success" />
{% endif %}
```

Or from within a route itself. Use this when HTMX is deleting an item and the only thing that needs to be returnedis the toast message:

```python
await catalog.render("global.Toast", msg=msg, level="success")
```

## Long running tasks

To keep long-running tasks from blocking routes, create a `BrokerTask` which will be executed by the `TaskBroker` at 1 minute intervals.

```python
from valentina.constants import BrokerTaskType
from valentina.models import BrokerTask

@app.route("/rebuild-channels")
async def rebuild_channels():
    task = BrokerTask(task=BrokerTaskType.REBUILD_CHANNELS, guild_id=session["GUILD_ID"])
    await task.insert()
    return "Task created"
```

## HTMX

[HTMX](https://htmx.org/) is a library that allows you to add interactivity to your HTML without needing to write JavaScript. It is used to handle the interaction between the client and the server. Common patterns used in Valentina are:

### Confirmation Dialogs before issuing requests

The javascript package [SweetAlert2](https://sweetalert2.github.io/) is used to create confirmation dialogs. To confirm an HTMX request before it is issued to the server, follow this pattern. Note the `hx-trigger='confirmed'` and the `onClick` event which pauses the HTMX request until the user confirms the dialog.

**NOTE:** SweetAlert2 is not loaded by default. It must be added to the individual pages that require it. When using the `PageLayout` template, set the `sweetalert` parameter to `True`.

```jinja
<PageLayout title={{ character.name }} _attrs={{ attrs }} sweetalert={{ True }}>
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
return f'<script>window.location.href="{url_for("homepage.homepage", success_msg="MESSAGE")}"</script>'
```

### Editable Tables of Database Items

Editable tables of database items share a common pattern. The Route, templates, and HTMXPartials are all designed to work together to allow for creation, editing, and deletion of items in the database.

The steps to create an editable table are:

1.  Add the type to the `constants.TableType` enum.
2.  Add the form to the `blueprints/HTMXPartials/forms.py` file.
3.  Configure the `EditTableView` route to use the form.
4.  Add the new table type to the templates in the `ItemDisplayPartial.jinja` file which has the HTML table rows.
5.  Add the necessary items to the template of the page that will display the table.

The route for the page that displays the table should have a parameter for the table type.

```python
from valentina.webui.constants import TableType

def get(self, table_type: TableType) -> str:
    ...
    items = await DatabaseModel.find(DatabaseModel.guild_id == session["GUILD_ID"]).to_list()
    catalog.render("route.route_name", table_type=TableType.SOMETHING, can_edit=True)
```

In the page template, use the `TablePartial` to display the table.

```jinja
<HTMXPartials.EditTable.TablePartial TableType={{ table_type }} items={{ items }} can_edit={{ can_edit }} />
```
