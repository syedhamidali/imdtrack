# imdtrack

**IMD RSMC New Delhi cyclone best-track data as tidy pandas DataFrames and
CF-style xarray Datasets — kept up to date automatically.**

The parsed dataset lives in the project's GitHub repo (rebuilt from the IMD
workbook by a monthly, validated pipeline). `imd.load()` downloads that
pre-parsed data — no Excel scraping on your machine.

```{toctree}
:maxdepth: 2
:caption: Contents

examples/quickstart
api
```

## Install

```bash
pip install imdtrack            # pandas + pyarrow
pip install imdtrack[xarray]    # + xarray/numpy for .to_xarray()
pip install imdtrack[all]       # everything
```

## At a glance

```python
import imdtrack as imd

bt = imd.load()          # pre-parsed dataset from GitHub (cached)
bt.observations          # one tidy row per 3-hourly fix
bt.storms                # one summary row per storm
bt.to_xarray()           # (storm, step) xarray.Dataset
```

See the {doc}`examples/quickstart` for a full walkthrough and the {doc}`api`
reference for every function.
