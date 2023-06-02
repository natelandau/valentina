# Valentina

A Discord bot used to help manage TTRPGs.

## Install CLI apps

Use [PIPX](https://pypa.github.io/pipx/) to install this package from Github.

```bash
pipx install git+https://some.url/to/the/package.git
```

Running the above command will install all script entry points as standalone scripts in the users' PATH.

**Note: You must be authenticated on Github for this to work**

**_Alternative_**
You can install from the local filesystem. This approach will create a link to the _editable version_ of the script which may cause problems if you plan on developing from that directory.

```bash
pipx install ~/path/to/project
```

## Contributing

## Setup: Once per project

There are two ways to contribute to this project.

### 1. Local development

1. Install Python 3.11 and [Poetry](https://python-poetry.org)
2. Clone this repository. `git clone https://some.url/to/the/package.git`
3. Install the Poetry environment with `poetry install`.
4. Activate your Poetry environment with `poetry shell`.
5. Install the pre-commit hooks with `pre-commit install --install-hooks`.

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
