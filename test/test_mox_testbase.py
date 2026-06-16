#!/usr/bin/env python
#
# Unit tests for Mox.
#
# Copyright 2008 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Tests for MoxTestBase and its variants."""

# Python imports
import unittest

# Internal imports
import mox

from . import mox_test_helper
from .mox_test_fixtures_helper import ClassWithProperties


OS_LISTDIR = mox_test_helper.os.listdir


class MoxTestBaseTest(unittest.TestCase):
    """Verify that all tests in a class derived from MoxTestBase are
    wrapped."""

    def setUp(self):
        self.mox = mox.Mox()
        self.test_mox = mox.Mox()
        self.test_stubs = mox.stubbingout.stubout()
        self.result = unittest.TestResult()

    def tearDown(self):
        self.mox.unset_stubs()
        self.test_mox.unset_stubs()
        self.test_stubs.unset_all()
        self.test_stubs.smart_unset_all()

    def _setUpTestClass(self):
        """Replacement for setUp in the test class instance.

        Assigns a mox.Mox instance as the mox attribute of the test class
        instance. This replacement Mox instance is under our control before
        setUp is called in the test class instance.
        """
        self.test.mox = self.test_mox
        self.test.stubs = self.test_stubs

    def _create_test(self, test_name):
        """Create a test from our example mox class.

        The created test instance is assigned to these instances test attribute.
        """
        self.test = mox_test_helper.ExampleMoxTest(test_name)
        self.mox.stubs.set(self.test, "setUp", self._setUpTestClass)

    def _verify_success(self):
        """Run the checks to confirm test method completed successfully."""
        self.mox.stubout(self.test_mox, "unset_stubs")
        self.mox.stubout(self.test_mox, "verify_all")
        self.mox.stubout(self.test_stubs, "unset_all")
        self.mox.stubout(self.test_stubs, "smart_unset_all")
        self.test_mox.unset_stubs()
        self.test_mox.verify_all()
        self.test_stubs.unset_all()
        self.test_stubs.smart_unset_all()
        self.mox.replay_all()
        self.test.run(result=self.result)
        self.assertTrue(self.result.wasSuccessful())
        self.mox.verify_all()
        self.mox.unset_stubs()  # Needed to call the real verify_all() below.
        self.test_mox.verify_all()

    def test_success(self):
        """Successful test method execution test."""
        self._create_test("test_success")
        self._verify_success()

    def test_success_no_mocks(self):
        """Let test_success() unset all the mocks, and verify they've been unset."""
        self._create_test("test_success")
        self.test.run(result=self.result)
        self.assertTrue(self.result.wasSuccessful())
        self.assertEqual(OS_LISTDIR, mox_test_helper.os.listdir)

    def test_stubs(self):
        """Test that "self.stubs" is provided as is useful."""
        self._create_test("test_has_stubs")
        self._verify_success()

    def test_raises_with_statement(self):
        self._create_test("test_raises_with_statement")
        self._verify_success()

    def test_stubs_no_mocks(self):
        """Let test_has_stubs() unset the stubs by itself."""
        self._create_test("test_has_stubs")
        self.test.run(result=self.result)
        self.assertTrue(self.result.wasSuccessful())
        self.assertEqual(OS_LISTDIR, mox_test_helper.os.listdir)

    def test_expected_not_called(self):
        """Stubbed out method is not called."""
        self._create_test("test_expected_not_called")
        self.mox.stubout(self.test_mox, "unset_stubs")
        self.mox.stubout(self.test_stubs, "unset_all")
        self.mox.stubout(self.test_stubs, "smart_unset_all")
        # Don't stub out verify_all - that's what causes the test to fail
        self.test_mox.unset_stubs().multiple_times(2)
        self.test_stubs.unset_all()
        self.test_stubs.smart_unset_all()
        self.mox.replay_all()

        self.test.run(result=self.result)
        self.assertFalse(self.result.wasSuccessful())
        self.mox.verify_all()
        # Since we mocked test_mox.unset_stubs, the stubs cache is not cleared.
        assert len(self.test_mox.stubs.cache) == 1

    def test_expected_not_called_no_mocks(self):
        """Let test_expected_not_called() unset all the mocks by itself."""
        self._create_test("test_expected_not_called")
        self.test.run(result=self.result)
        self.assertFalse(self.result.wasSuccessful())
        self.assertEqual(OS_LISTDIR, mox_test_helper.os.listdir)
        assert len(self.test_mox.stubs.cache) == 0

    def test_unexpected_call(self):
        """Stubbed out method is called with unexpected arguments."""
        self._create_test("test_unexpected_call")
        self.mox.stubout(self.test_mox, "unset_stubs")
        self.mox.stubout(self.test_stubs, "unset_all")
        self.mox.stubout(self.test_stubs, "smart_unset_all")
        # Ensure no calls are made to verify_all()
        self.mox.stubout(self.test_mox, "verify_all")
        self.test_mox.unset_stubs()
        self.test_mox.unset_stubs()
        self.test_stubs.unset_all()
        self.test_stubs.smart_unset_all()
        self.mox.replay_all()
        self.test.run(result=self.result)
        self.assertFalse(self.result.wasSuccessful())
        self.mox.verify_all()

    def test_failure(self):
        """Failing assertion in test method."""
        self._create_test("test_failure")
        self.mox.stubout(self.test_mox, "unset_stubs")
        self.mox.stubout(self.test_stubs, "unset_all")
        self.mox.stubout(self.test_stubs, "smart_unset_all")
        # Ensure no calls are made to verify_all()
        self.mox.stubout(self.test_mox, "verify_all")
        self.test_mox.unset_stubs()
        self.test_stubs.unset_all()
        self.test_stubs.smart_unset_all()
        self.mox.replay_all()
        self.test.run(result=self.result)
        self.assertFalse(self.result.wasSuccessful())
        self.mox.verify_all()

    def test_mixin(self):
        """Run test from mix-in test class, ensure it passes."""
        self._create_test("test_stat")
        self._verify_success()

    def test_mixin_again(self):
        """Run same test as above but from the current test class.

        This ensures metaclass properly wrapped test methods from all base
        classes. If unsetting of stubs doesn't happen, this will fail.
        """
        self._create_test("test_stat_other")
        self._verify_success()


