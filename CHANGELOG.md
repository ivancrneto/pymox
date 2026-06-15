# Changelog

## Unreleased

-   Python support: dropped end-of-life Python 3.8 and 3.9 (minimum is now 3.10) and added Python 3.13; CI now also runs on PyPy
-   CI: added a `mypy` type-checking job (the codebase is now mypy-clean), bumped all GitHub Actions to current major versions, and moved the Codecov token out of a committed file into the `CODECOV_TOKEN` repository secret
-   Tooling: switched linting/formatting to [Ruff](https://docs.astral.sh/ruff/) (replacing flake8 and black; isort is retained for its import-section headers), refreshed all pre-commit hooks to current versions, and added a `Makefile`, `CONTRIBUTING.md`, and GitHub issue/PR templates. Test runs are no longer forced to `-s -vv` (pass them on the command line when wanted)
-   `import pymox` now works and refers to the exact same package as `import mox` (`pymox is mox`), fixing the long-standing mismatch between the PyPI/distribution name (`pymox`) and the import name (`mox`)
-   The package now ships a `py.typed` marker and type hints on the public API (the `Mox` lifecycle methods, `stubout`/`stubout_class`, `@mox.patch`, and the module-level `replay`/`verify`/`reset`), so type checkers and editors pick up pymox's types
-   Added `@mox.patch` (and `@mox.patch_class`) decorators for context-manager-free stubbing, à la `unittest.mock.patch`: the mock is injected as an argument, stubs are restored, and mocks are verified automatically on a passing test. Decorators stack and inject mocks top-to-bottom
-   The pytest `mox` fixture is now functional: it yields a managed `Mox` (also exposing the module-level helpers and comparators), restores stubs, and verifies mocks automatically when a test passes - without masking a failing test's real error. `mox_verify` is kept as a backward-compatible alias
-   `mox.replay(factory)` now also puts the instances a `stubout_class` factory produced into replay mode, so a factory can be replayed with a single call

## 1.5.0

-   `MockObject`, `MockAnything` and `Comparator` instances are now hashable again, so mocks can be used as dict keys or set members by the code under test
-   Fixed `stubout`/`stubout_class` raising `AttributeError` when given a string object path together with a separate `attr_name`
-   Fixed the global Mox instance registry leaking instances for the life of the process and re-verifying mocks from earlier tests, which could leak failures across unrelated tests; test teardown now clears the registry
-   Fixed `smart_set`/`smart_unset_all` leaving a leftover shadowing attribute on a subclass when the stubbed attribute was inherited from a base class; the inherited definition is now properly restored
-   `StubOutForTesting.__del__` no longer raises during interpreter shutdown; cleanup is now best-effort
-   Modernized internal `super(Class, self)` calls to the argument-less `super()` form
-   Fixed `with_side_effects` overriding an explicit `and_return(None)`/`returns(None)`; an explicitly configured `None` return value is now respected instead of being replaced by the side effect's return value
-   Replaced the Python 2-only `__nonzero__` on mocks with `__bool__` (behavior unchanged)
-   Removed the empty, unused root `requirements.txt` and its `MANIFEST.in` entry
-   Removed dead, always-true type-selection logic in `stubout` (and the unused `_USE_MOCK_OBJECT`/`_USE_MOCK_FACTORY` tables); clarified its docstring to match actual behavior (MockObject by default, MockAnything with `use_mock_anything=True`)
-   Migrated packaging metadata off the unused `[tool.poetry]` block into PEP 621 `[project]`, so the hatchling-built package now actually ships its authors, license, keywords, classifiers and URLs; CI and the release workflow now use `pip`/`python -m build` instead of poetry

## 1.4.1

-   Fixed tests output when mocking builtin functions
-   Started using [`hatch`](https://hatch.pypa.io/latest/) as build tool
-   Fixed version shown on docs

## 1.4.0

-   Python 3.7 is no longer supported
-   String imports: now it's possible to `stubout` passing the objects' string path
-   Documentation improvements
-   Other minor fixes

## 1.3.0

-   Python 3.12 is now supported
-   Python 3.5 and 3.6 are no longer supported
-   Reworked documentation

## 1.2.2

-   Fixed importing issues with pytest plugin

## 1.2.1

-   Reworked README
-   Added `to_be`, `called_with`, `and_return` and `and_raise`
-   Methods `stubout` and `stubout_class` now return the stubs
-   Added `global_unset_stubs` and `global_verify` to the Mox metaclass
-   Added minimal `pytest` support
-   Added requirements file to build docs
-   Added `furo` as docs theme
-   Added `create`, `expect` and `stubout` context managers

## 1.1.0

-   Python 3.3 and 3.4 are (finally!) no longer supported
-   Most of the code is snake_case.
-   Reorganized project with new modules: `comparators`, `exceptions`,
    `groups` and `testing`.

## 1.0.2

-   Pymox API is now snake_case, with backwards compatibility
-   README is improved, with a tutorial

## 1.0.1

-   Fixed changelog
-   Replaced setup.py with pyproject.toml
-   Removed six dependency
-   Formatted the code with black
-   Replaced master branch with main
-   Fixed support to Python 3.3 to 3.5 in dev environment
-   Set up pyproject.toml with Poetry instead of the old setup.py
-   Fixed docs building
-   Removed dependency from six
-   Formatted the code using Black

## 1.0.0

-   **Dropped Python 2 support**
-   Added support to Python 3.3 through 3.11
-   Added CHANGELOG
-   Removed deprecated testing functions
-   Rearranged files to a better packaging organization
-   Fixed setup.py requirements parsing
-   Added GitHub Actions CI
-   General improvements to PyPI setup.py, including long description

## 0.7.8

-   Improved classes and functions descriptions

## 0.7.7

-   Improved docs
-   Small fixes

## 0.7.6

-   Improvements for detecting and displaying classes and functions
    descriptions

## 0.7.5

-   Moved the code to use 4 spaces and to be flake8 compliant

## 0.7.4

-   Another small fix to handle setup package version dinamically

## 0.7.3

-   Small fix to handle setup package version dinamically

## 0.7.2

-   Added support to multiple versions of Python: 2.7, 3.3, 3.4, 3.5
-   Added first documentation initiative with a Read the Docs page

## 0.5.3

-   Added more detailed exceptions
-   Detected when an unexpected exception raised during a test to
    consider as a failed test
-   Make it possible to stub out a whole class and its properties and
    methods with mocks
-   Added more comparators

## 0.5.2

-   Provided logic for mocking classes that are iterable
-   Tweaks, bugs fixes and improvements

## 0.5.1

-   Added first README
-   Added \_\_str\_\_ and \_\_repr\_\_ to Mox class
-   Added a call checker for args and kwargs passed to functions
-   Added a Not comparator
-   Making it possible to mock container classes

## 0.5.0

-   First release
