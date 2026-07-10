# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.16.0
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %% [markdown]
# # North Indian Ocean cyclone climatology
#
# This notebook explores the full IMD best-track record (1982–present) the way
# you might with [tropycal](https://tropycal.github.io/) for other basins: we map
# every track, look at where storms form, and build a climatology of frequency,
# seasonality, and intensity for the two North Indian Ocean sub-basins — the
# **Bay of Bengal (BOB)** and the **Arabian Sea (ARB)**.
#
# Everything runs against the dataset committed in the repo, so the numbers and
# figures below are real and regenerate on every docs build.

# %%
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import imdtrack as imd

plt.rcParams.update(
    {
        "figure.dpi": 110,
        "axes.grid": True,
        "grid.alpha": 0.25,
        "axes.spines.top": False,
        "axes.spines.right": False,
    }
)

bt = imd.load()
obs = bt.observations.copy()
storms = bt.storms.copy()

# A consistent colour per sub-basin, reused across every figure.
BASIN_COLORS = {"BOB": "#1f77b4", "ARB": "#d62728", "LAND": "#7f7f7f"}


def storm_label(row):
    """A display name, falling back to the storm id for unnamed systems."""
    name = row["name"]
    return name if isinstance(name, str) and name else row["storm_id"]


bt

# %% [markdown]
# ## Headline numbers
#
# A quick orientation before the plots.

# %%
n_storms = len(storms)
yr_min, yr_max = int(storms["year"].min()), int(storms["year"].max())
by_basin = storms["basin"].value_counts()
strongest = storms.loc[storms["max_wind"].idxmax()]

print(f"Record: {n_storms} systems, {yr_min}–{yr_max}")
print(f"By sub-basin: {by_basin.to_dict()}")
print(
    f"Bay of Bengal share: {by_basin.get('BOB', 0) / n_storms:.0%}  |  "
    f"Arabian Sea share: {by_basin.get('ARB', 0) / n_storms:.0%}"
)
print(
    f"Strongest system: {storm_label(strongest)} ({strongest['storm_id']}), "
    f"peak {strongest['max_wind']:.0f} kt, min pressure {strongest['min_pressure']:.0f} hPa"
)

# %% [markdown]
# The Bay of Bengal produces the large majority of North Indian Ocean systems —
# it is warmer, more humid, and its geometry funnels storms onto densely
# populated coasts. The Arabian Sea is quieter, but as we'll see its activity has
# not been steady over time.

# %% [markdown]
# ## Every track on one map
#
# Each line is one storm, coloured by its sub-basin. Even without coastlines the
# shape of the basin is obvious: BOB tracks (blue) curve up towards the
# north-east Indian and Bangladesh coasts, while ARB tracks (red) sit to the west.

# %%
storm_basin = storms.set_index("storm_id")["basin"]

fig, ax = plt.subplots(figsize=(8, 7))
for sid, g in obs.groupby("storm_id", sort=False):
    ax.plot(
        g["lon"],
        g["lat"],
        color=BASIN_COLORS.get(storm_basin.get(sid), "#7f7f7f"),
        lw=0.7,
        alpha=0.5,
    )

# Region labels for orientation.
ax.text(88, 15, "Bay of\nBengal", color=BASIN_COLORS["BOB"], fontsize=11, ha="center")
ax.text(63, 15, "Arabian\nSea", color=BASIN_COLORS["ARB"], fontsize=11, ha="center")
ax.text(80, 22, "India", color="0.4", fontsize=11, ha="center", style="italic")

handles = [
    plt.Line2D([], [], color=c, lw=2, label=b)
    for b, c in BASIN_COLORS.items()
    if b in set(storm_basin)
]
ax.legend(handles=handles, title="Sub-basin", loc="lower left")
ax.set_aspect("equal")
ax.set_xlabel("Longitude (°E)")
ax.set_ylabel("Latitude (°N)")
ax.set_title(f"All IMD best tracks, {yr_min}–{yr_max}  (n={n_storms})")
plt.show()

# %% [markdown]
# ## Where do storms form?
#
# The **genesis point** is the first fix of each track (`step == 0`). Colouring by
# peak intensity shows that the strongest systems tend to originate in the
# southern/central Bay of Bengal, with room to intensify before landfall.

