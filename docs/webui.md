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
