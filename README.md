[![Automated Tests](https://github.com/natelandau/valentina/actions/workflows/automated-tests.yml/badge.svg)](https://github.com/natelandau/valentina/actions/workflows/automated-tests.yml) [![codecov](https://codecov.io/gh/natelandau/valentina/branch/main/graph/badge.svg?token=2ZNJ20XDOQ)](https://codecov.io/gh/natelandau/valentina)

# Valentina

A Discord bot used to help manage playing Vampire the Masquerade with a highly customized ruleset. Major differences from the published game are:

1. Rolled ones count as `-1` success
2. Rolled tens count as `2` successes
3. `Cool points` are additional rewards worth `10xp` each

If you want to play with traditional rules I strongly recommend you use [Inconnu](https://docs.inconnu.app/) which has significantly more features and provided inspiration for Valentina.

Valentina provides the following functionality:

-   Character management
    -   Create and update characters
    -   Manage and spend experience
-   Dicerolling
    -   Roll any number of arbitrary dice
    -   Roll any number `d10s` with a set difficulty

## Install and run

### Prerequisites

Before running Valentina, the following must be configured or installed.

-   Docker and Docker Compose
-   A valid Discord Bot token. Instructions for this can be found on [Discord's Developer Portal](https://discord.com/developers/docs/getting-started)

### Run the bot

1. Copy the `docker-compose.yml` file to a directory on your machine
2. Edit the `docker-compose.yml` file
    - In the `volumes` section replace `/path/to/data` with the directory to hold persistent storage
    - In the `environment` section add correct values to each environment variable. All available environment variables are below.
3. Run `docker compose up`

#### Environment Variables

| Variable                    | Default Value              | Usage                                                                                                                                |
| --------------------------- | -------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| VALENTINA_BACKUP_PATH       | `/valentina/backup`        | Sets the directory to store database backups.<br />Note, this is the directory used withing the Docker container                     |
| VALENTINA_DAILY_RETENTION   | `7`                        | Sets the number of days to retain database backups.                                                                                  |
| VALENTINA_DB_PATH           | `/valentina/db`            | Sets the directory to store the database.<br />Note, this is the directory used withing the Docker container                         |
| VALENTINA_DISCORD_TOKEN     |                            | Sets the Discord bot token. This is required to run the bot.                                                                         |
| VALENTINA_GUILDS            |                            | Sets the Discord guilds the bot is allowed to join. This is a comma separated list of guild IDs.                                     |
| VALENTINA_LOG_FILE          | `/valentina/valentina.log` | Sets the file to write logs to.<br />Note, this is the directory used withing the Docker container                                   |
| VALENTINA_LOG_LEVEL         | `INFO`                     | Sets master log level. One of `TRACE`, `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`                                               |
| VALENTINA_LOG_LEVEL_DB      | `INFO`                     | Sets the log level for database SQL queries. One of `TRACE`, `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`                         |
| VALENTINA_LOG_LEVEL_HTTP    | `INFO`                     | Sets the log level for discord HTTP, gateway, webhook,client events. One of `TRACE`, `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| VALENTINA_MONTHLY_RETENTION | `12`                       | Sets the number of months to retain database backups.                                                                                |
| VALENTINA_OWNER_IDS         |                            | Sets the Discord user IDs that are allowed to run bot admin commands. This is a comma separated list of Discord user IDs.            |
| VALENTINA_WEEKLY_RETENTION  | `4`                        | Sets the number of weeks to retain database backups.                                                                                 |
| VALENTINA_YEARLY_RETENTION  | `2`                        | Sets the number of years to retain database backups.                                                                                 |

---

## Contributing

## Setup: Once per project

There are two ways to contribute to this project.

### 1. Local development

1. Install Python 3.11 and [Poetry](https://python-poetry.org)
2. Clone this repository. `git clone https://some.url/to/the/package.git`
3. Install the Poetry environment with `poetry install`.
4. Activate your Poetry environment with `poetry shell`.
5. Install the pre-commit hooks with `pre-commit install --install-hooks`.
6. Before running valentina locally, set the ENV variables with `export VAR=abc`
    - `VALENTINA_DISCORD_TOKEN`
    - `VALENTINA_GUILDS`
    - `VALENTINA_OWNER_IDS`

### 2. Containerized development

1. Clone this repository. `git clone https://some.url/to/the/package.git`
2. Open the repository in Visual Studio Code
3. Start the [Dev Container](https://code.visualstudio.com/docs/remote/containers). Run <kbd>Ctrl/⌘</kbd> + <kbd>⇧</kbd> + <kbd>P</kbd> → _Remote-Containers: Reopen in Container_.
4. Run `poetry env info -p` to find the PATH to the Python interpreter if needed by VSCode.

## Developing

-   This project follows the [Conventional Commits](https://www.conventionalcommits.org/) standard to automate [Semantic Versioning](https://semver.org/) and [Keep A Changelog](https://keepachangelog.com/) with [Commitizen](https://github.com/commitizen-tools/commitizen).
    -   When you're ready to commit changes run `cz c`
-   Run `poe` from within the development environment to print a list of [Poe the Poet](https://github.com/nat-n/poethepoet) tasks available to run on this project. Common commands:
    -   `poe lint` runs all linters
    -   `poe test` runs all tests with Pytest
-   Run `poetry add {package}` from within the development environment to install a run time dependency and add it to `pyproject.toml` and `poetry.lock`.
-   Run `poetry remove {package}` from within the development environment to uninstall a run time dependency and remove it from `pyproject.toml` and `poetry.lock`.
-   Run `poetry update` from within the development environment to upgrade all dependencies to the latest versions allowed by `pyproject.toml`.
