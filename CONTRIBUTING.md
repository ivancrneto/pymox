# Contributing to Pymox

Thanks for your interest in improving Pymox! This guide covers the local setup,
the test and lint workflow, and a few conventions.

## Development setup

Pymox targets Python 3.8+ and has no runtime dependencies. Work inside a
virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate           # Windows: .venv\Scripts\activate

make install                        # editable install + dev/lint tools + pre-commit
```

`make install` runs `pip install -e ".[dev,lint]"`. The **editable** (`-e`)
install matters: the import package is named `mox` (and `pymox` is an alias of
it), so a non-editable or stale install in your environment will shadow your
working tree — tests and especially subprocess-based tests would then run old
code. If something behaves oddly, confirm the package resolves to your checkout:

```bash
python -c "import mox; print(mox.__file__)"   # should point inside this repo
```

## Running tests

```bash
make test            # pytest test
make test-cov        # with branch coverage, like CI
pytest -n auto test  # parallel, via pytest-xdist (a dev dependency)
pytest -vv -s test   # verbose + unbuffered output when you need it
```

The suite runs on CPython 3.8–3.12 in CI. New code should keep coverage from
regressing (CI enforces a Codecov threshold).

## Linting and formatting

Linting and formatting are handled by [pre-commit](https://pre-commit.com):
**Ruff** (replacing flake8 and black), **isort** (import ordering, including the
`# Python imports` / `# Internal imports` section headers Ruff does not emit),
and **bandit**.

```bash
make lint      # run every hook in check mode (pre-commit run --all-files)
make format    # auto-format + sort imports in place
```

`pre-commit install` (run by `make install`) wires the hooks to run on every
commit.

## Conventions

- Keep imports grouped under the `# Python imports` / `# Pip imports` /
  `# Internal imports` headers; isort maintains these automatically.
- Line length is 120.
- Public-facing changes should add type hints and update `CHANGELOG.md` under
  `## Unreleased`.
- Pymox exposes several API styles (the modern `with stubout(...)` /
  `@mox.patch` / `mox` fixture forms, plus the classic and legacy
  `StubOutWithMock` ones). When adding behavior, prefer wiring it through the
  modern API and keep the others working.

## Pull requests

- Branch off `main` (e.g. `feature/...`, `fix/...`).
- Make sure `make lint` and `make test` pass before pushing.
- Describe the change and the motivation; link any related issue.
