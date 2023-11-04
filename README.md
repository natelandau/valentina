[![Automated Tests](https://github.com/natelandau/valentina/actions/workflows/automated-tests.yml/badge.svg)](https://github.com/natelandau/valentina/actions/workflows/automated-tests.yml) [![codecov](https://codecov.io/gh/natelandau/valentina/branch/main/graph/badge.svg?token=2ZNJ20XDOQ)](https://codecov.io/gh/natelandau/valentina)

# Valentina

A discord bot to manage roll playing sessions for a highly customized version of Vampire the Masquerade. Major differences from the published game are:

1. Dice a rolled as a single pool of D10s with a set difficulty. The number of success determines the outcome of the roll.

> `< 0` successes: Botch
> `0` successes: Failure
> `> 0` successes: Success
> `> dice pool` successes: Critical success

2. Rolled ones count as `-1` success
3. Rolled tens count as `2` successes
4. `Cool points` are additional rewards worth `10xp` each

To play with traditional rules I strongly recommend you use [Inconnu Bot](https://docs.inconnu.app/) instead.

**For more information on the features and functionality, see the [User Guide](user_guide.md)**

## Install and run

### Prerequisites

Before running Valentina, the following must be configured or installed.

-   Docker and Docker Compose
-   A valid Discord Bot token. Instructions for this can be found on [Discord's Developer Portal](https://discord.com/developers/docs/getting-started)
-   To use image uploads, an AWS S3 Bucket must be configured with appropriate permissions. _(Instructions on how to do this are out of scope for this document)_

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

### Run the bot

1. Copy the `docker-compose.yml` file to a directory on your machine
2. Edit the `docker-compose.yml` file
    - In the `volumes` section replace `/path/to/data` with the directory to hold persistent storage
    - In the `environment` section add correct values to each environment variable. All available environment variables are below.
3. Run `docker compose up`

#### Environment Variables

| Variable                        | Default Value               | Usage                                                                                                                                |
| ------------------------------- | --------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| VALENTINA_AWS_ACCESS_KEY_ID     |                             | Access key for AWS (_Optional: Only needed for image uploads_)                                                                       |
| VALENTINA_AWS_SECRET_ACCESS_KEY |                             | Secret access key for AWS (_Optional: Only needed for image uploads_)                                                                |
| VALENTINA_S3_BUCKET_NAME        |                             | Name of the S3 bucket to use (_Optional: Only needed for image uploads_)                                                             |
| VALENTINA_DISCORD_TOKEN         |                             | Sets the Discord bot token. This is required to run the bot.                                                                         |
| VALENTINA_GUILDS                |                             | Sets the Discord guilds the bot is allowed to join. This is a comma separated string of guild IDs.                                   |
| VALENTINA_LOG_FILE              | `/valentina/valentina.log`  | Sets the file to write logs to.<br />Note, this is the directory used within the Docker container                                    |
| VALENTINA_LOG_LEVEL             | `INFO`                      | Sets master log level. One of `TRACE`, `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`                                               |
| VALENTINA_LOG_LEVEL_AWS         | `INFO`                      | Sets the log level for AWS S3. One of `TRACE`, `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`                                       |
| VALENTINA_LOG_LEVEL_DB          | `INFO`                      | Sets the log level for database SQL queries. One of `TRACE`, `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`                         |
| VALENTINA_LOG_LEVEL_HTTP        | `INFO`                      | Sets the log level for discord HTTP, gateway, webhook,client events. One of `TRACE`, `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| VALENTINA_OWNER_CHANNELS        |                             | Sets the Discord channels that are allowed to run bot admin commands. This is a comma separated string of Discord channel IDs.       |
| VALENTINA_OWNER_IDS             |                             | Sets the Discord user IDs that are allowed to run bot admin commands. This is a comma separated string of Discord user IDs.          |
| VALENTINA_MONGO_URI             | `mongodb://localhost:27017` | Production MongoDB URI                                                                                                               |
| VALENTINA_MONGO_DATABASE_NAME   | `valentina`                 | Production Database name                                                                                                             |

---

## Contributing

## Setup: Once per project

1. Install Python 3.11 and [Poetry](https://python-poetry.org)
2. Clone this repository. `git clone https://github.com/natelandau/valentina.git`
3. Install the Poetry environment with `poetry install`.
4. Activate your Poetry environment with `poetry shell`.
5. Install the pre-commit hooks with `pre-commit install --install-hooks`.
6. Before running valentina locally, set the minimum required ENV variables with `export VAR=abc`
    - `VALENTINA_DISCORD_TOKEN`
    - `VALENTINA_GUILDS`
    - `VALENTINA_OWNER_IDS`
    - `VALENTINA_LOG_FILE`
    - `VALENTINA_MONGO_URI`
    - `VALENTINA_MONGO_DATABASE_NAME`

## Developing

-   This project follows the [Conventional Commits](https://www.conventionalcommits.org/) standard to automate [Semantic Versioning](https://semver.org/) and [Keep A Changelog](https://keepachangelog.com/) with [Commitizen](https://github.com/commitizen-tools/commitizen).
    -   When you're ready to commit changes run `cz c`
-   Run `poe` from within the development environment to print a list of [Poe the Poet](https://github.com/nat-n/poethepoet) tasks available to run on this project. Common commands:
    -   `poe lint` runs all linters
    -   `poe test` runs all tests with Pytest
-   Run `poetry add {package}` from within the development environment to install a runtime dependency and add it to `pyproject.toml` and `poetry.lock`.
-   Run `poetry remove {package}` from within the development environment to uninstall a runtime dependency and remove it from `pyproject.toml` and `poetry.lock`.
-   Run `poetry update` from within the development environment to upgrade all dependencies to the latest versions allowed by `pyproject.toml`.

## Testing MongoDB locally

To run the tests associated with the MongoDB database, you must have MongoDB installed locally. The easiest way to do this is with Docker. Set two additional environment variables to allow the tests to connect to the local MongoDB instance.

| Variable                   | Default Value               | Usage                                        |
| -------------------------- | --------------------------- | -------------------------------------------- |
| VALENTINA_TEST_MONGODB_URI | `mongodb://localhost:27017` | URI to the MongoDB instance used for testing |
| VALENTINA_TEST_MONGODB_DB  | `valentina-test-db`         | Name of the database used for testing        |

NOTE: Github CI integrations will ignore these variables and run the tests against a Mongo instance within the workflows.

## Troubleshooting

If connecting to Discord with the bot fails due to a certificate error, run `scripts/install_certifi.py` to install the latest certificate bundle.
