"""Lightweight quality-control flags for the parsed track.

The IMD workbook is hand-maintained and contains occasional data-entry errors —
most visibly single fixes with a corrupted latitude/longitude that place a storm
hundreds of km off its track (e.g. 1989-008's ``40.8°N`` fix). We don't alter the
source values; instead we *flag* them so users can filter or interpolate.

The check is deliberately conservative: a fix is flagged only when it is an
**isolated spike** — the implied translation speed both *into* it (from the
previous fix) and *out of* it (to the next fix) exceeds a physical cap. That
catches a single bad coordinate between two good ones without touching the good
fixes on either side, and essentially never fires on a genuinely fast storm.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# Tropical cyclones translate at up to ~30 kt (~55 km/h); extratropical
# transition can be faster. 110 km/h is well above any real motion, so anything
# beyond it over a 3-6 h step implies a corrupted position, not real movement.
MAX_TRANSLATION_KMH = 110.0


def _haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlam = np.radians(lon2 - lon1)
    a = np.sin(dphi / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dlam / 2) ** 2
    return 2 * r * np.arcsin(np.sqrt(a))


def flag_positions(observations: pd.DataFrame, max_kmh: float = MAX_TRANSLATION_KMH) -> pd.Series:
    """Return a boolean Series (aligned to ``observations``) flagging fixes whose
    position implies an impossible translation speed from *both* neighbours.

    Source coordinates are never modified — this only marks suspects.
    """
    suspect = pd.Series(False, index=observations.index)
    if observations.empty or not {"storm_id", "time", "lat", "lon"} <= set(observations.columns):
        return suspect

    for _, g in observations.groupby("storm_id", sort=False):
        if len(g) < 3:
            continue
        g = g.sort_values("time")
        lat, lon = g["lat"].to_numpy(dtype="float64"), g["lon"].to_numpy(dtype="float64")
        dt_h = np.diff(g["time"].to_numpy()).astype("timedelta64[s]").astype("float64") / 3600.0
        dist = _haversine_km(lat[:-1], lon[:-1], lat[1:], lon[1:])
        with np.errstate(invalid="ignore", divide="ignore"):
            speed = np.where(dt_h > 0, dist / dt_h, np.nan)  # speed[j] spans fix j -> j+1
        # interior fix j (1..n-2) is a spike when the segments on both sides are fast
        spike = (speed[:-1] > max_kmh) & (speed[1:] > max_kmh)
        suspect.loc[g.index[1:-1]] = spike

    return suspect
