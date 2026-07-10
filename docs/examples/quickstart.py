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
# # Quickstart
#
# This example loads the IMD best-track record, explores the tidy tables, plots a
# cyclone track, and shows the xarray view. It runs end-to-end when the docs are
# built, so every output below is real.

# %%
import imdtrack as imd

bt = imd.load()
bt

# %% [markdown]
# ## The tidy `observations` frame
#
# One row per 3-hourly fix, with a stable `storm_id` (`"<year>-<serial>"`).

# %%
bt.observations.head()

# %% [markdown]
# ## Storm-level summary
#
# One row per storm: peak grade, max wind, min pressure, start/end time.

# %%
bt.storms.tail()

# %% [markdown]
# ## Plot a cyclone track
#
# Pick the most recent storm and plot its path.

# %%
import matplotlib.pyplot as plt

latest_id = bt.storms["storm_id"].iloc[-1]
track = bt.storm(latest_id)

fig, ax = plt.subplots(figsize=(6, 5))
sc = ax.scatter(track["lon"], track["lat"], c=track["wind"], cmap="viridis")
ax.plot(track["lon"], track["lat"], color="grey", lw=0.6, zorder=0)
ax.set_xlabel("Longitude (°E)")
ax.set_ylabel("Latitude (°N)")
ax.set_title(f"Track of {latest_id}")
fig.colorbar(sc, ax=ax, label="Max sustained wind (kt)")
plt.show()

# %% [markdown]
# ## The xarray Dataset
#
# A ragged track becomes a 2-D `(storm, step)` grid, IBTrACS-style.

# %%
ds = bt.to_xarray()
ds

# %% [markdown]
# Slice one storm and get its peak intensity:

# %%
ds.sel(storm=latest_id)["wind"].max().item()
