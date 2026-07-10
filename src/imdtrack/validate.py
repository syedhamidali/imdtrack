"""Sanity-check a freshly-parsed dataset *before* it is allowed to replace the
committed one.

IMD maintains the workbook by hand, so a new upload can be malformed: a renamed
header we no longer detect, a corrupted sheet, an accidental truncation.  If we
blindly parsed and committed such a file we would clobber a good dataset with a
broken one.  The pipeline runs these checks and refuses to publish (the whole
job fails, leaving the previous data in place) when any of them trips.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import pandas as pd

# How much the record is allowed to *shrink* versus the currently-published one.
# IMD updates are append/revise, essentially never a big deletion, so a large
# drop almost always means a parse failure rather than real data loss.
SHRINK_TOLERANCE = 0.10  # new count must be >= 90% of the previous count

_REQUIRED_OBS_COLUMNS = {
    "storm_id", "year", "serial", "basin", "name", "time",
    "lat", "lon", "grade", "step",
}


class ValidationError(Exception):
    """Raised when a newly-parsed dataset fails a sanity check."""


def validate_frames(frames: dict) -> None:
    """Structural / plausibility checks on a parsed dataset. Raises on failure."""
    for name in ("observations", "remarks", "storms"):
        if name not in frames or not isinstance(frames[name], pd.DataFrame):
            raise ValidationError(f"missing or non-DataFrame frame: {name!r}")

    obs = frames["observations"]
    storms = frames["storms"]

    if obs.empty:
        raise ValidationError("observations frame is empty (nothing parsed)")
    if storms.empty:
        raise ValidationError("storms frame is empty (no storms summarised)")

    missing = _REQUIRED_OBS_COLUMNS - set(obs.columns)
    if missing:
        raise ValidationError(f"observations missing required columns: {sorted(missing)}")

    if not pd.api.types.is_datetime64_any_dtype(obs["time"]):
        raise ValidationError("observations['time'] is not datetime-typed")
    if obs["time"].isna().all():
        raise ValidationError("observations['time'] is entirely null")

    # Positions must be present and physically plausible for the North Indian Ocean.
    for col, lo, hi in (("lat", -90.0, 90.0), ("lon", 0.0, 180.0)):
        vals = pd.to_numeric(obs[col], errors="coerce")
        if vals.isna().all():
            raise ValidationError(f"observations['{col}'] is entirely null")
        bad_frac = ((vals < lo) | (vals > hi)).mean()
        if bad_frac > 0.01:
            raise ValidationError(
                f"{bad_frac:.1%} of '{col}' values fall outside [{lo}, {hi}] "
                "— column likely mis-detected"
            )

    yr_min, yr_max = int(obs["year"].min()), int(obs["year"].max())
    next_year = datetime.now(timezone.utc).year + 1
    if yr_min < 1800 or yr_max > next_year:
        raise ValidationError(f"implausible year range: {yr_min}-{yr_max}")


def validate_against_previous(frames: dict, previous) -> None:
    """Guard against silent shrinkage versus the currently-published manifest.

    ``previous`` is a :class:`imdtrack.store.Manifest` (or ``None`` to skip).
    """
    if previous is None:
        return

    n_obs = len(frames["observations"])
    n_storms = len(frames["storms"])

    floor_obs = previous.n_obs * (1 - SHRINK_TOLERANCE)
    if n_obs < floor_obs:
        raise ValidationError(
            f"new observation count ({n_obs}) is far below the published record "
            f"({previous.n_obs}); refusing to publish a shrinking dataset"
        )

    floor_storms = previous.n_storms * (1 - SHRINK_TOLERANCE)
    if n_storms < floor_storms:
        raise ValidationError(
            f"new storm count ({n_storms}) is far below the published record "
            f"({previous.n_storms}); refusing to publish a shrinking dataset"
        )

    if previous.year_max is not None:
        new_year_max = int(frames["observations"]["year"].max())
        if new_year_max < previous.year_max:
            raise ValidationError(
                f"new data's latest year ({new_year_max}) predates the published "
                f"record ({previous.year_max})"
            )
