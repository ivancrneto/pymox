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
"""Tests for MockObject via the context-manager API."""

import unittest

import mox

from . import mox_test_helper
from .mox_test_fixtures_helper import SubscribtableNonIterableClass, TestClass
from .test_helpers.subpackage.faraway import FarAwayClass


class MockObjectContextManagerTest(unittest.TestCase):
    """Verify that the MockObject class works as expected with context managers."""

    def setUp(self):
        self.mock_object = mox.MockObject(TestClass)

    def test_description_mocked_object(self):
        obj = FarAwayClass()

        with mox.stubout(obj, "distant_method") as stub, mox.expect:
            obj.distant_method().returns(True)

        self.assertEqual(obj.distant_method._description, "FarAwayClass.distant_method")

        mox.reset(stub)

    def test_description_module_function(self):
        with mox.stubout(mox_test_helper, "MyTestFunction") as stub, mox.expect:
            mox_test_helper.MyTestFunction(one=1, two=2).returns(True)

        self.assertEqual(
            mox_test_helper.MyTestFunction._description,
            "function test.mox_test_helper.MyTestFunction",
        )

        mox.reset(stub)

    def test_description_mocked_class(self):
        obj = FarAwayClass()

        with mox.stubout(FarAwayClass, "distant_method") as stub, mox.expect:
            obj.distant_method().returns(True)

        self.assertEqual(obj.distant_method._description, "FarAwayClass.distant_method")

        mox.reset(stub)

    def test_description_class_method(self):
        obj = mox_test_helper.SpecialClass()

        with mox.stubout(mox_test_helper.SpecialClass, "class_method") as stub, mox.expect:
            mox_test_helper.SpecialClass.class_method().returns(True)

        self.assertEqual(obj.class_method._description, "SpecialClass.class_method")

        mox.reset(stub)

    def test_description_static_method_mock_class(self):
        with mox.stubout(mox_test_helper.SpecialClass, "static_method") as stub, mox.expect:
            mox_test_helper.SpecialClass.static_method().returns(True)

        self.assertIn(
            mox_test_helper.SpecialClass.static_method._description,
            ["SpecialClass.static_method", "function test.mox_test_helper.static_method"],
        )

        mox.reset(stub)

    def test_description_static_method_mock_instance(self):
        obj = mox_test_helper.SpecialClass()

        with mox.stubout(obj, "static_method") as stub, mox.expect:
            obj.static_method().returns(True)

        self.assertIn(
            obj.static_method._description,
            ["SpecialClass.static_method", "function test.mox_test_helper.static_method"],
        )

        mox.reset(stub)

    def test_replay_with_invalid_call(self):
        """UnknownMethodCallError should be raised if a non-member method is
        called."""
        m = self.mock_object
        with m._expect:
            m.valid_call()
        # Note: assertRaises does not catch exceptions thrown by MockObject's
        # __getattr__
        try:
            self.mock_object.invalid_call()
            self.fail("No exception thrown, expected UnknownMethodCallError")
        except mox.UnknownMethodCallError:
            pass
        except Exception:
            self.fail("Wrong exception type thrown, expected UnknownMethodCallError")

    def test_equal(self):
        """A mock should be able to compare itself to another object."""
        self.mock_object._replay()
        self.assertEqual(self.mock_object, self.mock_object)

    def test_equal_replay(self):
        other_mock_object = mox.MockObject(TestClass)

        self.mock_object._replay()
        self.assertNotEqual(self.mock_object, other_mock_object)

        other_mock_object._replay()
        self.assertEqual(self.mock_object, other_mock_object)

        self.mock_object._reset()
        other_mock_object._reset()

        self.mock_object.valid_call()
        self.assertNotEqual(self.mock_object, other_mock_object)

        other_mock_object.valid_call()
        self.assertEqual(self.mock_object, other_mock_object)

    def test_equal_mock_failure(self):
        """Verify equals identifies unequal objects."""
        self.mock_object.valid_call()
        self.mock_object._replay()
        self.assertNotEqual(self.mock_object, mox.MockObject(TestClass))

    def test_mock_set_item__expected_set_item__success(self):
        """Test that __setitem__() gets mocked in Dummy.

        In this test, _verify() succeeds.
        """
        dummy = mox.MockObject(TestClass)
        with dummy._expect:
            dummy["X"] = "Y"

        dummy["X"] = "Y"

        dummy._verify()

    def test_mock_set_item__expected_set_item__no_success(self):
        """Test that __setitem__() gets mocked in Dummy.

        In this test, _verify() fails.
        """
        dummy = mox.MockObject(TestClass)
        with dummy._expect as d:
            d["X"] = "Y"

        # NOT doing dummy['X'] = 'Y'

        self.assertRaises(mox.ExpectedMethodCallsError, dummy._verify)

    def test_mock_set_item__expected_no_set_item__success(self):
        """Test that __setitem__() gets mocked in Dummy."""
        dummy = mox.MockObject(TestClass)
        # NOT doing dummy['X'] = 'Y'

        dummy._replay()

        def call():
            dummy["X"] = "Y"

        self.assertRaises(mox.UnexpectedMethodCallError, call)

    def test_mock_set_item__expected_no_set_item__no_success(self):
        """Test that __setitem__() gets mocked in Dummy.

        In this test, _verify() fails.
        """
        dummy = mox.MockObject(TestClass)

        with dummy._expect:
            pass

        dummy._replay()

        # NOT doing dummy['X'] = 'Y'

        dummy._verify()

    def test_mock_set_item__expected_set_item__nonmatching_parameters(self):
        """Test that __setitem__() fails if other parameters are expected."""
        dummy = mox.MockObject(TestClass)

        with dummy._expect as d:
            d["X"] = "Y"

        def call():
            dummy["wrong"] = "Y"

        self.assertRaises(mox.UnexpectedMethodCallError, call)

        self.assertRaises(mox.SwallowedExceptionError, dummy._verify)

    def test_mock_set_item__with_sub_class(self):
        class NewTestClass:
            def __init__(self):
                self.my_dict = {}

            def __setitem__(self, key, value):
                self.my_dict[key] = value

        class TestSubClass(NewTestClass):
            pass

        dummy = mox.MockObject(TestSubClass)
        with dummy._expect as d:
            d[1] = 2

        dummy[1] = 2
        dummy._verify()

    def test_mock_get_item__expected_get_item__success(self):
        """Test that __getitem__() gets mocked in Dummy.

        In this test, _verify() succeeds.
        """
        dummy = mox.MockObject(TestClass)

        with dummy._expect as d:
            d["X"].returns("value")

        assert dummy["X"] == "value"

        dummy._verify()

    def test_mock_get_item__expected_get_item__no_success(self):
        """Test that __getitem__() gets mocked in Dummy.

        In this test, _verify() fails.
        """
        dummy = mox.MockObject(TestClass)

        with dummy._expect as d:
            d["X"].returns("value")

        # NOT doing dummy['X']

        self.assertRaises(mox.ExpectedMethodCallsError, dummy._verify)

    def test_mock_get_item__expected_no_get_item__no_success(self):
        """Test that __getitem__() gets mocked in Dummy."""
        dummy = mox.MockObject(TestClass)

        with dummy._expect:
            pass

        dummy._replay()

        def call():
            return dummy["X"]

        self.assertRaises(mox.UnexpectedMethodCallError, call)

    def test_mock_get_item__expected_get_item__nonmatching_parameters(self):
        """Test that __getitem__() fails if other parameters are expected."""
        dummy = mox.MockObject(TestClass)

        with dummy._expect as d:
            d["X"].returns("value")

        def call():
            return dummy["wrong"]

        self.assertRaises(mox.UnexpectedMethodCallError, call)

        self.assertRaises(mox.SwallowedExceptionError, dummy._verify)

    def test_mock_get_item__with_sub_class_of_new_style_class(self):
        class NewTestClass:
            def __getitem__(self, key):
                return {1: "1", 2: "2"}[key]

        class TestSubClass(NewTestClass):
            pass

        dummy = mox.MockObject(TestSubClass)
        with dummy._expect as d:
            d[1].returns("3")

        assert dummy.__getitem__(1) == "3"
        dummy._verify()

    def test_mock_iter__expected_iter__success(self):
        """Test that __iter__() gets mocked in Dummy.

        In this test, _verify() succeeds.
        """
        dummy = mox.MockObject(TestClass)

        with dummy._expect as d:
            iter(d).returns(iter(["X", "Y"]))

        assert [x for x in dummy] == ["X", "Y"]
        dummy._verify()

    def test_mock_contains__expected_contains__success(self):
        """Test that __contains__ gets mocked in Dummy.

        In this test, _verify() succeeds.
        """
        dummy = mox.MockObject(TestClass)

        with dummy._expect as d:
            d.__contains__("X").returns(True)

        assert "X" in dummy
        dummy._verify()

    def test_mock_contains__expected_contains__no_success(self):
        """Test that __contains__() gets mocked in Dummy.

        In this test, _verify() fails.
        """
        dummy = mox.MockObject(TestClass)
        with dummy._expect as d:
            d.__contains__("X").returns("True")

        # NOT doing 'X' in dummy

        self.assertRaises(mox.ExpectedMethodCallsError, dummy._verify)

    def test_mock_contains__expected_contains__nonmatching_parameter(self):
        """Test that __contains__ fails if other parameters are expected."""
        dummy = mox.MockObject(TestClass)

        with dummy._expect as d:
            d.__contains__("X").returns(True)

        def call():
            return "Y" in dummy

        self.assertRaises(mox.UnexpectedMethodCallError, call)

        self.assertRaises(mox.SwallowedExceptionError, dummy._verify)

    def test_mock_iter__expected_iter__no_success(self):
        """Test that __iter__() gets mocked in Dummy.

        In this test, _verify() fails.
        """
        dummy = mox.MockObject(TestClass)
        with dummy._expect as d:
            iter(d).returns(iter(["X", "Y"]))

        # NOT doing assert [x for x in dummy] == ["X", "Y"]

        self.assertRaises(mox.ExpectedMethodCallsError, dummy._verify)

    def test_mock_iter__expected_no_iter__no_success(self):
        """Test that __iter__() gets mocked in Dummy."""
        dummy = mox.MockObject(TestClass)

        dummy._replay()

        def call():
            return [x for x in dummy]

        self.assertRaises(mox.UnexpectedMethodCallError, call)

    def test_mock_iter__expected_get_item__success(self):
        """Test that __iter__() gets mocked in Dummy using getitem."""
        dummy = mox.MockObject(SubscribtableNonIterableClass)

        with dummy._expect as d:
            d[0].returns("a")
            d[1].returns("b")
            d[2].raises(IndexError)

        assert ["a", "b"] == [x for x in dummy]
        dummy._verify()

    def test_mock_iter__expected_no_get_item__no_success(self):
        """Test that __iter__() gets mocked in Dummy using getitem."""
        dummy = mox.MockObject(SubscribtableNonIterableClass)
        # NOT doing dummy[index]

        dummy._replay()

        def function():
            return [x for x in dummy]

        self.assertRaises(mox.UnexpectedMethodCallError, function)

    def test_mock_get_iter__with_sub_class_of_new_style_class(self):
        class NewTestClass:
            def __iter__(self):
                return iter([1, 2, 3])

        class TestSubClass(NewTestClass):
            pass

        dummy = mox.MockObject(TestSubClass)
        with dummy._expect as d:
            iter(d).returns(iter(["a", "b"]))

        self.assertEqual(["a", "b"], [x for x in dummy])
        dummy._verify()


if __name__ == "__main__":
    unittest.main()