# %%
genesis = obs[obs["step"] == 0].merge(
    storms[["storm_id", "peak_grade", "max_wind"]], on="storm_id", how="left"
)

fig, ax = plt.subplots(figsize=(8, 6))
sc = ax.scatter(
    genesis["lon"],
    genesis["lat"],
    c=genesis["max_wind"],
    cmap="turbo",
    s=22,
    alpha=0.8,
    edgecolor="none",
)
ax.set_aspect("equal")
ax.set_xlabel("Longitude (°E)")
ax.set_ylabel("Latitude (°N)")
ax.set_title("Genesis locations, coloured by lifetime peak wind")
fig.colorbar(sc, ax=ax, label="Peak sustained wind (kt)")
plt.show()

# %% [markdown]
# ## Annual frequency, split by sub-basin
#
# Counts of named/numbered systems per year. The Bay of Bengal dominates almost
# every season; the Arabian Sea contributes a smaller, more variable share.

# %%
counts = (
    storms.groupby(["year", "basin"], observed=True)
    .size()
    .unstack("basin")
    .reindex(range(yr_min, yr_max + 1), fill_value=0)
)
for col in ("BOB", "ARB"):
    if col not in counts:
        counts[col] = 0

fig, ax = plt.subplots(figsize=(10, 4.5))
ax.bar(counts.index, counts["BOB"], color=BASIN_COLORS["BOB"], label="BOB")
ax.bar(
    counts.index,
    counts["ARB"],
    bottom=counts["BOB"],
    color=BASIN_COLORS["ARB"],
    label="ARB",
)
ax.set_xlabel("Year")
ax.set_ylabel("Number of systems")
ax.set_title("North Indian Ocean systems per year")
ax.legend()
plt.show()

# %% [markdown]
# ### Is the Arabian Sea getting busier?
#
# A recurring result in the literature is that Arabian Sea activity has increased
# in recent decades. We can check the record directly by comparing the first and
# second halves of the period.

# %%
mid = (yr_min + yr_max) // 2
early = storms[storms["year"] <= mid]
late = storms[storms["year"] > mid]


def basin_rate(df, basin):
    n_years = df["year"].nunique()
    return (df["basin"] == basin).sum() / n_years if n_years else np.nan


print(
    f"Mean systems per year (ARB):  {yr_min}–{mid}: {basin_rate(early, 'ARB'):.2f}"
    f"   {mid + 1}–{yr_max}: {basin_rate(late, 'ARB'):.2f}"
)
print(
    f"Mean systems per year (BOB):  {yr_min}–{mid}: {basin_rate(early, 'BOB'):.2f}"
    f"   {mid + 1}–{yr_max}: {basin_rate(late, 'BOB'):.2f}"
)

# %% [markdown]
# ## The double cyclone season
#
# Unlike most basins, the North Indian Ocean has a **bimodal** season: the summer
# monsoon suppresses cyclogenesis, leaving two peaks — a **pre-monsoon** peak
# (April–June) and a stronger **post-monsoon** peak (October–December). Grouping
# genesis month by sub-basin shows this clearly.

# %%
gen_month = storms.assign(month=storms["start_time"].dt.month)
season = (
    gen_month.groupby(["month", "basin"], observed=True)
    .size()
    .unstack("basin")
    .reindex(range(1, 13), fill_value=0)
)
for col in ("BOB", "ARB"):
    if col not in season:
        season[col] = 0

months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
x = np.arange(12)
fig, ax = plt.subplots(figsize=(9, 4.5))
ax.bar(x - 0.2, season["BOB"], width=0.4, color=BASIN_COLORS["BOB"], label="BOB")
ax.bar(x + 0.2, season["ARB"], width=0.4, color=BASIN_COLORS["ARB"], label="ARB")
ax.axvspan(2.5, 5.5, color="orange", alpha=0.08)
ax.axvspan(8.5, 11.5, color="purple", alpha=0.08)
ax.set_xticks(x)
ax.set_xticklabels(months)
ax.set_xlabel("Genesis month")
ax.set_ylabel("Number of systems")
ax.set_title("Seasonal cycle of cyclogenesis (shaded: pre- and post-monsoon peaks)")
ax.legend()
plt.show()

