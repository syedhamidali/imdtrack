# imdtrack

[![CI](https://github.com/syedhamidali/imdtrack/actions/workflows/ci.yml/badge.svg)](https://github.com/syedhamidali/imdtrack/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/syedhamidali/imdtrack/branch/main/graph/badge.svg)](https://codecov.io/gh/syedhamidali/imdtrack)
[![Update dataset](https://github.com/syedhamidali/imdtrack/actions/workflows/update-dataset.yml/badge.svg)](https://github.com/syedhamidali/imdtrack/actions/workflows/update-dataset.yml)

Read the [India Meteorological Department (IMD) RSMC New Delhi](https://rsmcnewdelhi.imd.gov.in/)
**cyclone best-track dataset** — the official record of every depression and
cyclonic storm in the North Indian Ocean (Bay of Bengal & Arabian Sea) since
1982 — as a tidy **pandas DataFrame** or a CF-style **xarray Dataset**, and keep
it up to date automatically.

IMD publishes the record as a single, frequently-updated Excel workbook (one
sheet per year, 1982–present). That workbook is convenient for humans but awkward
for analysis: column headers drift between years, serial numbers appear only on
each storm's first row, numeric columns mix strings and floats, and free-text
landfall/weakening notes are interleaved with the 3-hourly track rows. This
library turns all of that into clean, analysis-ready tables.

## How it works

The **parsed dataset is committed into this repository** (under [`data/`](data/),
as parquet + a `manifest.json`). A scheduled GitHub Action rebuilds it from the
IMD workbook once a month. So:

- **You** just download the pre-parsed parquet from the repo — no Excel parsing,
  no scraping IMD on your machine. `imd.load()` fetches it (cached) and hands you
  DataFrames / an xarray Dataset.
- **The Action** does the heavy lifting: fetch → parse → **validate** → commit.
  If a new IMD upload fails to parse or looks corrupt, the run **fails and the
  committed dataset is left untouched** — a broken source file can never clobber
  the good published data.

## Install

```bash
pip install imdtrack            # pandas + pyarrow (reads the published parquet)
pip install imdtrack[xarray]    # + xarray/numpy for .to_xarray()
pip install imdtrack[pipeline]  # + openpyxl, only needed to parse IMD yourself
pip install imdtrack[all]       # everything
```

## Usage

```python
import imdtrack as imd

bt = imd.load()                 # downloads the pre-parsed dataset from GitHub (cached)
df = bt.observations            # tidy DataFrame: one row per 3-hourly fix
ds = bt.to_xarray()             # (storm, step) xarray.Dataset

# Keep it current — re-downloads only if the repo published new data:
bt = imd.load(update=True)

# Parse the IMD workbook directly instead of using the published dataset:
bt = imd.load(source="imd")     # needs the [pipeline] extra (openpyxl)

# One storm's track:
bt.storm("2020-001")            # AMPHAN

# Storm-level summary and the free-text notes:
bt.storms                       # one row per storm (peak grade, max wind, ...)
bt.remarks                      # landfall / weakening notes, linked by storm_id
```

### The tidy `observations` frame

| column | meaning |
|---|---|
| `storm_id` | stable id, `"<year>-<serial>"` e.g. `2020-001` |
| `year`, `serial` | year and serial number of the system within that year |
| `basin` | `BOB` (Bay of Bengal), `ARB` (Arabian Sea), or `LAND` |
| `name` | cyclone name (blank for unnamed / older systems) |
| `time` | observation time (UTC, `datetime64`) |
| `lat`, `lon` | position (°N, °E) |
| `ci_no` | Dvorak CI / T-number |
| `pressure` | estimated central pressure (hPa) |
| `wind` | maximum sustained surface wind (knots) |
| `pressure_drop` | pressure drop / ΔP (hPa) |
| `grade` | ordered category: `D < DD < CS < SCS < VSCS < ESCS < SuCS` |
| `oci`, `oci_diameter` | outermost closed isobar pressure (hPa) & diameter (°) |
| `step` | 0-based fix index within the storm |

### The xarray Dataset

Laid out like [IBTrACS](https://www.ncei.noaa.gov/products/international-best-track-archive):
a ragged track becomes a 2-D `(storm, step)` grid, padded with `NaN`/`NaT`.
Per-fix variables (`lat`, `lon`, `wind`, `pressure`, …) span both dims;
storm-level metadata (`name`, `basin`, `year`, `serial`, `peak_grade`) are
coordinates on the `storm` dimension.

```python
ds = bt.to_xarray()
ds.sel(storm="2020-001")["wind"].max()      # AMPHAN peak intensity
ds.where(ds.basin == "ARB", drop=True)      # Arabian Sea storms only
```

## Staying up to date

The dataset in [`data/`](data/) is refreshed automatically by the
[monthly GitHub Action](.github/workflows/update-dataset.yml). The pipeline:

1. Downloads the current IMD workbook and hashes it. If it matches the published
   `manifest.json`, there's nothing to do.
2. Otherwise parses it and runs validators (positions in range, expected columns
   present, record not mysteriously shrinking, plausible year range).
3. Only if **every** check passes are the parquet files replaced (atomically)
   and committed. If parsing or validation fails, the job exits non-zero — GitHub
   emails the failure and **the committed dataset stays as it was**.

You can run the same pipeline locally:

```bash
imdtrack build                     # fetch IMD → parse → validate → write ./data
imdtrack build --force             # rebuild even if the source is unchanged
imdtrack info                      # summary of the current record
imdtrack update                    # refresh the cached copy from the repo
imdtrack export tracks.parquet     # dump observations to CSV/Parquet
```

### Configuration

The library needs to know which repo hosts the published data. It's baked into
`imdtrack/_repo.py` but can be overridden:

```bash
export IMDTRACK_REPO=myuser/imdtrack   # owner/name of the data repo
export IMDTRACK_BRANCH=main            # default: main
export IMDTRACK_CACHE=/data/imd        # download cache (default: ~/.cache/imdtrack)
```

## Notes & caveats

- Data © India Meteorological Department. This library only reformats it; verify
  against IMD for operational use. The most recent season is marked *tentative*
  by IMD until its post-season review.
- Older years (pre-2000ish) often lack storm names and some fields (e.g. central
  pressure); those appear as blanks / `NaN`.
- Free-text annotation rows embedded in the sheets are not dropped — they are
  parsed into `bt.remarks`.

## License

BSD 3-Clause. See [LICENSE](LICENSE).
