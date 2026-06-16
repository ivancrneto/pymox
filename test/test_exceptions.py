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
"""Tests for mox exception types."""

# Python imports
import unittest

# Internal imports
import mox


class ExpectedMethodCallsErrorTest(unittest.TestCase):
    """Test creation and string conversion of ExpectedMethodCallsError."""

    def test_at_least_one_method(self):
        self.assertRaises(ValueError, mox.ExpectedMethodCallsError, [])

    def test_one_error(self):
        method = mox.MockMethod("test_method", [], [], False)
        method(1, 2).returns("output")
        e = mox.ExpectedMethodCallsError([method])
        self.assertEqual(
            "Verify: Expected methods never called:\n  0.  test_method(1, 2) -> 'output'",
            str(e),
        )

    def test_many_errors(self):
        method1 = mox.MockMethod("test_method", [], [], False)
        method1(1, 2).returns("output")
        method2 = mox.MockMethod("test_method", [], [], False)
        method2(a=1, b=2, c="only named")
        method3 = mox.MockMethod("test_method2", [], [], False)
        method3().returns(44)
        method4 = mox.MockMethod("test_method", [], [], False)
        method4(1, 2).returns("output")
        e = mox.ExpectedMethodCallsError([method1, method2, method3, method4])
        self.assertEqual(
            "Verify: Expected methods never called:\n"
            "  0.  test_method(1, 2) -> 'output'\n"
            "  1.  test_method(a=1, b=2, c='only named') -> None\n"
            "  2.  test_method2() -> 44\n"
            "  3.  test_method(1, 2) -> 'output'",
            str(e),
        )


if __name__ == "__main__":
    unittest.main()
