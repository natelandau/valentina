# type: ignore
"""Test the changelog parser."""

import pytest
from rich import print  # noqa: A004

from valentina.models import ChangelogParser

sample_changelog = """
## v2.0.0 (2023-11-04)

### Feat

- Lorem ipsum dolor sit amet (#100)
- Lorem ipsum dolor sit amet

### Fix

- Lorem ipsum dolor sit amet (#100)
- Lorem ipsum dolor sit amet

### Test

- Lorem ipsum dolor sit amet (#100)
- Lorem ipsum dolor sit amet

### Build

- Lorem ipsum dolor sit amet (#100)
- Lorem ipsum dolor sit amet

### CI

- Lorem ipsum dolor sit amet (#100)
- Lorem ipsum dolor sit amet

### Chore

- Lorem ipsum dolor sit amet (#100)
- Lorem ipsum dolor sit amet

## v1.1.0 (2023-10-10)

### Feat

- Lorem ipsum dolor sit amet (#100)
- Lorem ipsum dolor sit amet

## v1.0.0 (2023-10-02)

### Feat

- Lorem ipsum dolor sit amet (#100)
- Lorem ipsum dolor sit amet

### Fix

- Lorem ipsum dolor sit amet (#100)
- Lorem ipsum dolor sit amet

### Test

- Lorem ipsum dolor sit amet (#100)
- Lorem ipsum dolor sit amet

### Style

- Lorem ipsum dolor sit amet (#100)
- Lorem ipsum dolor sit amet

### CI

- Lorem ipsum dolor sit amet (#100)
- Lorem ipsum dolor sit amet

### Refactor

- Lorem ipsum dolor sit amet (#100)
- Lorem ipsum dolor sit amet
"""


@pytest.fixture
def changelog(tmp_path, mocker):
    """Create a sample changelog file."""
    changelog = tmp_path / "CHANGELOG.md"
    if not changelog.exists():
        changelog.write_text(sample_changelog)

    mocker.patch("valentina.models.changelog.CHANGELOG_PATH", changelog)

    return changelog


def test_changelog_init(changelog, mock_bot):
    """Test the ChangelogParser init."""
    parser = ChangelogParser(mock_bot)
    assert parser.path == changelog
    assert parser.all_categories == [
        "feat",
        "fix",
        "docs",
        "refactor",
        "style",
        "test",
        "chore",
        "perf",
        "ci",
        "build",
    ]
    assert parser.exclude_categories == []
    assert parser.oldest_version == "0.0.1"
    assert parser.newest_version == "999.999.999"
    assert parser.full_changelog == sample_changelog
    assert parser.changelog_dict == {
        "1.0.0": {
            "ci": ["- Lorem ipsum dolor sit amet", "- Lorem ipsum dolor sit amet"],
            "date": "2023-10-02",
            "feat": [
                "- Lorem ipsum dolor sit amet",
                "- Lorem ipsum dolor sit amet",
            ],
            "fix": [
                "- Lorem ipsum dolor sit amet",
                "- Lorem ipsum dolor sit amet",
            ],
            "refactor": [
                "- Lorem ipsum dolor sit amet",
                "- Lorem ipsum dolor sit amet",
            ],
            "style": [
                "- Lorem ipsum dolor sit amet",
                "- Lorem ipsum dolor sit amet",
            ],
            "test": [
                "- Lorem ipsum dolor sit amet",
                "- Lorem ipsum dolor sit amet",
            ],
        },
        "1.1.0": {
            "date": "2023-10-10",
            "feat": [
                "- Lorem ipsum dolor sit amet",
                "- Lorem ipsum dolor sit amet",
            ],
        },
        "2.0.0": {
            "build": [
                "- Lorem ipsum dolor sit amet",
                "- Lorem ipsum dolor sit amet",
            ],
            "chore": [
                "- Lorem ipsum dolor sit amet",
                "- Lorem ipsum dolor sit amet",
            ],
            "ci": ["- Lorem ipsum dolor sit amet", "- Lorem ipsum dolor sit amet"],
            "date": "2023-11-04",
            "feat": [
                "- Lorem ipsum dolor sit amet",
                "- Lorem ipsum dolor sit amet",
            ],
            "fix": [
                "- Lorem ipsum dolor sit amet",
                "- Lorem ipsum dolor sit amet",
            ],
            "test": [
                "- Lorem ipsum dolor sit amet",
                "- Lorem ipsum dolor sit amet",
            ],
        },
    }


