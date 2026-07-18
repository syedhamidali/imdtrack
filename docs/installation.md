# Installation

```bash
pip install imdtrack            # core: pandas + pyarrow (reads the published parquet)
pip install imdtrack[xarray]    # + xarray/numpy for .to_xarray()
pip install imdtrack[plot]      # + cartopy/matplotlib for map plotting
pip install imdtrack[all]       # xarray + numpy + openpyxl
```

Or with [conda](https://conda-forge.org/) / [uv](https://docs.astral.sh/uv/):

```bash
conda install -c conda-forge imdtrack   # core package
uv add imdtrack                          # into a project  (or: uv pip install imdtrack)
```

## Optional extras

| Extra | Adds | For |
|---|---|---|
| *(none)* | pandas, pyarrow | loading the data as DataFrames |
| `xarray` | xarray, numpy | {meth}`~imdtrack.BestTracks.to_xarray` |
| `plot` | cartopy, matplotlib | {func}`~imdtrack.plot_track` / {func}`~imdtrack.plot_tracks` maps |
| `pipeline` | openpyxl | parsing the IMD workbook yourself (`source="imd"`) |

```{note}
`cartopy` has no Python 3.14 wheel yet, so the `[plot]` extra needs Python ≤ 3.13
(or a conda / system GEOS + PROJ to build it). Installing with
`conda install -c conda-forge imdtrack` pulls in a prebuilt cartopy and sidesteps
this entirely.
```

## Requirements

Python **3.9+**. The core install is pure-Python and depends only on pandas and
pyarrow, so `imd.load()` works everywhere; the heavier extras are opt-in.
