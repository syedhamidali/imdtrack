# Conda packaging

`imdtrack` is a pure-Python, `noarch` package. [`meta.yaml`](meta.yaml) builds it
from the PyPI sdist. The recommended distribution channel is **conda-forge**,
which builds, hosts, and **auto-updates** the package (its bot opens a PR for each
new PyPI release).

## Publish on conda-forge (one-time)

1. Verify the release is on PyPI and the recipe's `version` + `sha256` match it.
   Get the sdist hash with:
   ```bash
   pip download imdtrack==<version> --no-deps --no-binary :all: -d /tmp/imd
   openssl dgst -sha256 /tmp/imd/imdtrack-<version>.tar.gz
   ```
2. Fork **[conda-forge/staged-recipes](https://github.com/conda-forge/staged-recipes)**.
3. Copy this `meta.yaml` to `recipes/imdtrack/meta.yaml` in your fork.
4. Open a PR to `staged-recipes`. The linter bot checks it; a conda-forge
   maintainer reviews and merges.
5. On merge, conda-forge creates `imdtrack-feedstock` and builds the package.
   It then appears as:
   ```bash
   conda install -c conda-forge imdtrack
   ```

After that, the **regro-cf-autotick-bot** opens a version-bump PR on the feedstock
each time a new `imdtrack` release lands on PyPI — merge it and the new version
ships automatically.

## Optional dependencies

The recipe pins only the runtime deps (`pandas`, `pyarrow`). The extras
(`xarray`, `cartopy` plotting, `openpyxl` pipeline) are all on conda-forge, so
users add whichever they need:

```bash
conda install -c conda-forge imdtrack xarray cartopy
```

## Local build (to test the recipe)

```bash
conda install -n base conda-build
conda build conda/          # builds meta.yaml from the PyPI sdist
```

## Alternative: a personal channel

To publish under your own [anaconda.org](https://anaconda.org) channel instead of
conda-forge:

```bash
conda build conda/
anaconda login
anaconda upload $(conda build conda/ --output)
# users: conda install -c <your-username> imdtrack
```
