# Python imports
import unittest

# Internal imports
import mox
from mox.testing import pytest_mox


class _FakeRequest:
    """Minimal stand-in for a pytest request object."""

    def __init__(self, mox_obj):
        self._mox_obj = mox_obj

    def getfixturevalue(self, name):
        assert name == "mox_verify"
        return self._mox_obj


class _FakeItem:
    def __init__(self, funcargs):
        self.funcargs = funcargs


class PytestPluginTeardownTest(unittest.TestCase):
    """Exercise the pytest plugin's teardown hook directly."""

    def tearDown(self):
        # Make sure we never leak instances into other tests.
        mox.Mox.reset_instances()

    def test_teardown_with_mox_verify_fixture_unsets_and_verifies(self):
        """When the mox_verify fixture yields a Mox, teardown must unset its
        stubs, verify it, and clear the global registry."""

        mox_obj = mox.Mox()
        mocked = mox_obj.create_mock_anything()
        mocked.do_something()  # record an expectation
        mox.replay(mocked)
        mocked.do_something()  # satisfy it

        item = _FakeItem({"request": _FakeRequest(mox_obj)})

        # Should run global_unset_stubs + global_verify (cleanup_mox branch)
        # without raising, then clear the registry in the finally block.
        pytest_mox.pytest_runtest_teardown(item)

        self.assertEqual(len(mox.Mox._instances), 0)

    def test_teardown_without_request_still_clears_registry(self):
        """Teardown for a test that uses no fixtures must still clear the
        global registry (and not raise)."""

        mox.Mox()  # registered in the global registry
        item = _FakeItem({})

        pytest_mox.pytest_runtest_teardown(item)

        self.assertEqual(len(mox.Mox._instances), 0)


if __name__ == "__main__":
    unittest.main()
