"""Publication-quality Cartopy plots for IMD cyclone tracks (optional ``plot`` extra).

Inspired by `tropycal <https://tropycal.github.io/>`_ but coloured by **IMD grade**
rather than Saffir–Simpson. Cartopy/matplotlib are imported lazily inside the
functions, so ``import imdtrack`` works even without them — calling a plot then
raises a clear ``pip install imdtrack[plot]`` message.

Examples
--------
>>> import imdtrack as imd
>>> bt = imd.load()
>>> imd.plot_track(bt.storm("tauktae"), color="grade")      # by IMD category
>>> imd.plot_track(bt.storm("2020-001"), color="wind")      # by wind speed
>>> imd.plot_tracks(bt.observations, color="basin")         # every track
"""

from __future__ import annotations

from ._schema import GRADE_LONG, GRADE_ORDER

# IMD grade -> colour: a calm→intense ramp (blue depression → dark-red super cyclone).
GRADE_COLORS = {
    "D": "#8ecae6",
    "DD": "#52b788",
    "CS": "#ffd166",
    "SCS": "#f8961e",
    "VSCS": "#f3722c",
    "ESCS": "#d62828",
    "SuCS": "#6a040f",
}
BASIN_COLORS = {"BOB": "#2a78d6", "ARB": "#eb6834", "LAND": "#9aa0a6"}

# chrome
_OCEAN = "#eaf2fb"
_LAND = "#f1eee7"
_COAST = "#7d7d7d"
_BORDER = "#c4c4c4"
_INK = "#1a1a1a"


def _cartopy():
    try:
        import cartopy.crs as ccrs
        import cartopy.feature as cfeature
        import matplotlib.pyplot as plt
    except ImportError as exc:  # pragma: no cover - only hit without cartopy
        raise ImportError(
            "Map plotting needs cartopy and matplotlib. Install them with:\n"
            "    pip install 'imdtrack[plot]'"
        ) from exc
    return ccrs, cfeature, plt


def _basemap(ax, extent, ccrs, cfeature):
    ax.set_extent(extent, crs=ccrs.PlateCarree())
    ax.add_feature(cfeature.OCEAN.with_scale("50m"), facecolor=_OCEAN, zorder=0)
    ax.add_feature(cfeature.LAND.with_scale("50m"), facecolor=_LAND, zorder=0)
    ax.add_feature(cfeature.COASTLINE.with_scale("50m"), linewidth=0.6, edgecolor=_COAST, zorder=1)
    ax.add_feature(cfeature.BORDERS.with_scale("50m"), linewidth=0.4, edgecolor=_BORDER, zorder=1)
    gl = ax.gridlines(
        draw_labels=True, linewidth=0.4, color="#c9c9c9", alpha=0.7, linestyle=(0, (1, 3))
    )
    gl.top_labels = gl.right_labels = False
    gl.xlabel_style = gl.ylabel_style = {"size": 8, "color": "#666"}


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
    figh = max(3.5, min(11.0, base * (h / w) + 1.2))
    fig = plt.figure(figsize=(base, figh), layout="constrained")
    ax = fig.add_subplot(1, 1, 1, projection=ccrs.PlateCarree())
    return fig, ax


def _peak_idx(t):
    return t["wind"].idxmax() if t["wind"].notna().any() else None


def _auto_title(t):
    """A two-line title from the storm's own data, e.g.::

    Cyclone Tauktae (2021)
    Peak: ESCS · 100 kt

    Defensive: works on any track frame, falling back gracefully when the name,
    id, year, or intensity columns are missing.
    """
    year = int(t["time"].dt.year.iloc[0]) if "time" in t.columns else None
    name = None
    if "name" in t.columns and t["name"].notna().any():
        name = str(t["name"].dropna().iloc[0]).title()
    if name:
        label = f"Cyclone {name}"
    elif "storm_id" in t.columns:
        label = str(t["storm_id"].iloc[0])
    else:
        label = "Cyclone track"
    head = f"{label} ({year})" if year else label
    if "wind" in t.columns and t["wind"].notna().any():
        grade = t["grade"].max() if "grade" in t.columns else float("nan")
        gtxt = f"{grade} · " if grade == grade else ""  # skip if NaN
        head += f"\nPeak: {gtxt}{t['wind'].max():.0f} kt"
    return head