def test__clean_changelog(changelog, mock_bot):
    """Test the __clean_changelog method."""
    parser = ChangelogParser(
        mock_bot,
        exclude_categories=[
            "docs",
            "refactor",
            "style",
            "test",
            "chore",
            "perf",
            "ci",
            "build",
        ],
    )

    assert parser.changelog_dict == {
        "1.0.0": {
            "date": "2023-10-02",
            "feat": [
                "- Lorem ipsum dolor sit amet",
                "- Lorem ipsum dolor sit amet",
            ],
            "fix": [
                "- Lorem ipsum dolor sit amet",
                "- Lorem ipsum dolor sit amet",
            ],
        },
        "1.1.0": {
            "date": "2023-10-10",
            "feat": [
                "- Lorem ipsum dolor sit amet",
                "- Lorem ipsum dolor sit amet",
            ],
        },
        "2.0.0": {
            "date": "2023-11-04",
            "feat": [
                "- Lorem ipsum dolor sit amet",
                "- Lorem ipsum dolor sit amet",
            ],
            "fix": [
                "- Lorem ipsum dolor sit amet",
                "- Lorem ipsum dolor sit amet",
            ],
        },
    }


def test_changelog_list_of_versions(changelog, mock_bot):
    """Test the ChangelogParser list_of_versions property."""
    parser = ChangelogParser(mock_bot, oldest_version="1.1.0", newest_version="2.0.0")

    assert parser.list_of_versions() == ["2.0.0", "1.1.0"]


def test_changelog_has_updates(changelog, mock_bot):
    """Test the ChangelogParser has_updates method."""
    parser = ChangelogParser(mock_bot)
    assert parser.has_updates() is True

    parser = ChangelogParser(mock_bot, oldest_version="2.1.0", newest_version="2.0.0")
    print(parser.changelog_dict)
    assert parser.has_updates() is False


def test_changelog_get_embed(changelog, mock_bot):
    """Test the ChangelogParser get_embed method."""
    parser = ChangelogParser(mock_bot, oldest_version="1.1.0", newest_version="1.1.0")

    embed = parser.get_embed()
    assert (
        embed.description
        == """\
## Valentina Noir Changelog

### v1.1.0 (2023-10-10)

**Feat**

- Lorem ipsum dolor sit amet
- Lorem ipsum dolor sit amet


----
View the [full changelog on Github](https://github.com/natelandau/valentina/releases)
"""
    )


def test_changelog_get_embed_exclude_oldest(changelog, mock_bot):
    """Test the ChangelogParser get_embed method with exclude_oldest."""
    parser = ChangelogParser(
        mock_bot,
        oldest_version="1.1.0",
        newest_version="2.0.0",
        exclude_oldest_version=True,
    )

    embed = parser.get_embed()

    assert (
        embed.description
        == """\
## Valentina Noir Changelog

### v2.0.0 (2023-11-04)

**Feat**

- Lorem ipsum dolor sit amet
- Lorem ipsum dolor sit amet

**Fix**

- Lorem ipsum dolor sit amet
- Lorem ipsum dolor sit amet

**Test**

- Lorem ipsum dolor sit amet
- Lorem ipsum dolor sit amet

**Build**

- Lorem ipsum dolor sit amet
- Lorem ipsum dolor sit amet

**Ci**

- Lorem ipsum dolor sit amet
- Lorem ipsum dolor sit amet

**Chore**

- Lorem ipsum dolor sit amet
- Lorem ipsum dolor sit amet


----
View the [full changelog on Github](https://github.com/natelandau/valentina/releases)
"""
    )
