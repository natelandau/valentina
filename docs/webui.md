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
