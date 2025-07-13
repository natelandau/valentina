# Contributing

Thank you for your interest in contributing to Valentina! This document provides guidelines and instructions to make the contribution process smooth and effective.

## Development Setup

### Prerequisites

This project uses [uv](https://docs.astral.sh/uv/) for dependency management. To start developing:

1. Install uv using the [recommended method](https://docs.astral.sh/uv/installation/) for your operating system
2. Clone this repository: `git clone https://github.com/natelandau/valentina`
3. Navigate to the repository: `cd valentina`
4. Install dependencies with uv: `uv sync`
5. Activate your virtual environment: `source .venv/bin/activate`
6. Install pre-commit hooks: `pre-commit install --install-hooks`
7. [Install Docker](https://www.docker.com/get-started/) to run the development environment
8. Use the [Discord Developer Portal](https://discord.com/developers/applications) to create a test Discord application and bot token and set the `VALENTINA_DISCORD_TOKEN` environment variable.

### Running Tasks

We use [Duty](https://pawamoy.github.io/duty/) as our task runner. Common tasks:

-   `duty --list` - List all available tasks
-   `duty lint` - Run all linters
-   `duty test` - Run all tests
-   `duty clean` - Clean the project of all temporary files
-   `duty dev-clean` - Clean the development environment
-   `duty dev-setup` - Set up the development environment in `.dev` including storage for logs, the development database, and Redis instance all of which are mounted as volumes.

### Set environment variables

Copy the `.env` file to `.env.secrets` and add your own values to configure Valentina.

These variables are required for the bot to run:

-   `VALENTINA_DISCORD_TOKEN`
-   `VALENTINA_GUILDS`
-   `VALENTINA_OWNER_IDS`
-   `VALENTINA_MONGO_DATABASE_NAME`

> [!IMPORTANT]\
> The recommended approach to developing Valentina is to use the [Docker Compose](https://docs.docker.com/compose/) file to start the development environment (more info below). **The following environment variables should not be set in `.env.secrets` unless you know what you are doing.**
>
> -   `VALENTINA_MONGO_URI`
> -   `VALENTINA_REDIS_ADDRESS`
> -   `VALENTINA_REDIS_PASSWORD`

### Start the development environment

Starting the development environment with a development database and Redis instanceis as easy as running:

```bash
# Start the development environment
docker compose up

# Trigger a rebuild of the Valentina container
docker compose up --build
```

Alternatively, you can run the databases from docker and the bot outside of docker for faster development:

```bash
docker compose -f compose-db.yml up -d
uv run valentina
```

> [!WARNING]\
> Running `duty dev-setup` or `duty dev-clean` will delete all of the data in the development database and Redis instance.

### Running tests

To run tests, run `duty test`. This will run all tests in the `tests` directory.

```bash
duty test
```

> [!IMPORTANT]\
> To run tests, you must have a MongoDB instance available on port `localhost:27017`. The development environment will start one for you using docker if you don't have one running.

### Convenience Commands

Once the development environment is running, the following slash commands are available in your test Discord Server:

-   `/developer guild create_dummy_data` - Populate the database and Discord server with dummy data for testing.
-   `/developer guild create_test_characters` - Create test characters in the database.
-   `/admin rebuild_campaign_channels` - Rebuild the campaign channels in the Discord server.
-   `/admin delete_campaign_channels` - Delete the campaign channels in the Discord server.

## Development Guidelines

When developing for ezbak, please follow these guidelines:

-   Write full docstrings
-   All code should use type hints
-   Write unit tests for all new functions
-   Write integration tests for all new features
-   Follow the existing code style

## Commit Process

1. Create a branch for your feature or fix
2. Make your changes
3. Ensure code passes linting with `duty lint`
4. Ensure tests pass with `duty test`
5. Commit using [Commitizen](https://github.com/commitizen-tools/commitizen): `cz c`
6. Push your branch and create a pull request

We use [Semantic Versioning](https://semver.org/) for version management.

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
