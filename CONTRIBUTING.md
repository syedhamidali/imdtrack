# Contributing to imdtrack

Thanks for helping! Bug reports, fixes, and features are all welcome via
[issues](https://github.com/syedhamidali/imdtrack/issues) and pull requests.

## Development setup ([uv](https://docs.astral.sh/uv/))

[uv](https://docs.astral.sh/uv/) is the fastest way to get a dev environment:

```bash
uv venv                                    # create .venv (uv picks a Python)
uv pip install -e ".[dev,plot,docs]"       # all dev/test/plot/docs deps
```

(Plain `pip` works too: `pip install -e ".[dev]"`.) The version is derived from
git tags by [hatch-vcs](https://github.com/ofek/hatch-vcs), so no
`__version__` to edit.

## Checks

```bash
pytest                 # tests (cartopy plot tests skip if cartopy is absent)
black . && ruff check .  # format + lint
```

Install the pre-commit hooks so these run automatically:

```bash
uv pip install pre-commit
pre-commit install --hook-type pre-commit --hook-type pre-push
```

## Workflow

Never push to `main` directly. Create a branch, open a PR, and let CI (lint +
tests on Python 3.9–3.14 + docs build) go green before merging:

```bash
git switch -c my-change
# ... commit ...
git push -u origin my-change   # then open a PR
```

## Releases

Releases are cut from a git tag — no source edit. Tag `main` and push:

```bash
git tag v0.2.6 && git push origin v0.2.6
```

That triggers the release workflow (build → TestPyPI → PyPI → GitHub Release →
Zenodo). The dataset in `data/` also auto-updates monthly and cuts its own
patch release when IMD publishes new data.
