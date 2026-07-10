"""Tests for the end-user load paths that don't hit the network.

`imd.load()` normally downloads the published dataset from GitHub. Setting
``IMDTRACK_DATA_DIR`` makes it read a local committed dataset instead — the same
mechanism the docs build and offline users rely on. These tests exercise that
path end to end without any HTTP.
"""

from datetime import datetime

import openpyxl

import imdtrack as imd
from imdtrack import store
from imdtrack.parse import parse_workbook

HEADER_14 = [
    "Serial Number of system during year",
    "Basin of origin",
    "Name",
    "Date(DD-MM-YYYY)",
    "Time (UTC)",
    "Latitude (lat.)",
    "Longitude (lon.)",
    'CI No [or "T. No"]',
    "Estimated Central Pressure (hPa)",
    "Maximum Sustained Surface Wind (kt) ",
    "Pressure Drop (hPa)",
    "Grade (text)",
    "Outermost closed isobar (hPa)",
    "Diameter/Size of outermost closed isobar",
]


def _write_dataset(tmp_path):
    d = datetime(2020, 5, 16)
    rows = [
        HEADER_14,
        [1, "BOB", "AMPHAN", d, "0000", 10.4, 87.0, 1.5, "1000", "25", "3", "D", "", ""],
        [None, "BOB", "AMPHAN", d, "0300", 10.7, 86.5, 2.0, "998", "30", "5", "DD", "", ""],
        [None, "BOB", "AMPHAN", d, "0600", 11.0, 86.0, 6.5, "920", "130", "84", "SuCS", "", ""],
    ]
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    ws = wb.create_sheet(title="2020")
    for row in rows:
        ws.append(row)
    xlsx = tmp_path / "wb.xlsx"
    wb.save(xlsx)

    frames = parse_workbook(xlsx)
    data_dir = tmp_path / "data"
    store.write_dataset(frames, data_dir, source_url="http://x", source_sha256="deadbeef")
    return data_dir


def test_load_from_local_data_dir(tmp_path, monkeypatch):
    data_dir = _write_dataset(tmp_path)
    monkeypatch.setenv("IMDTRACK_DATA_DIR", str(data_dir))
    # Point the cache elsewhere so nothing leaks in from a real user cache.
    monkeypatch.setenv("IMDTRACK_CACHE", str(tmp_path / "cache"))

    bt = imd.load()  # default source="github", but IMDTRACK_DATA_DIR short-circuits it

    assert len(bt.storms) == 1
    assert bt.storms["storm_id"].iloc[0] == "2020-001"
    assert bt.sha256 == "deadbeef"
    # ordered categorical restored on read
    assert bt.observations["grade"].cat.ordered
    assert bt.storm("2020-001")["wind"].max() == 130.0


def test_load_local_to_xarray(tmp_path, monkeypatch):
    data_dir = _write_dataset(tmp_path)
    monkeypatch.setenv("IMDTRACK_DATA_DIR", str(data_dir))
    monkeypatch.setenv("IMDTRACK_CACHE", str(tmp_path / "cache"))

    ds = imd.load().to_xarray()
    assert dict(ds.sizes) == {"storm": 1, "step": 3}
    assert float(ds.sel(storm="2020-001")["wind"].max()) == 130.0
