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


@pytest.mark.parametrize(
    "lat_raw,lon_raw,expected",
    [
        ("8.5/96.5", "8.5/96.5", (8.5, 96.5)),  # packed in both cells (2013 LEHAR)
        ("12.0", "88.0", (12.0, 88.0)),  # normal separate cells
        ("10.0/95.0", None, (10.0, 95.0)),  # packed only in the lat cell
    ],
)
def test_parse_latlon(lat_raw, lon_raw, expected):
    assert S.parse_latlon(lat_raw, lon_raw) == expected


def test_latlon_pair_string_is_split(tmp_path):
    """Some rows pack 'lat/lon' into one string in both coordinate cells; without
    splitting, lon wrongly equals lat (2013 LEHAR/MADI tracked at ~8°E instead
    of ~96°E)."""
    rows = [
        HEADER_14,
        [
            9,
            "BOB",
            "LEHAR",
            datetime(2013, 11, 23),
            "1200",
            "8.5/96.5",
            "8.5/96.5",
            1.5,
            "1004",
            "25",
            "3",
            "D",
            "",
            "",
        ],
        [
            None,
            "BOB",
            "LEHAR",
            None,
            "1800",
            "9.0/96.0",
            "9.0/96.0",
            2,
            "1002",
            "30",
            "5",
            "DD",
            "",
            "",
        ],
    ]
    res = parse_workbook(_write(tmp_path, {"2013": rows}))
    o = res["observations"]
    assert len(o) == 2
    assert o["lat"].iloc[0] == 8.5 and o["lon"].iloc[0] == 96.5
    assert o["lon"].iloc[1] == 96.0


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("16-06-2008", datetime(2008, 6, 16)),
        ("01/10/2025", datetime(2025, 10, 1)),
        ("24.5.2021", datetime(2021, 5, 24)),
        (datetime(2020, 5, 16, 3, 0), datetime(2020, 5, 16)),
        ("garbage", None),
        (None, None),
    ],
)
def test_parse_date(raw, expected):
    assert S.parse_date(raw) == expected


def test_text_string_dates_are_parsed(tmp_path):
    """Some storms store the date as day-first text ("16-06-2008") rather than a
    datetime; without parsing it, every fix in the storm is dropped."""
    rows = [
        HEADER_14,
        [3, "BOB", None, "16-06-2008", "0300", 21.5, 90.0, 1.5, "990", "30", "5", "DD", "", ""],
        [None, "BOB", None, None, "0900", 21.5, 89.5, 1.5, "990", "30", "5", "DD", "", ""],
        [None, "BOB", None, "17-06-2008", "0300", 23.0, 88.5, 1.5, "992", "25", "3", "D", "", ""],
    ]
    res = parse_workbook(_write(tmp_path, {"2008": rows}))
    obs = res["observations"]
    assert len(obs) == 3
    assert obs["time"].iloc[0] == datetime(2008, 6, 16, 3, 0)
    assert obs["time"].iloc[2] == datetime(2008, 6, 17, 3, 0)


def test_per_basin_serial_does_not_merge_storms(tmp_path):
    """IMD restarts the serial number per basin in older years (ARB 1,2 then
    BOB 1,2). Keying storms on (year, serial) would merge ARB #1 with BOB #1;
    each must stay a separate storm with a unique id."""
    d1, d2 = datetime(1993, 11, 12), datetime(1993, 12, 1)
    rows = [
        HEADER_14,
        [1, "ARB", None, d1, "0300", 15.0, 68.0, 1.5, "1000", "25", "3", "D", "", ""],
        [
            2,
            "ARB",
            None,
            datetime(1993, 11, 8),
            "0300",
            12.0,
            66.0,
            1.5,
            "1000",
            "25",
            "3",
            "D",
            "",
            "",
        ],
        [],  # blank separator between basins
        [1, "BOB", None, d2, "0600", 12.0, 88.0, 2.0, "990", "90", "42", "ESCS", "", ""],
        [
            2,
            "BOB",
            None,
            datetime(1993, 12, 19),
            "0000",
            14.0,
            90.0,
            1.5,
            "998",
            "30",
            "5",
            "DD",
            "",
            "",
        ],
    ]
    res = parse_workbook(_write(tmp_path, {"1993": rows}))
    storms = res["storms"]
    assert len(storms) == 4  # not 2 — ARB #1/#2 and BOB #1/#2 are distinct
    assert storms["storm_id"].tolist() == ["1993-001", "1993-002", "1993-003", "1993-004"]
    by_id = storms.set_index("storm_id")
    assert by_id.loc["1993-001", "basin"] == "ARB"
    assert by_id.loc["1993-003", "basin"] == "BOB"
    assert by_id.loc["1993-003", "peak_grade"] == "ESCS"


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
