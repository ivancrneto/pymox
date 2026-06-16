"""The ``pymox`` import name must mirror the ``mox`` package exactly."""

import mox
import mox.testing.pytest_mox  # noqa: F401  (ensure the submodule is loaded)


def test_pymox_is_mox():
    import pymox

    assert pymox is mox


def test_pymox_exposes_public_api():
    import pymox

    for name in ("Mox", "patch", "patch_class", "stubout", "expect", "create", "is_a", "replay", "verify"):
        assert hasattr(pymox, name), name


def test_pymox_submodules_resolve_to_mox():
    import pymox

    # Attribute access (the way code actually reaches submodules) returns the
    # very same module objects as ``mox`` - so a single Mox registry and a
    # single ``mox`` pytest fixture.
    assert pymox.testing is mox.testing
    assert pymox.testing.pytest_mox is mox.testing.pytest_mox


def test_py_typed_marker_is_shipped():
    import os

    marker = os.path.join(os.path.dirname(mox.__file__), "py.typed")
    assert os.path.exists(marker)
