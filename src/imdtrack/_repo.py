"""Where the *published* dataset lives.

The parsed dataset is committed into this GitHub repository under ``data/`` and
refreshed by a scheduled GitHub Action (see ``pipeline.py`` and
``.github/workflows/update-dataset.yml``).  End users download those parquet
files straight from the repo's raw endpoint instead of parsing the IMD workbook
themselves.

The repo slug is baked in below but can be overridden with the ``IMDTRACK_REPO``
/ ``IMDTRACK_BRANCH`` environment variables (handy for forks and CI).
"""

from __future__ import annotations

import os

# ``owner/name`` of the GitHub repository hosting the committed dataset.
DEFAULT_REPO = "syedhamidali/imdtrack"
DEFAULT_BRANCH = "main"

# Directory (within the repo) that holds the committed parquet + manifest.
DATA_DIR_NAME = "data"

_PLACEHOLDER = "OWNER/REPO"

RAW_HOST = "https://raw.githubusercontent.com"


def repo_slug() -> str:
    return os.environ.get("IMDTRACK_REPO", DEFAULT_REPO).strip("/")


def repo_branch() -> str:
    return os.environ.get("IMDTRACK_BRANCH", DEFAULT_BRANCH)


def is_configured() -> bool:
    """True once a real repo slug (not the placeholder) is available."""
    return repo_slug() != _PLACEHOLDER


def raw_url(filename: str) -> str:
    """Raw-content URL for ``data/<filename>`` in the published repo."""
    if not is_configured():
        raise RuntimeError(
            "imdtrack: no GitHub repo configured for the published dataset.\n"
            "Set the IMDTRACK_REPO environment variable (e.g. "
            "IMDTRACK_REPO=myuser/imdtrack) or edit DEFAULT_REPO in "
            "imdtrack/_repo.py, or call load(source='imd') to parse the IMD "
            "workbook directly instead."
        )
    return f"{RAW_HOST}/{repo_slug()}/{repo_branch()}/{DATA_DIR_NAME}/{filename}"
