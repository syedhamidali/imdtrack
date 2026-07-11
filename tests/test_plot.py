"""Smoke tests for the optional cartopy plotting (skipped where cartopy absent)."""

import pandas as pd
import pytest

pytest.importorskip("cartopy")

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from imdtrack import _schema as S  # noqa: E402
from imdtrack.plot import plot_track, plot_tracks  # noqa: E402


def _track():
    return pd.DataFrame(
        {
            "storm_id": ["x"] * 4,
            "basin": ["BOB"] * 4,
            "time": pd.to_datetime([f"2020-05-1{i} 00:00" for i in range(4)]),
            "lat": [10.0, 12.0, 14.0, 16.0],
            "lon": [88.0, 87.0, 86.0, 85.0],
            "wind": [25.0, 45.0, 65.0, 90.0],
            "grade": pd.Categorical(
                ["D", "CS", "VSCS", "ESCS"], categories=S.GRADE_ORDER, ordered=True
            ),
        }
    )


def test_plot_track_by_grade_returns_geoaxes():
    ax = plot_track(_track(), color="grade")
    assert ax is not None and hasattr(ax, "projection")
    plt.close("all")


def test_plot_track_by_wind():
    ax = plot_track(_track(), color="wind", title="test")
    assert ax.get_title() == "test"
    plt.close("all")


def test_plot_tracks_multiple():
    ax = plot_tracks(_track(), color="basin")
    assert ax is not None
    plt.close("all")
