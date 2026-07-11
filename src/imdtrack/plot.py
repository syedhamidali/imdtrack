"""Cartopy map plotting for cyclone tracks (optional — needs the ``plot`` extra).

Inspired by `tropycal <https://tropycal.github.io/>`_'s storm plots, but coloured
by **IMD grade** rather than Saffir–Simpson. Cartopy is imported lazily inside
the functions, so ``import imdtrack`` works even where cartopy isn't installed;
call these and you'll get a clear message pointing at ``pip install imdtrack[plot]``.
"""

from __future__ import annotations

from ._schema import GRADE_LONG, GRADE_ORDER

# IMD grade -> colour, a weak→intense ramp (matches the docs examples).
GRADE_COLORS = {
    "D": "#6baed6",
    "DD": "#74c476",
    "CS": "#fed976",
    "SCS": "#feb24c",
    "VSCS": "#fd8d3c",
    "ESCS": "#e31a1c",
    "SuCS": "#800026",
}
BASIN_COLORS = {"BOB": "#2a78d6", "ARB": "#eb6834", "LAND": "#b8b6ae"}


def _cartopy():
    try:
        import cartopy.crs as ccrs
        import cartopy.feature as cfeature
        import matplotlib.pyplot as plt
    except ImportError as exc:  # pragma: no cover - exercised only without cartopy
        raise ImportError(
            "Map plotting needs cartopy and matplotlib. Install them with:\n"
            "    pip install 'imdtrack[plot]'"
        ) from exc
    return ccrs, cfeature, plt


def _basemap(ax, extent, ccrs, cfeature):
    ax.set_extent(extent, crs=ccrs.PlateCarree())
    ax.add_feature(cfeature.OCEAN.with_scale("50m"), facecolor="#eaf3fb")
    ax.add_feature(cfeature.LAND.with_scale("50m"), facecolor="#f4f1ea")
    ax.add_feature(cfeature.COASTLINE.with_scale("50m"), linewidth=0.5, edgecolor="#8a8a8a")
    ax.add_feature(cfeature.BORDERS.with_scale("50m"), linewidth=0.3, edgecolor="#bcbcbc")
    gl = ax.gridlines(draw_labels=True, linewidth=0.4, color="0.85", alpha=0.7)
    gl.top_labels = gl.right_labels = False


def _extent(lon, lat, pad):
    return [
        float(lon.min()) - pad,
        float(lon.max()) + pad,
        float(lat.min()) - pad,
        float(lat.max()) + pad,
    ]


def _new_fig(extent, base, plt, ccrs):
    """A figure sized to the map's aspect so a fixed-aspect GeoAxes fills it."""
    w = max(extent[1] - extent[0], 1e-6)
    h = max(extent[3] - extent[2], 1e-6)
    figh = max(3.5, min(10.5, base * (h / w) + 1.0))
    fig = plt.figure(figsize=(base, figh), layout="constrained")
    ax = fig.add_subplot(1, 1, 1, projection=ccrs.PlateCarree())
    return fig, ax


def plot_track(track, ax=None, color="grade", extent=None, pad=2.0, title=None):
    """Plot one storm's track on a cartopy map.

    Parameters
    ----------
    track : DataFrame for a single storm (e.g. ``bt.storm(id)``) with ``lat``,
            ``lon``, ``time`` and — for colouring — ``grade`` or ``wind``.
    color : ``"grade"`` (IMD category, discrete legend) or ``"wind"`` (colorbar).
    ax    : an existing cartopy GeoAxes; created if omitted.
    """
    ccrs, cfeature, plt = _cartopy()
    from matplotlib.lines import Line2D

    t = track.sort_values("time")
    ext = extent or _extent(t["lon"], t["lat"], pad)
    if ax is None:
        _, ax = _new_fig(ext, 7.0, plt, ccrs)
    _basemap(ax, ext, ccrs, cfeature)

    pc = ccrs.PlateCarree()
    ax.plot(t["lon"], t["lat"], color="0.45", linewidth=1.0, transform=pc, zorder=2)
    if color == "wind":
        sc = ax.scatter(
            t["lon"],
            t["lat"],
            c=t["wind"],
            cmap="viridis",
            s=46,
            edgecolor="white",
            linewidth=0.4,
            transform=pc,
            zorder=3,
        )
        cb = ax.figure.colorbar(sc, ax=ax, shrink=0.7, pad=0.02)
        cb.set_label("Max sustained wind (kt)")
    else:
        colors = [GRADE_COLORS.get(g, "#999999") for g in t["grade"].astype(object)]
        ax.scatter(
            t["lon"],
            t["lat"],
            c=colors,
            s=46,
            edgecolor="white",
            linewidth=0.4,
            transform=pc,
            zorder=3,
        )
        present = [g for g in GRADE_ORDER if g in set(t["grade"].dropna())]
        handles = [
            Line2D(
                [],
                [],
                marker="o",
                linestyle="",
                markerfacecolor=GRADE_COLORS[g],
                markeredgecolor="white",
                label=f"{g} · {GRADE_LONG[g]}",
            )
            for g in present
        ]
        if handles:
            ax.legend(handles=handles, title="IMD grade", loc="upper right", fontsize=8)
    if title:
        ax.set_title(title)
    return ax


def plot_tracks(
    observations, ax=None, color="basin", extent=None, pad=1.0, linewidth=0.8, alpha=0.5, title=None
):
    """Plot many tracks on one map (e.g. ``bt.observations``), coloured by
    ``"basin"`` (default) or by each storm's peak ``"grade"``."""
    ccrs, cfeature, plt = _cartopy()
    from matplotlib.lines import Line2D

    obs = observations
    ext = extent or _extent(obs["lon"], obs["lat"], pad)
    if ax is None:
        _, ax = _new_fig(ext, 9.0, plt, ccrs)
    _basemap(ax, ext, ccrs, cfeature)

    pc = ccrs.PlateCarree()
    peak = None
    if color == "grade":
        peak = obs.groupby("storm_id")["grade"].max()
    for sid, g in obs.groupby("storm_id", sort=False):
        if color == "grade":
            c = GRADE_COLORS.get(str(peak.get(sid)), "#999999")
        else:
            c = BASIN_COLORS.get(str(g["basin"].iloc[0]), "#b8b6ae")
        ax.plot(
            g["lon"], g["lat"], color=c, linewidth=linewidth, alpha=alpha, transform=pc, zorder=2
        )

    if color == "basin":
        keys = [b for b in ("BOB", "ARB", "LAND") if b in set(obs["basin"].astype(object))]
        handles = [Line2D([], [], color=BASIN_COLORS[b], linewidth=2, label=b) for b in keys]
    else:
        keys = [g for g in GRADE_ORDER if peak is not None and g in set(peak.dropna())]
        handles = [Line2D([], [], color=GRADE_COLORS[g], linewidth=2, label=g) for g in keys]
    if handles:
        ax.legend(
            handles=handles,
            loc="upper right",
            fontsize=8,
            title="Sub-basin" if color == "basin" else "Peak grade",
        )
    if title:
        ax.set_title(title)
    return ax
