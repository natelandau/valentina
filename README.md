[![Automated Tests](https://github.com/natelandau/valentina/actions/workflows/automated-tests.yml/badge.svg)](https://github.com/natelandau/valentina/actions/workflows/automated-tests.yml) [![codecov](https://codecov.io/gh/natelandau/valentina/branch/main/graph/badge.svg?token=2ZNJ20XDOQ)](https://codecov.io/gh/natelandau/valentina)

# Valentina

A Discord bot and optional web service to manage roll playing sessions for a highly customized version of the White Wolf series of TTRPGs. This project is not affiliated with White Wolf or [Paradox Interactive](https://www.paradoxinteractive.com/).

## Topline Features

-   Character creation and management
-   Campaign management
-   Dice rolling
-   Storyteller tools
-   Other niceties such as:
    -   Optional Web UI
    -   Github integration
    -   Image uploads
    -   Statistic tracking
    -   And more!

## Ruleset Overview

Major differences from the games published by White Wolf are:

1. Dice are rolled as a single pool of D10s with a set difficulty. The number of success determines the outcome of the roll.

> `< 0` successes: Botch `0` successes: Failure `> 0` successes: Success `> dice pool` successes: Critical success

2. Rolled ones count as `-1` success
3. Rolled tens count as `2` successes
4. `Cool points` are additional rewards worth `10xp` each

To play with traditional rules I strongly recommend you use [Inconnu Bot](https://docs.inconnu.app/) instead.

**For more information on the features and functionality, see the [User Guide](user_guide.md)**

# Install and run

## Prerequisites

Before running Valentina, the following must be configured or installed.

<details>
<summary>Discord Bot</summary>

-   Docker and Docker Compose
-   A valid Discord Bot token. Instructions for this can be found on [Discord's Developer Portal](https://discord.com/developers/docs/getting-started)

</details>

<details>
<summary>Web UI (Optional)</summary>

-   A Redis instance for caching. This can be run locally or in a cloud service.
-   Discord OAuth credentials for the bot. Instructions for this can be found on [Discord's Developer Portal](https://discord.com/developers/docs/topics/oauth2)
-   Ability to run the Docker container on a public IP address or domain name. This is outside the scope of this document.
</details>

<details>
<summary>Image Uploads (Optional)</summary>
To allow image uploads, an AWS S3 bucket must be configured with appropriate permissions. Instructions for this can be found on the [AWS Documentation](https://docs.aws.amazon.com/AmazonS3/latest/userguide/creating-bucket.html)

-   Public must be able to read objects from the bucket
-   An IAM role must be created with read/write/list access and the credentials added to the environment variables.

    ```json
    {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "GetBucketLocation",
                "Effect": "Allow",
                "Action": ["s3:GetBucketLocation"],
                "Resource": ["arn:aws:s3:::Bucket-Name"]
            },
            {
                "Sid": "ListObjectsInBucket",
                "Effect": "Allow",
                "Action": ["s3:ListBucket"],
                "Resource": ["arn:aws:s3:::Bucket-Name"]
            },
            {
                "Sid": "AllObjectActions",
                "Effect": "Allow",
                "Action": "s3:*Object",
                "Resource": ["arn:aws:s3:::Bucket-Name/*"]
            }
        ]
    }
    ```

</details>

## Run the bot (Local)

1. Enter the virtual environment with `source .venv/bin/activate`
2. Confirm the app is configured correctly
3. Run `valentina --help` to see the available options
4. Run `valentina [options]` to run the bot

## Run the bot (Docker)

1. Copy the `docker-compose.yml` file to a directory on your machine
2. Edit the `docker-compose.yml` file
    - In the `volumes` section replace `/path/to/data` with the directory to hold persistent storage
    - In the `environment` section add correct values to each environment variable.
3. Run `docker compose up`

### Environment Variables

Settings for Valentina are controlled by environment variables. The following is a list of the available variables and their default values.

| Variable | Default Value | Usage |
| --- | --- | --- |
| VALENTINA_AWS_ACCESS_KEY_ID |  | Access key for AWS (_Optional: Only needed for image uploads_) |
| VALENTINA_AWS_SECRET_ACCESS_KEY |  | Secret access key for AWS (_Optional: Only needed for image uploads_) |
| VALENTINA_S3_BUCKET_NAME |  | Name of the S3 bucket to use (_Optional: Only needed for image uploads_) |
| VALENTINA_DISCORD_TOKEN |  | Sets the Discord bot token. This is required to run the bot. |
| VALENTINA_GUILDS |  | Sets the Discord guilds the bot is allowed to join. This is a comma separated string of guild IDs. |
| VALENTINA_LOG_FILE | `/valentina/valentina.log` | Sets the file to write logs to.<br />Note, this is the directory used within the Docker container |
| VALENTINA_LOG_LEVEL | `INFO` | Sets master log level. One of `TRACE`, `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| VALENTINA_LOG_LEVEL_AWS | `INFO` | Sets the log level for AWS S3. One of `TRACE`, `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| VALENTINA_LOG_LEVEL_HTTP | `WARNING` | Sets the log level for discord HTTP, gateway, webhook,client events. One of `TRACE`, `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| VALENTINA_LOG_LEVEL_PYMONGO | `WARNING` | Sets the log level for PyMongo. One of `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| VALENTINA_OWNER_CHANNELS |  | Sets the Discord channels that are allowed to run bot admin commands. This is a comma separated string of Discord channel IDs. |
| VALENTINA_OWNER_IDS |  | Sets the Discord user IDs that are allowed to run bot admin commands. This is a comma separated string of Discord user IDs. |
| VALENTINA_MONGO_URI | `mongodb://localhost:27017` | Production MongoDB URI |
| VALENTINA_MONGO_DATABASE_NAME | `valentina` | Production Database name |
| VALENTINA_GITHUB_REPO |  | Optional: Sets the Github repo to use for Github integration `username/repo` |
| VALENTINA_GITHUB_TOKEN |  | Optional: Sets the Github API Access token to use for Github integration |
| VALENTINA_WEBUI_ENABLE | `false` | Optional: Enables the web UI. Set to `true` to enable. |
| VALENTINA_WEBUI_HOST | `127.0.0.1` | Set the host IP for the web UI. Note: when running in Docker this should always be `0.0.0.0` |
| VALENTINA_WEBUI_PORT | `8088` | Set the port for the web UI. |
| VALENTINA_WEBUI_LOG_LEVEL | `INFO` | Sets the log level for the web UI. One of `TRACE`, `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| VALENTINA_WEBUI_BASE_URL | `http://127.0.0.1:8088` | Base URL for the web service. |
| VALENTINA_WEBUI_DEBUG | `false` | Enables debug mode for the web UI. Set to `true` to enable. |
| VALENTINA_REDIS_ADDRESS | `127.0.0.1:6379` | Sets the IP and port for the Redis instance |
| VALENTINA_REDIS_PASSWORD |  | Optional: Sets the password for the Redis instance |
| VALENTINA_WEBUI_SECRET_KEY |  | Sets the secret key for the web UI. This is required to run the web UI. |
| VALENTINA_DISCORD_OAUTH_SECRET |  | Sets the secret for the Discord OAuth. This is required to run the web UI. |
| VALENTINA_DISCORD_OAUTH_CLIENT_ID |  | Sets the ID for the Discord OAuth. This is required to run the web UI. |
| VALENTINA_WEBUI_BEHIND_REVERSE_PROXY | `false` | Set to `true` if the web UI is behind a reverse proxy. |
| VALENTINA_WEBUI_ACCESS_LOG | `/valentina/access.log` | Sets the file to write access logs to.<br />Note, this is the directory used within the Docker container |
| VALENTINA_CLOUDFLARE_ANALYTICS_TOKEN |  | Optional: Enable Cloudflare Web Analytics by setting this to your Cloudflare Web Analytics token |
| VALENTINA_GOOGLE_ANALYTICS_ID |  | Optional: Enable Google Analytics by setting this to your Google Analytics ID |

---

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

## Access logs from the webui

Set the location of the access logs with the `VALENTINA_WEBUI_ACCESS_LOG` environment variable.

These logs can be parsed with any web log parser. For example, with goaccess:

```bash
goaccess access.log \
    --log-format='[%d %t %z] [%^] [%^] %h %^ %^ [%^ %^] "%m %U %^" %s %b "%R" "%u"' \
    --date-format=%Y-%m-%d \
    --time-format='%T' \
    --tz=America/New_York \
    --no-ip-validation # Optional: Disables IP validation for local testing
```
