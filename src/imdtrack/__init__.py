"""imdtrack - IMD RSMC New Delhi cyclone best-track data as pandas / xarray.

Quick start
-----------
>>> import imdtrack as imd
>>> bt = imd.load()                 # download the pre-parsed dataset from GitHub
>>> df = bt.observations            # tidy pandas DataFrame, one row per fix
>>> ds = bt.to_xarray()             # (storm, step) xarray.Dataset
>>> bt = imd.load(update=True)      # re-fetch only if the repo published new data

The published dataset is rebuilt from the IMD workbook by a scheduled GitHub
Action (see :mod:`imdtrack.pipeline`); ``load(source="imd")`` parses the raw
workbook directly instead.
"""

from __future__ import annotations

from ._schema import GRADE_LONG, GRADE_ORDER, VALID_BASINS
from .core import BestTracks, load, update
from .fetch import DEFAULT_URL, fetch_data_from_repo, fetch_workbook
from .parse import parse_workbook
from .pipeline import build

__all__ = [
    "load",
    "update",
    "build",
    "BestTracks",
    "parse_workbook",
    "fetch_workbook",
    "fetch_data_from_repo",
    "DEFAULT_URL",
    "GRADE_ORDER",
    "GRADE_LONG",
    "VALID_BASINS",
]

__version__ = "0.2.1"
