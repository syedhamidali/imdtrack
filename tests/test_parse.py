"""Regression tests for the parser, built on small synthetic workbooks.

These lock in the tricky real-world behaviours: forward-filled serials, name
bleed between storms, free-text remark rows, messy numeric cells, and the
alternate 16-column (split-date) sheet layout.
"""

from datetime import datetime

import openpyxl
import pytest

from imdtrack import _schema as S
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

HEADER_16 = [
    "Serial Number of system during year",
    "Basin of origin",
    "Name",
    "Date(DD/MM/YYYY)",
    "Time (UTC)",
    "Latitude (lat)",
    "longitude  (Long)",
    'CI No [or "T. No"]',
    "Estimated Central Pressure (hPa)",
    "Maximum Sustained Surface Wind (kt) ",
    "Pressure Drop (hPa)",
    "Grade (text)",
    "Outermost closed isobar (hPa)",
    "DD",
    "MM",
    "YYYY",
]


def _write(tmp_path, sheets):
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for name, rows in sheets.items():
        ws = wb.create_sheet(title=name)
        for row in rows:
            ws.append(row)
    path = tmp_path / "wb.xlsx"
    wb.save(path)
    return path


def test_merged_date_cell_is_forward_filled(tmp_path):
    """The Date column is a merged cell: it is populated only on the first row of
    each day and ``None`` on the 3-hourly rows below. All those fixes must still
    be captured (regression for dropping ~7/8 of every storm's track)."""
    day1 = datetime(2021, 5, 14)
    day2 = datetime(2021, 5, 15)
    rows = [
        HEADER_14,
        # Serial + date only on the first row of the storm/day (merged-cell effect)
        [2, "AS", "TAUKTAE", day1, "0300", 10.5, 72.3, 1.5, "997", "25", "3", "D", "", ""],
        [None, "AS", "TAUKTAE", None, "0600", 11.0, 72.5, 1.5, "996", "25", "4", "D", "", ""],
        [None, "AS", "TAUKTAE", None, "0900", 11.5, 72.5, 2.0, "995", "30", "5", "D", "", ""],
        [None, "AS", "TAUKTAE", None, "1200", 11.6, 72.6, 2.0, "995", "30", "6", "DD", "", ""],
        # Next day: date reappears on its first row, then None again
        [None, "AS", "TAUKTAE", day2, "0000", 12.7, 72.5, 2.5, "992", "40", "8", "CS", "", ""],
        [None, "AS", "TAUKTAE", None, "0300", 12.8, 72.5, 2.5, "992", "40", "8", "CS", "", ""],
    ]
    res = parse_workbook(_write(tmp_path, {"2021": rows}))
    obs = res["observations"]
    assert len(obs) == 6  # not 2 — the merged-date continuation rows are kept
    assert obs["storm_id"].nunique() == 1
    assert list(obs["step"]) == [0, 1, 2, 3, 4, 5]
    # times are reconstructed from the forward-filled date + each row's HHMM
    assert obs["time"].iloc[1] == datetime(2021, 5, 14, 6, 0)
    assert obs["time"].iloc[5] == datetime(2021, 5, 15, 3, 0)


def test_serial_ffill_and_grouping(tmp_path):
    d = datetime(2020, 5, 16)
    rows = [
        HEADER_14,
        [1, "BOB", "AMPHAN", d, "0000", 10.4, 87.0, 1.5, "1000", "25", "3", "D", "", ""],
        [None, "BOB", "AMPHAN", d, "0300", 10.7, 86.5, 1.5, "1000", "25", "3", "D", "", ""],
        [None, "BOB", "AMPHAN", d, "0600", 10.9, 86.3, 2.0, "998", "30", "5", "DD", "", ""],
    ]
    res = parse_workbook(_write(tmp_path, {"2020": rows}))
    obs = res["observations"]
    assert len(obs) == 3
    assert obs["storm_id"].nunique() == 1
    assert obs["storm_id"].iloc[0] == "2020-001"
    assert list(obs["step"]) == [0, 1, 2]
    assert obs["name"].unique().tolist() == ["AMPHAN"]


def test_name_does_not_bleed_across_storms(tmp_path):
    d = datetime(2020, 5, 16)
    rows = [
        HEADER_14,
        [1, "BOB", "AMPHAN", d, "0000", 10.4, 87.0, 1.5, "1000", "25", "3", "D", "", ""],
        [None, "BOB", "AMPHAN", d, "0300", 10.7, 86.5, 1.5, "1000", "25", "3", "D", "", ""],
        [],  # blank separator
        [
            2,
            "ARB",
            None,
            datetime(2020, 5, 29),
            "0900",
            15.0,
            68.0,
            1.5,
            "1000",
            "25",
            "3",
            "D",
            "",
            "",
        ],
    ]
    res = parse_workbook(_write(tmp_path, {"2020": rows}))
    storms = res["storms"].set_index("storm_id")
    assert storms.loc["2020-001", "name"] == "AMPHAN"
    assert storms.loc["2020-002", "name"] is None or storms.loc["2020-002", "name"] != "AMPHAN"


