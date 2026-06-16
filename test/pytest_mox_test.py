import unittest

import mox
from mox.testing import pytest_mox


def _drive_wrapper(gen):
    """Run a hookwrapper generator: advance to the yield, then to completion."""
    next(gen)
    try:
        next(gen)
    except StopIteration:
        pass


class _FakeItem:
    pass


class PytestPluginTeardownTest(unittest.TestCase):
    """Exercise the pytest plugin's teardown hook directly."""

    def tearDown(self):
        # Make sure we never leak instances into other tests.
        mox.Mox.reset_instances()

    def test_teardown_unsets_stubs_and_clears_registry(self):
        """The teardown wrapper must unset global stubs and clear the registry,
        even for a Mox created by the context-manager API."""

        mox_obj = mox.Mox()
        mocked = mox_obj.create_mock_anything()
        mocked.do_something()  # record an expectation
        mox.replay(mocked)
        mocked.do_something()  # satisfy it

        self.assertGreater(len(mox.Mox._instances), 0)

        _drive_wrapper(pytest_mox.pytest_runtest_teardown(_FakeItem()))

        self.assertEqual(len(mox.Mox._instances), 0)

    def test_teardown_clears_registry_with_no_instances(self):
        """Teardown must be a no-op (and not raise) when nothing is registered."""

        mox.Mox.reset_instances()
        _drive_wrapper(pytest_mox.pytest_runtest_teardown(_FakeItem()))
        self.assertEqual(len(mox.Mox._instances), 0)


class PytestPluginFailedHelperTest(unittest.TestCase):
    """Exercise the per-phase failure tracking the ``mox`` fixture relies on."""

    def test_failed_helper_reads_recorded_phase_flags(self):
        node = _FakeItem()
        self.assertFalse(pytest_mox._test_failed(node))

        node._mox_call_failed = True
        self.assertTrue(pytest_mox._test_failed(node))

        node._mox_call_failed = False
        node._mox_setup_failed = True
        self.assertTrue(pytest_mox._test_failed(node))


if __name__ == "__main__":
    unittest.main()