class MoxTestBaseContextManagerTest(unittest.TestCase):
    """Verify that all tests in a class derived from MoxTestBase are wrapped."""

    def setUp(self):
        self.mox = mox.Mox()
        self.test_mox = mox.Mox()
        self.test_stubs = mox.stubbingout.stubout()
        self.result = unittest.TestResult()

    def tearDown(self):
        self.mox.unset_stubs()
        self.test_mox.unset_stubs()
        self.test_stubs.unset_all()
        self.test_stubs.smart_unset_all()

    def _setUpTestClass(self):
        """Replacement for setUp in the test class instance.

        Assigns a mox.Mox instance as the mox attribute of the test class
        instance. This replacement Mox instance is under our control before
        setUp is called in the test class instance.
        """
        self.test.mox = self.test_mox
        self.test.stubs = self.test_stubs

    def _create_test(self, test_name):
        """Create a test from our example mox class.

        The created test instance is assigned to these instances test attribute.
        """
        self.test = mox_test_helper.ExampleMoxTest(test_name)
        self.mox.stubs.set(self.test, "setUp", self._setUpTestClass)

    def _verify_success(self):
        """Run the checks to confirm test method completed successfully."""
        m = self.mox

        m.stubout(self.test_mox, "unset_stubs")
        m.stubout(self.test_mox, "verify_all")
        m.stubout(self.test_stubs, "unset_all")
        m.stubout(self.test_stubs, "smart_unset_all")

        with m.expect:
            self.test_mox.unset_stubs()
            self.test_mox.verify_all()
            self.test_stubs.unset_all()
            self.test_stubs.smart_unset_all()

        self.test.run(result=self.result)
        assert self.result.wasSuccessful() is True
        m.verify_all()
        m.unset_stubs()  # Needed to call the real verify_all() below.
        self.test_mox.verify_all()

    def test_success(self):
        """Successful test method execution test."""
        self._create_test("test_success")
        self._verify_success()

    def test_success_no_mocks(self):
        """Let test_success() unset all the mocks, and verify they've been unset."""
        self._create_test("test_success")
        self.test.run(result=self.result)
        assert self.result.wasSuccessful() is True
        assert OS_LISTDIR == mox_test_helper.os.listdir

    def test_stubs(self):
        """Test that "self.stubs" is provided as is useful."""
        self._create_test("test_has_stubs")
        self._verify_success()

    def test_raises_with_statement(self):
        self._create_test("test_raises_with_statement")
        self._verify_success()

    def test_stubs_no_mocks(self):
        """Let test_has_stubs() unset the stubs by itself."""
        self._create_test("test_has_stubs")
        self.test.run(result=self.result)
        assert self.result.wasSuccessful() is True
        assert OS_LISTDIR == mox_test_helper.os.listdir

    def test_expected_not_called(self):
        """Stubbed out method is not called."""
        self._create_test("test_expected_not_called")

        m = self.mox
        m.stubout(self.test_mox, "unset_stubs")
        m.stubout(self.test_stubs, "unset_all")
        m.stubout(self.test_stubs, "smart_unset_all")
        # Don't stub out verify_all - that's what causes the test to fail

        with m.expect:
            self.test_mox.unset_stubs().multiple_times(2)
            self.test_stubs.unset_all()
            self.test_stubs.smart_unset_all()

        self.test.run(result=self.result)
        assert self.result.wasSuccessful() is False
        m.verify_all()
        # Since we mocked test_mox.unset_stubs, the stubs cache is not cleared.
        assert len(self.test_mox.stubs.cache) == 1

    def test_expected_not_called_no_mocks(self):
        """Let test_expected_not_called() unset all the mocks by itself."""
        self._create_test("test_expected_not_called")
        self.test.run(result=self.result)
        assert self.result.wasSuccessful() is False
        assert OS_LISTDIR == mox_test_helper.os.listdir
        assert len(self.test_mox.stubs.cache) == 0

    def test_unexpected_call(self):
        """Stubbed out method is called with unexpected arguments."""
        self._create_test("test_unexpected_call")

        m = self.mox
        m.stubout(self.test_mox, "unset_stubs")
        m.stubout(self.test_stubs, "unset_all")
        m.stubout(self.test_stubs, "smart_unset_all")
        # Ensure no calls are made to verify_all()
        m.stubout(self.test_mox, "verify_all")

        with m.expect:
            self.test_mox.unset_stubs()
            self.test_mox.unset_stubs()
            self.test_stubs.unset_all()
            self.test_stubs.smart_unset_all()

        self.test.run(result=self.result)
        assert self.result.wasSuccessful() is False
        m.verify_all()

    def test_failure(self):
        """Failing assertion in test method."""
        self._create_test("test_failure")

        m = self.mox
        m.stubout(self.test_mox, "unset_stubs")
        m.stubout(self.test_stubs, "unset_all")
        m.stubout(self.test_stubs, "smart_unset_all")
        # Ensure no calls are made to verify_all()
        m.stubout(self.test_mox, "verify_all")

        with m.expect:
            self.test_mox.unset_stubs()
            self.test_stubs.unset_all()
            self.test_stubs.smart_unset_all()

        self.test.run(result=self.result)
        assert self.result.wasSuccessful() is False
        m.verify_all()

    def test_mixin(self):
        """Run test from mix-in test class, ensure it passes."""
        self._create_test("test_stat")
        self._verify_success()

    def test_mixin_again(self):
        """Run same test as above but from the current test class.

        This ensures metaclass properly wrapped test methods from all base
        classes. If unsetting of stubs doesn't happen, this will fail.
        """
        self._create_test("test_stat_other")
        self._verify_success()


