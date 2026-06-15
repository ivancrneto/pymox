# Changelog

## Unreleased

-   Removed dead, always-true type-selection logic in `stubout` (and the unused `_USE_MOCK_OBJECT`/`_USE_MOCK_FACTORY` tables); clarified its docstring to match actual behavior (MockObject by default, MockAnything with `use_mock_anything=True`)

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