def _halo():
    import matplotlib.patheffects as pe

    return [pe.withStroke(linewidth=2.4, foreground="white")]


def _colored_line(ax, t, color, cmap, pc):
    """Draw the track as intensity-coloured segments; return a mappable or None."""
    import numpy as np
    from matplotlib.collections import LineCollection

    pts = np.column_stack([t["lon"].to_numpy(), t["lat"].to_numpy()]).reshape(-1, 1, 2)
    if len(pts) < 2:
        ax.plot(t["lon"], t["lat"], color="0.5", transform=pc, zorder=3)
        return None
    segs = np.concatenate([pts[:-1], pts[1:]], axis=1)

    # a white casing under the coloured line makes it read cleanly over coastlines
    casing = LineCollection(
        segs, colors="white", linewidths=5.2, transform=pc, zorder=3, capstyle="round"
    )
    ax.add_collection(casing)

    if color == "wind":
        from matplotlib.colors import Normalize

        w = t["wind"].to_numpy(dtype="float64")
        finite = w[np.isfinite(w)]
        vmin = float(finite.min()) if finite.size else 20.0
        vmax = float(finite.max()) if finite.size else 120.0
        lc = LineCollection(
            segs,
            cmap=cmap,
            norm=Normalize(vmin, vmax),
            transform=pc,
            linewidths=3.4,
            zorder=4,
            capstyle="round",
        )
        lc.set_array(w[:-1])
        ax.add_collection(lc)
        return lc

    seg_colors = [GRADE_COLORS.get(str(g), "#999999") for g in t["grade"].astype(object)[:-1]]
    lc = LineCollection(
        segs, colors=seg_colors, transform=pc, linewidths=3.4, zorder=4, capstyle="round"
    )
    ax.add_collection(lc)
    return None


def plot_track(
    track,
    ax=None,
    color="grade",
    cmap="viridis",
    extent=None,
    pad=2.0,
    show_start=True,
    show_end=True,
    show_peak=True,
    annotate=False,
    title=None,
):
    """Plot one storm's track on a Cartopy map, as intensity-coloured segments.

    Parameters
    ----------
    track : DataFrame for a single storm (e.g. ``bt.storm(id_or_name)``) with
            ``lat``, ``lon``, ``time`` and, for colouring, ``grade`` or ``wind``.
    color : ``"grade"`` (IMD category, discrete legend) or ``"wind"`` (colorbar).
    cmap  : colormap used when ``color="wind"``.
    show_start, show_end, show_peak : mark genesis (●), dissipation (✖) and the
            lifetime-peak (★) fixes.
    annotate : label those markers (peak includes its wind speed).
    title : your own title string; ``""`` for none. If left as ``None`` a
            two-line title is generated from the storm — e.g.
            ``"Cyclone Tauktae (2021)\\nPeak: ESCS · 100 kt"``.
    """
    ccrs, cfeature, plt = _cartopy()
    from matplotlib.lines import Line2D

    t = track.sort_values("time").reset_index(drop=True)
    ext = extent or _extent(t["lon"], t["lat"], pad)
    if ax is None:
        _, ax = _new_fig(ext, 7.5, plt, ccrs)
    _basemap(ax, ext, ccrs, cfeature)
    pc = ccrs.PlateCarree()

    mappable = _colored_line(ax, t, color, cmap, pc)
    if mappable is not None:
        cb = ax.figure.colorbar(mappable, ax=ax, shrink=0.72, pad=0.02)
        cb.set_label("Max sustained wind (kt)", color=_INK)
        cb.outline.set_visible(False)
        cb.ax.tick_params(color="#999", labelcolor="#555")

    def _mark(i, marker, size, face, label):
        ax.scatter(
            t["lon"].iloc[i],
            t["lat"].iloc[i],
            marker=marker,
            s=size,
            facecolor=face,
            edgecolor="black",
            linewidth=0.8,
            transform=pc,
            zorder=6,
        )
        if annotate:
            ax.annotate(
                label,
                (t["lon"].iloc[i], t["lat"].iloc[i]),
                xytext=(7, 7),
                textcoords="offset points",
                fontsize=8.5,
                fontweight="bold",
                color=_INK,
                zorder=7,
                path_effects=_halo(),
            )

    pk = _peak_idx(t)
    if show_start:
        _mark(0, "o", 80, "#2ca02c", "start")
    if show_end:
        _mark(len(t) - 1, "X", 95, "#d62828", "end")
    if show_peak and pk is not None:
        pos = int(t.index.get_loc(pk))
        _mark(pos, "*", 260, "#ffcf33", f"peak {t['wind'].iloc[pos]:.0f} kt")

    handles = []
    if color == "grade":
        present = [g for g in GRADE_ORDER if g in set(t["grade"].dropna().astype(object))]
        handles += [
            Line2D([], [], color=GRADE_COLORS[g], lw=3, label=f"{g} · {GRADE_LONG[g]}")
            for g in present
        ]
    marks = []
    if show_start:
        marks.append(Line2D([], [], marker="o", ls="", mfc="#2ca02c", mec="black", label="genesis"))
    if show_peak and pk is not None:
        marks.append(
            Line2D(
                [], [], marker="*", ls="", mfc="#ffcf33", mec="black", markersize=12, label="peak"
            )
        )
    if show_end:
        marks.append(Line2D([], [], marker="X", ls="", mfc="#d62828", mec="black", label="end"))
    if handles or marks:
        ax.legend(
            handles=handles + marks,
            loc="upper right",
            fontsize=8,
            framealpha=0.92,
            edgecolor="#dddddd",
        ).set_zorder(8)

    title = _auto_title(t) if title is None else title
    _set_title(ax, title)
    return ax