# %% [markdown]
# ## Intensity distribution
#
# IMD classifies systems on an ordered scale from Depression (`D`) up to Super
# Cyclonic Storm (`SuCS`). Most systems never get past Cyclonic Storm; only a
# handful each decade reach the top categories.

# %%
from imdtrack import GRADE_LONG, GRADE_ORDER  # noqa: E402

grade_counts = storms["peak_grade"].value_counts().reindex(GRADE_ORDER, fill_value=0)

fig, ax = plt.subplots(figsize=(9, 4.5))
ax.bar(range(len(GRADE_ORDER)), grade_counts.values, color="#4c72b0")
ax.set_xticks(range(len(GRADE_ORDER)))
ax.set_xticklabels([f"{g}\n{GRADE_LONG[g].split()[0]}" for g in GRADE_ORDER], fontsize=8)
ax.set_ylabel("Number of systems (by lifetime peak grade)")
ax.set_title("Distribution of peak intensity")
for i, v in enumerate(grade_counts.values):
    ax.text(i, v, str(int(v)), ha="center", va="bottom", fontsize=8)
plt.show()

# %% [markdown]
# ## An ACE-like activity index
#
# [Accumulated Cyclone Energy](https://en.wikipedia.org/wiki/Accumulated_cyclone_energy)
# (ACE) sums the square of the maximum sustained wind over a storm's life, counting
# only fixes at tropical-storm strength (≥ 34 kt) and at 6-hourly (synoptic)
# times. The IMD record is 3-hourly, so we subsample to the synoptic hours to
# approximate the standard definition. Treat this as an *ACE-like* index rather
# than an official value.

# %%
syn = obs[obs["time"].dt.hour.isin([0, 6, 12, 18])]
syn = syn[syn["wind"] >= 34.0]
ace = 1e-4 * (syn["wind"] ** 2)
ace_year = ace.groupby(syn["year"]).sum().reindex(range(yr_min, yr_max + 1), fill_value=0)

fig, ax = plt.subplots(figsize=(10, 4.5))
ax.bar(ace_year.index, ace_year.values, color="#55a868")
ax.axhline(ace_year.mean(), color="0.3", ls="--", lw=1, label="period mean")
ax.set_xlabel("Year")
ax.set_ylabel("ACE-like index (10$^4$ kt$^2$)")
ax.set_title("Basin-wide seasonal activity (ACE-like)")
ax.legend()
plt.show()

# %% [markdown]
# ## The strongest storms on record

# %%
top10 = (
    storms.sort_values("max_wind", ascending=False)
    .head(10)[["storm_id", "name", "basin", "start_time", "peak_grade", "max_wind", "min_pressure"]]
    .reset_index(drop=True)
)
top10

# %% [markdown]
# ### Track of the most intense system
#
# Colouring a single track by wind speed shows the classic
# intensification-then-landfall life cycle.

# %%
track = bt.storm(strongest["storm_id"])
fig, ax = plt.subplots(figsize=(7, 6))
ax.plot(track["lon"], track["lat"], color="0.7", lw=1, zorder=0)
sc = ax.scatter(track["lon"], track["lat"], c=track["wind"], cmap="turbo", s=40)
ax.set_aspect("equal")
ax.set_xlabel("Longitude (°E)")
ax.set_ylabel("Latitude (°N)")
ax.set_title(f"{storm_label(strongest)} — peak {strongest['max_wind']:.0f} kt")
fig.colorbar(sc, ax=ax, label="Sustained wind (kt)")
plt.show()

# %% [markdown]
# ## Takeaways
#
# - The **Bay of Bengal** dominates North Indian Ocean cyclone activity, but the
#   **Arabian Sea** is the more variable — and, in this record, increasingly
#   active — sub-basin.
# - The basin's defining feature is its **bimodal season**, split by the summer
#   monsoon into pre- and post-monsoon peaks.
# - Most systems stay weak; a small tail of intense storms drives the
#   basin-wide ACE-like index and, of course, the impacts.
#
# From here you can slice the {doc}`xarray view <quickstart>` for gridded
# analysis, or pull any single storm with `bt.storm(...)`.
