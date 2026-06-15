# Pip imports
import _pytest.fixtures
import pytest


@pytest.fixture
def mox_verify():
    ...


def pytest_runtest_teardown(item):
    # Internal imports
    import mox

    mox_verify = None
    if "request" in item.funcargs:
        try:
            mox_verify = item.funcargs["request"].getfixturevalue("mox_verify")
        except _pytest.fixtures.FixtureLookupError:
            pass

    cleanup_mox = bool(mox_verify and isinstance(mox_verify, mox.Mox))
    if cleanup_mox:
        mox_verify.unset_stubs()

    try:
        mox.Mox.global_unset_stubs()
        if cleanup_mox:
            mox.Mox.global_verify()
    finally:
        # Forget this test's Mox instances so they neither leak for the life of
        # the process nor get re-verified during a later test's teardown.
        mox.Mox.reset_instances()
