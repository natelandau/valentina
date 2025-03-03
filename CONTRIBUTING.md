# Contributing

This project uses [uv](https://docs.astral.sh/uv/) to manage Python requirements and virtual environments.

## Setup: Once per project

1. Install [uv](https://docs.astral.sh/uv/)
2. Clone this repository. `git clone https://github.com/natelandau/valentina.git`
3. Install the virtual environment with `uv sync`.
4. Activate your virtual environment with `source .venv/bin/activate`
5. Install the pre-commit hooks with `pre-commit install --install-hooks`.
6. Install a local MongoDB instance for testing. The easiest way to do this is with [Docker](https://hub.docker.com/_/mongo). `docker run -d -p 27017:27017 --name valentina-mongo mongo:latest` will start a MongoDB instance on port `27017`.
7. Before running valentina locally, set the minimum required ENV variables with `export VAR=abc` or add them to a `.env` file within the project root.
    - `VALENTINA_DISCORD_TOKEN`
    - `VALENTINA_GUILDS`
    - `VALENTINA_OWNER_IDS`
    - `VALENTINA_LOG_FILE`
    - `VALENTINA_MONGO_URI`
    - `VALENTINA_MONGO_DATABASE_NAME`
    - `VALENTINA_TEST_MONGO_URI=mongodb://localhost:27017`
    - `VALENTINA_TEST_MONGO_DATABASE_NAME=valentina_test_db`

## Developing

-   This project follows the [Conventional Commits](https://www.conventionalcommits.org/) standard to automate [Semantic Versioning](https://semver.org/) and [Keep A Changelog](https://keepachangelog.com/) with [Commitizen](https://github.com/commitizen-tools/commitizen).
    -   When you're ready to commit changes run `cz c`
-   Run `duty --help` from within the development environment to print a list of [Duty](https://pawamoy.github.io/duty/) tasks available to run on this project. Common commands:
    -   `duty lint` runs all linters
    -   `duty test` runs all tests with Pytest
    -   `duty clean` cleans the project of temporary files
-   Run `uv add {package}` from within the development environment to install a run time dependency and add it to `pyproject.toml` and `uv.lock`.
-   Run `uv remove {package}` from within the development environment to uninstall a run time dependency and remove it from `pyproject.toml` and `uv.lock`.

## Common Patterns and Snippets

Documentation for common patterns used in development are available here:

-   [Developing the Discord bot](docs/discord.md)
-   [Developing the WebUI](docs/webui.md)

## Third Party Package Documentation

Many Python packages are used in this project. Here are some of the most important ones with links to their documentation:

**Discord Bot**

-   [Beanie ODM](https://beanie-odm.dev/) - MongoDB ODM
-   [ConfZ](https://confz.readthedocs.io/en/latest/index.html) - Configuration management
-   [Loguru](https://loguru.readthedocs.io/en/stable/) - Logging
-   [Pycord](https://docs.pycord.dev/en/stable/) - Discord API wrapper
-   [Typer](https://typer.tiangolo.com/) - CLI app framework

**Web UI**

-   [Bootstrap](https://getbootstrap.com/) - Frontend framework for the web UI
-   [HTMX](https://htmx.org/) - High level library for AJAX, WebSockets, and server sent events
-   [Jinja](https://jinja.palletsprojects.com/en/3.0.x/) - Templating engine for the web UI
-   [JinjaX](https://jinjax.scaletti.dev/) - Super components powers for your Jinja templates
-   [quart-wtf](https://quart-wtf.readthedocs.io/en/latest/index.html) - Integration of Quart and WTForms including CSRF and file uploading.
-   [Quart](https://quart.palletsprojects.com/en/latest/index.html) - Async web framework based on Flask

## Troubleshooting

If connecting to Discord with the bot fails due to a certificate error, run `scripts/install_certifi.py` to install the latest certificate bundle.
