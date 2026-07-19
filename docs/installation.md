# Installation

imdtrack is published on both [PyPI](https://pypi.org/project/imdtrack/) (for
`pip` / `uv`) and [conda-forge](https://anaconda.org/conda-forge/imdtrack) (for
the whole conda family). Pick whichever matches your stack — the core package is
identical either way.

## pip

```bash
pip install imdtrack            # core: pandas + pyarrow (reads the published parquet)
pip install imdtrack[xarray]    # + xarray/numpy for .to_xarray()
pip install imdtrack[plot]      # + cartopy/matplotlib for map plotting
pip install imdtrack[all]       # xarray + numpy + openpyxl
```

It's good practice to install into a virtual environment rather than the system
Python:

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install imdtrack
```

## conda / mamba / micromamba

imdtrack is on **conda-forge**, so it installs with any tool in the conda family.
`conda` ships with [Anaconda](https://www.anaconda.com/download) or the smaller
[Miniconda](https://docs.anaconda.com/miniconda/); [`mamba`](https://mamba.readthedocs.io/)
and [`micromamba`](https://mamba.readthedocs.io/en/latest/user_guide/micromamba.html)
are faster, drop-in replacements that take the **same commands and flags** — just
swap the executable name.

The recommended pattern is a dedicated environment. Create one with imdtrack
already in it, then activate it:

```bash
# conda (Anaconda / Miniconda)
conda create -n imd -c conda-forge imdtrack
conda activate imd

# mamba
mamba create -n imd -c conda-forge imdtrack
mamba activate imd

# micromamba (no base conda install required)
micromamba create -n imd -c conda-forge imdtrack
micromamba activate imd
```

Pin a Python version at creation time if you need one, and add any extras' deps
as ordinary conda packages (they live on conda-forge too):

```bash
conda create -n imd -c conda-forge python=3.12 imdtrack xarray cartopy matplotlib
```

To add imdtrack to an environment you already have active, use `install` instead
of `create` (again, `conda` / `mamba` / `micromamba` are interchangeable):

```bash
conda install -c conda-forge imdtrack
```

```{tip}
The conda-forge build **bundles a prebuilt cartopy**, so map plotting works with
no compiler and no system GEOS/PROJ — the easiest route if you want the plotting
features.
```

## uv

[uv](https://docs.astral.sh/uv/) installs the same PyPI package, very fast:

```bash
uv add imdtrack                 # add to a uv-managed project's dependencies
uv add "imdtrack[plot]"         # …with an extra
uv pip install imdtrack         # into the active/target environment (pip-compatible)
```

You can also run a throwaway session with imdtrack available, without installing
it into a project:

```bash
uv run --with imdtrack python -c "import imdtrack as imd; print(imd.load())"
```

## Optional extras

| Extra | Adds | For |
|---|---|---|
| *(none)* | pandas, pyarrow | loading the data as DataFrames |
| `xarray` | xarray, numpy | {meth}`~imdtrack.BestTracks.to_xarray` |
| `plot` | cartopy, matplotlib | {func}`~imdtrack.plot_track` / {func}`~imdtrack.plot_tracks` maps |
| `pipeline` | openpyxl | parsing the IMD workbook yourself (`source="imd"`) |

```{note}
Extras apply to the **pip / uv** install. With those, `cartopy` has no Python 3.14
wheel yet, so `[plot]` needs Python ≤ 3.13 (or a system GEOS + PROJ to build it).
The **conda-forge** package sidesteps this — see the tip above.
```

## Requirements

Python **3.9+**. The core install is pure-Python and depends only on pandas and
pyarrow, so `imd.load()` works everywhere; the heavier extras are opt-in.
