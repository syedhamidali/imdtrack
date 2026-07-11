"""Tests for the non-destructive position quality-control flag."""

import pandas as pd

from imdtrack import BestTracks
from imdtrack import _schema as S
from imdtrack.parse import _summarize_storms
from imdtrack.qc import flag_positions


def _track(coords, sid="2020-001"):
    t0 = pd.Timestamp("2020-05-16")
    return pd.DataFrame(
        {
            "storm_id": sid,
            "time": [t0 + pd.Timedelta(hours=3 * i) for i in range(len(coords))],
            "lat": [c[0] for c in coords],
            "lon": [c[1] for c in coords],
        }
    )


def test_flags_isolated_position_spike():
    # one bad middle fix jumps ~20° away and back
    obs = _track([(10, 80), (10.3, 80.2), (30, 60), (10.6, 80.6), (10.9, 80.8)])
    assert list(flag_positions(obs)) == [False, False, True, False, False]


def test_no_flag_on_a_normal_track():
    obs = _track([(10, 80), (10.3, 80.2), (10.6, 80.4), (10.9, 80.6)])
    assert not flag_positions(obs).any()


def test_short_track_never_flagged():
    obs = _track([(10, 80), (30, 60)])  # only 2 fixes -> no interior fix to bracket
    assert not flag_positions(obs).any()


def _bestracks_with_spike():
    obs = pd.DataFrame(
        {
            "storm_id": ["2020-001"] * 3,
            "year": [2020] * 3,
            "serial": [1] * 3,
            "name": [None] * 3,
            "basin": ["BOB"] * 3,
            "time": pd.to_datetime(["2020-05-16 00:00", "2020-05-16 03:00", "2020-05-16 06:00"]),
            "lat": [10.0, 30.0, 10.6],
            "lon": [80.0, 60.0, 80.4],
            "wind": [25.0, 25.0, 25.0],
            "pressure": [1000.0, 1000.0, 1000.0],
            "grade": pd.Categorical(["D", "D", "D"], categories=S.GRADE_ORDER, ordered=True),
            "step": [0, 1, 2],
            "pos_suspect": [False, True, False],
        }
    )
    return BestTracks(obs, pd.DataFrame(), _summarize_storms(obs))


def test_clean_drop_removes_flagged_fix():
    c = _bestracks_with_spike().clean(how="drop")
    assert len(c.observations) == 2
    assert not c.observations["pos_suspect"].any()
    assert list(c.observations["step"]) == [0, 1]  # renumbered


def test_clean_mask_nulls_position_but_keeps_row():
    m = _bestracks_with_spike().clean(how="mask")
    assert len(m.observations) == 3
    bad = m.observations[m.observations["pos_suspect"]]
    assert bad["lat"].isna().all() and bad["lon"].isna().all()