def _set_title(ax, title):
    # A fixed-aspect GeoAxes can fill the figure, leaving no room for ax.set_title
    # under constrained_layout; suptitle reserves space reliably. Only when we own
    # the whole figure (single map) — otherwise fall back to a normal axes title.
    if not title:
        return
    fig = ax.figure
    if len(fig.axes) <= 2:  # the map (+ optional colorbar)
        fig.suptitle(title, fontsize=12.5, fontweight="bold", color=_INK, linespacing=1.4)
    else:
        ax.set_title(title, fontsize=12.5, fontweight="bold", color=_INK, linespacing=1.4)


def plot_tracks(
    observations, ax=None, color="basin", extent=None, pad=1.0, linewidth=1.1, alpha=0.6, title=None
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
        rank = {g: i for i, g in enumerate(GRADE_ORDER)}
        peak = (
            obs.assign(_r=obs["grade"].astype(object).map(rank))
            .sort_values("_r")
            .groupby("storm_id", sort=False)
            .last()["grade"]
        )
    for sid, g in obs.groupby("storm_id", sort=False):
        if color == "grade":
            c = GRADE_COLORS.get(str(peak.get(sid)), "#999999")
        else:
            c = BASIN_COLORS.get(str(g["basin"].iloc[0]), "#9aa0a6")
        ax.plot(
            g["lon"],
            g["lat"],
            color=c,
            linewidth=linewidth,
            alpha=alpha,
            solid_capstyle="round",
            transform=pc,
            zorder=3,
        )

    if color == "basin":
        keys = [b for b in ("BOB", "ARB", "LAND") if b in set(obs["basin"].astype(object))]
        handles = [Line2D([], [], color=BASIN_COLORS[b], lw=2.5, label=b) for b in keys]
        ttl = "Sub-basin"
    else:
        present = set(peak.dropna().astype(object)) if peak is not None else set()
        keys = [g for g in GRADE_ORDER if g in present]
        handles = [Line2D([], [], color=GRADE_COLORS[g], lw=2.5, label=g) for g in keys]
        ttl = "Peak grade"
    if handles:
        ax.legend(
            handles=handles,
            loc="upper right",
            fontsize=8,
            title=ttl,
            framealpha=0.92,
            edgecolor="#dddddd",
        ).set_zorder(8)

    if title:
        ax.set_title(title, fontsize=13, fontweight="bold", color=_INK)
    return ax