def test_remark_rows_captured_not_dropped(tmp_path):
    d = datetime(2020, 5, 20)
    remark = "Crossed West Bengal coast near Sagar Island around 1000 UTC."
    rows = [
        HEADER_14,
        [1, "BOB", "AMPHAN", d, "0900", 21.4, 88.1, 5.0, "960", "90", "42", "ESCS", "", ""],
        [None, "BOB", "AMPHAN", d, remark, None, None, None, None, None, None, None, "", ""],
        [None, "BOB", "AMPHAN", d, "1200", 21.9, 88.4, "-", "957", "85", "36", "VSCS", "", ""],
    ]
    res = parse_workbook(_write(tmp_path, {"2020": rows}))
    assert len(res["observations"]) == 2  # remark row is not a track fix
    assert len(res["remarks"]) == 1
    assert remark in res["remarks"]["remark"].iloc[0]
    assert res["remarks"]["storm_id"].iloc[0] == "2020-001"


def test_messy_numeric_and_time_coercion(tmp_path):
    d = datetime(1992, 6, 17)
    rows = [
        HEADER_14,
        # time '0' -> 00:00, ECP as float, wind as str, pressure_drop '-' -> NaN
        [2, "BOB", None, d, 0, "19.0", 89.0, "-", 992, "30", "-", "D", "994", "5.0"],
    ]
    res = parse_workbook(_write(tmp_path, {"1992": rows}))
    o = res["observations"].iloc[0]
    assert o["time"] == datetime(1992, 6, 17, 0, 0)
    assert o["lat"] == 19.0 and o["pressure"] == 992.0 and o["wind"] == 30.0
    assert o["ci_no"] != o["ci_no"]  # '-' -> NaN


def test_16_column_split_date_layout(tmp_path):
    d = datetime(2025, 5, 24)
    rows = [
        HEADER_16,
        [1, "AS", None, d, "0000", 17.0, 73.0, 1.5, 998, 25, 3, "D", None, 24, 5, 2025],
        [None, "AS", None, d, "0300", 17.0, 73.2, 1.5, 998, 25, 3, "D", None, 24, 5, 2025],
    ]
    res = parse_workbook(_write(tmp_path, {"2025": rows}))
    obs = res["observations"]
    assert len(obs) == 2
    assert obs["basin"].iloc[0] == "ARB"  # "AS" normalized to ARB
    assert obs["oci_diameter"].isna().all()  # no diameter col in this layout
    assert obs["time"].iloc[1] == datetime(2025, 5, 24, 3, 0)


def test_note_row_above_header(tmp_path):
    rows = [
        ["The best track parameters are tentative and subject to finalisation."],
        HEADER_16,
        [
            1,
            "BOB",
            None,
            datetime(2026, 1, 7),
            "0300",
            4.8,
            88.2,
            1.5,
            1008,
            25,
            3,
            "D",
            None,
            7,
            1,
            2026,
        ],
    ]
    res = parse_workbook(_write(tmp_path, {"2026": rows}))
    assert len(res["observations"]) == 1


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("BOB", "BOB"),
        ("AS", "ARB"),
        ("arb", "ARB"),
        ("Land", "LAND"),
        ("junk", None),
    ],
)
def test_basin_normalization(raw, expected):
    assert S.normalize_basin(raw) == expected


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("NIVAR’", "NIVAR"),
        ("-", None),
        ("--", None),
        ("SYSTEM CROSSED COAST NEAR X", None),
        ("AMPHAN", "AMPHAN"),
    ],
)
def test_name_normalization(raw, expected):
    assert S.normalize_name(raw) == expected


def test_grade_is_ordered_category(tmp_path):
    d = datetime(2020, 5, 16)
    rows = [
        HEADER_14,
        [1, "BOB", "X", d, "0000", 10.0, 87.0, 1.5, "1000", "25", "3", "D", "", ""],
        [None, "BOB", "X", d, "0300", 10.0, 87.0, 6.5, "920", "130", "84", "SuCS", "", ""],
    ]
    res = parse_workbook(_write(tmp_path, {"2020": rows}))
    grade = res["observations"]["grade"]
    assert grade.cat.ordered
    assert grade.max() == "SuCS"
    assert res["storms"]["peak_grade"].iloc[0] == "SuCS"