class MyTestCase(unittest.TestCase):
    """Simulate the use of a fake wrapper around Python's unittest library."""

    def setUp(self):
        super(MyTestCase, self).setUp()
        self.critical_variable = 42
        self.another_critical_variable = 42

    def test_method_override(self):
        """Should be properly overriden in a derived class."""
        self.assertEqual(42, self.another_critical_variable)
        self.another_critical_variable += 1


class MoxTestBaseMultipleInheritanceTest(mox.testing.unittest_mox.MoxTestBase, MyTestCase):
    """Test that multiple inheritance can be used with MoxTestBase."""

    def setUp(self):
        super(MoxTestBaseMultipleInheritanceTest, self).setUp()
        self.another_critical_variable = 99

    def test_multiple_inheritance(self):
        """Should be able to access members created by all parent setUp()."""
        self.assertIsInstance(self.mox, mox.Mox)
        self.assertEqual(42, self.critical_variable)

    def test_method_override(self):
        """Should run before MyTestCase.test_method_override."""
        self.assertEqual(99, self.another_critical_variable)
        self.another_critical_variable = 42
        super(MoxTestBaseMultipleInheritanceTest, self).test_method_override()
        self.assertEqual(43, self.another_critical_variable)


class MoxTestDontMockProperties(MoxTestBaseTest):
    def test_properties_arent_mocked(self):
        mock_class = self.mox.create_mock(ClassWithProperties)
        self.assertRaises(mox.UnknownMethodCallError, lambda: mock_class.prop_attr)


if __name__ == "__main__":
    unittest.main()
