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
"""Tests for the Mox manager (classic API) and replay/verify/reset."""

import re
import sys
import unittest

import mox

from . import mox_test_helper
from .mox_test_fixtures_helper import CallableClass, InheritsFromCallable, TestClass


class TestMoxMeta:
    def test_context_managers(self):
        assert type(mox.create) is mox.contextmanagers.Create
        assert type(mox.expect) is mox.contextmanagers.Expect

    def test_instances(self):
        m1 = mox.Mox()
        m2 = mox.Mox()

        assert id(m1) in mox.Mox._instances
        assert mox.Mox._instances[id(m1)] == m1
        assert id(m2) in mox.Mox._instances
        assert mox.Mox._instances[id(m2)] == m2

    def test_unset_stubs_for_id(self):
        m1 = mox.Mox()
        m2 = mox.Mox()

        m1.stubout(TestClass, "valid_call")
        m2.stubout(TestClass, "other_valid_call")

        assert len(mox.Mox._instances[id(m1)].stubs.cache) == 1
        assert len(mox.Mox._instances[id(m2)].stubs.cache) == 1

        mox.Mox.unset_stubs_for_id(id(m1))

        assert len(mox.Mox._instances[id(m1)].stubs.cache) == 0
        assert len(mox.Mox._instances[id(m2)].stubs.cache) == 1

        mox.Mox.unset_stubs_for_id(id(m2))

        assert len(mox.Mox._instances[id(m1)].stubs.cache) == 0
        assert len(mox.Mox._instances[id(m2)].stubs.cache) == 0

    def test_global_unset_stubs(self):
        m1 = mox.Mox()
        m2 = mox.Mox()

        m1.stubout(TestClass, "valid_call")
        m2.stubout(TestClass, "other_valid_call")

        assert len(mox.Mox._instances[id(m1)].stubs.cache) == 1
        assert len(mox.Mox._instances[id(m2)].stubs.cache) == 1

        mox.Mox.global_unset_stubs()

        assert len(mox.Mox._instances[id(m1)].stubs.cache) == 0
        assert len(mox.Mox._instances[id(m2)].stubs.cache) == 0

    def test_global_verify(self):
        m1 = mox.Mox()
        m2 = mox.Mox()

        m1.stubout(TestClass, "valid_call")
        m2.stubout(TestClass, "other_valid_call")
        m1.stubout(m1, "verify_all")
        m2.stubout(m2, "verify_all")

        test = TestClass()
        test.valid_call()
        test.other_valid_call()
        m1.verify_all()
        m2.verify_all()

        m1.replay_all()
        m2.replay_all()

        mox.Mox.global_verify()
        mox.Mox.global_unset_stubs()


class MoxTest(unittest.TestCase):
    """Verify Mox works correctly."""

    def setUp(self):
        self.mox = mox.Mox()

    def test_create_object(self):
        """Mox should create a mock object."""
        self.mox.create_mock(TestClass)

    def test_create_object_using_simple_imported_module(self):
        """Mox should create a mock object for a class from a module imported
        using a simple 'import module' statement"""
        self.mox.create_mock(mox_test_helper.ExampleClass)

    def test_create_object_using_simple_imported_module_class_method(self):
        """Mox should create a mock object for a class from a module imported
        using a simple 'import module' statement"""
        example_obj = self.mox.create_mock(mox_test_helper.ExampleClass)

        self.mox.stubout(mox_test_helper.ExampleClass, "class_method")
        mox_test_helper.ExampleClass.class_method().returns(example_obj)

        def call_helper_class_method():
            return mox_test_helper.ExampleClass.class_method()

        self.mox.replay_all()
        expected_obj = call_helper_class_method()
        self.mox.verify_all()

        self.assertEqual(expected_obj, example_obj)

    def test_create_mock_of_type(self):
        self.mox.create_mock(type)

    def test_create_mock_with_bogus_attr(self):
        class BogusAttrClass(object):
            __slots__ = ("no_such_attr",)

        foo = BogusAttrClass()
        self.mox.create_mock(foo)

    def test_verify_object_with_complete_replay(self):
        """Mox should replay and verify all objects it created."""
        mock_obj = self.mox.create_mock(TestClass)
        mock_obj.valid_call()
        mock_obj.valid_call_with_args(mox.IsA(TestClass))
        self.mox.replay_all()
        mock_obj.valid_call()
        mock_obj.valid_call_with_args(TestClass("some_value"))
        self.mox.verify_all()

    def test_verify_object_with_incomplete_replay(self):
        """Mox should raise an exception if a mock didn't replay completely."""
        mock_obj = self.mox.create_mock(TestClass)
        mock_obj.valid_call()
        self.mox.replay_all()
        # valid_call() is never made
        self.assertRaises(mox.ExpectedMethodCallsError, self.mox.verify_all)

    def test_entire_workflow(self):
        """Test the whole work flow."""
        mock_obj = self.mox.create_mock(TestClass)
        mock_obj.valid_call().returns("yes")
        self.mox.replay_all()

        ret_val = mock_obj.valid_call()
        self.assertEqual("yes", ret_val)
        self.mox.verify_all()

    def test_mox_id(self):
        mock = self.mox.create_mock(mox_test_helper.SpecialClass)
        assert mock._mox_id == id(self.mox)

        mock_anything = self.mox.create_mock_anything()
        assert mock_anything._mox_id == id(self.mox)

    def test_signature_matching_with_comparator_as_first_arg(self):
        """Test that the first argument can be a comparator."""

        def verify_len(val):
            """This will raise an exception when not given a list.

            This exception will be raised when trying to infer/validate the
            method signature.
            """
            return len(val) != 1

        mock_obj = self.mox.create_mock(TestClass)
        # This intentionally does not name the 'nine' param, so it triggers
        # deeper inspection.
        mock_obj.method_with_args(mox.Func(verify_len), mox.IgnoreArg(), None)
        self.mox.replay_all()

        mock_obj.method_with_args([1, 2], "foo", None)

        self.mox.verify_all()

    def test_callable_object(self):
        """Test recording calls to a callable object works."""
        mock_obj = self.mox.create_mock(CallableClass)
        mock_obj("foo").returns("qux")
        self.mox.replay_all()

        ret_val = mock_obj("foo")
        self.assertEqual("qux", ret_val)
        self.mox.verify_all()

    def test_inherited_callable_object(self):
        """Test recording calls to an object inheriting from a callable
        object."""
        mock_obj = self.mox.create_mock(InheritsFromCallable)
        mock_obj("foo").returns("qux")
        self.mox.replay_all()

        ret_val = mock_obj("foo")
        self.assertEqual("qux", ret_val)
        self.mox.verify_all()

    def test_call_on_non_callable_object(self):
        """Test that you cannot call a non-callable object."""

        class NonCallable(object):
            pass

        noncallable = NonCallable()
        self.assertNotIn("__call__", dir(noncallable))
        mock_obj = self.mox.create_mock(noncallable)
        self.assertRaises(TypeError, mock_obj)

    def test_callable_object_with_bad_call(self):
        """Test verifying calls to a callable object works."""
        mock_obj = self.mox.create_mock(CallableClass)
        mock_obj("foo").returns("qux")
        self.mox.replay_all()

        self.assertRaises(mox.UnexpectedMethodCallError, mock_obj, "ZOOBAZ")

    def test_callable_object_verifies_signature(self):
        mock_obj = self.mox.create_mock(CallableClass)
        # Too many arguments
        self.assertRaises(AttributeError, mock_obj, "foo", "bar")

    def test_callable_object_with_bad_signature_unsets_stubs(self):
        mox2 = mox.Mox()
        mox2.stubout(TestClass, "valid_call")
        self.mox.stubout(TestClass, "other_valid_call")

        assert len(self.mox.stubs.cache) == 1
        assert len(mox2.stubs.cache) == 1

        mock_obj = self.mox.create_mock(CallableClass)
        # Too many arguments
        self.assertRaises(AttributeError, mock_obj, "foo", "bar")

        assert len(self.mox.stubs.cache) == 0
        assert len(mox2.stubs.cache) == 1

        test_obj = TestClass()
        self.assertRaises(AttributeError, test_obj.valid_call, "bar")

        assert len(self.mox.stubs.cache) == 0
        assert len(mox2.stubs.cache) == 0

    def test_unordered_group(self):
        """Test that using one unordered group works."""
        mock_obj = self.mox.create_mock_anything()
        mock_obj.method(1).any_order()
        mock_obj.method(2).any_order()
        self.mox.replay_all()

        mock_obj.method(2)
        mock_obj.method(1)

        self.mox.verify_all()

    def test_unordered_groups_inline(self):
        """Unordered groups should work in the context of ordered calls."""
        mock_obj = self.mox.create_mock_anything()
        mock_obj.open()
        mock_obj.method(1).any_order()
        mock_obj.method(2).any_order()
        mock_obj.close()
        self.mox.replay_all()

        mock_obj.open()
        mock_obj.method(2)
        mock_obj.method(1)
        mock_obj.close()

        self.mox.verify_all()

    def test_multiple_unorderd_groups(self):
        """Multiple unoreded groups should work."""
        mock_obj = self.mox.create_mock_anything()
        mock_obj.method(1).any_order()
        mock_obj.method(2).any_order()
        mock_obj.foo().any_order("group2")
        mock_obj.bar().any_order("group2")
        self.mox.replay_all()

        mock_obj.method(2)
        mock_obj.method(1)
        mock_obj.bar()
        mock_obj.foo()

        self.mox.verify_all()

    def test_multiple_unorderd_groups_out_of_order(self):
        """Multiple unordered groups should maintain external order"""
        mock_obj = self.mox.create_mock_anything()
        mock_obj.method(1).any_order()
        mock_obj.method(2).any_order()
        mock_obj.foo().any_order("group2")
        mock_obj.bar().any_order("group2")
        self.mox.replay_all()

        mock_obj.method(2)
        self.assertRaises(mox.UnexpectedMethodCallError, mock_obj.bar)

    def test_unordered_group_with_return_value(self):
        """Unordered groups should work with return values."""
        mock_obj = self.mox.create_mock_anything()
        mock_obj.open()
        mock_obj.method(1).any_order().returns(9)
        mock_obj.method(2).any_order().returns(10)
        mock_obj.close()
        self.mox.replay_all()

        mock_obj.open()
        actual_two = mock_obj.method(2)
        actual_one = mock_obj.method(1)
        mock_obj.close()

        self.assertEqual(9, actual_one)
        self.assertEqual(10, actual_two)

        self.mox.verify_all()

    def test_unordered_group_with_comparator(self):
        """Unordered groups should work with comparators"""

        def verify_one(cmd):
            if not isinstance(cmd, str):
                self.fail("Unexpected type passed to comparator: " + str(cmd))
            return cmd == "test"

        def verify_two(cmd):
            return True

        mock_obj = self.mox.create_mock_anything()
        mock_obj.foo(["test"], mox.Func(verify_one), bar=1).any_order().returns("yes test")
        mock_obj.foo(["test"], mox.Func(verify_two), bar=1).any_order().returns("anything")

        self.mox.replay_all()

        mock_obj.foo(["test"], "anything", bar=1)
        mock_obj.foo(["test"], "test", bar=1)

        self.mox.verify_all()

    def test_multiple_times(self):
        """Test if MultipleTimesGroup works."""
        mock_obj = self.mox.create_mock_anything()
        mock_obj.method(1).multiple_times().returns(9)
        mock_obj.method(2).returns(10)
        mock_obj.method(3).multiple_times().returns(42)
        self.mox.replay_all()

        actual_one = mock_obj.method(1)
        second_one = mock_obj.method(1)  # This tests multiple_times.
        actual_two = mock_obj.method(2)
        actual_three = mock_obj.method(3)
        mock_obj.method(3)
        mock_obj.method(3)

        self.mox.verify_all()

        self.assertEqual(9, actual_one)

        # Repeated calls should return same number.
        self.assertEqual(9, second_one)
        self.assertEqual(10, actual_two)
        self.assertEqual(42, actual_three)

    def test_multiple_times_using_is_a_parameter(self):
        """Test if MultipleTimesGroup works with a IsA parameter."""
        mock_obj = self.mox.create_mock_anything()
        mock_obj.open()
        mock_obj.method(mox.IsA(str)).multiple_times("IsA").returns(9)
        mock_obj.close()
        self.mox.replay_all()

        mock_obj.open()
        actual_one = mock_obj.method("1")
        second_one = mock_obj.method("2")  # This tests multiple_times.
        mock_obj.close()

        self.mox.verify_all()

        self.assertEqual(9, actual_one)

        # Repeated calls should return same number.
        self.assertEqual(9, second_one)

    def test_multiple_times_using_func(self):
        """Test that the Func is not evaluated more times than necessary.

        If a Func() has side effects, it can cause a passing test to fail.
        """

        self.counter = 0

        def my_func(actual_str):
            """Increment the counter if actual_str == 'foo'."""
            if actual_str == "foo":
                self.counter += 1
            return True

        mock_obj = self.mox.create_mock_anything()
        mock_obj.open()
        mock_obj.method(mox.Func(my_func)).multiple_times()
        mock_obj.close()
        self.mox.replay_all()

        mock_obj.open()
        mock_obj.method("foo")
        mock_obj.method("foo")
        mock_obj.method("not-foo")
        mock_obj.close()

        self.mox.verify_all()

        self.assertEqual(2, self.counter)

    def test_multiple_times_three_methods(self):
        """Test if MultipleTimesGroup works with three or more methods."""
        mock_obj = self.mox.create_mock_anything()
        mock_obj.open()
        mock_obj.method(1).multiple_times().returns(9)
        mock_obj.method(2).multiple_times().returns(8)
        mock_obj.method(3).multiple_times().returns(7)
        mock_obj.method(4).returns(10)
        mock_obj.close()
        self.mox.replay_all()

        mock_obj.open()
        actual_three = mock_obj.method(3)
        mock_obj.method(1)
        actual_two = mock_obj.method(2)
        mock_obj.method(3)
        actual_one = mock_obj.method(1)
        actual_four = mock_obj.method(4)
        mock_obj.close()

        self.assertEqual(9, actual_one)
        self.assertEqual(8, actual_two)
        self.assertEqual(7, actual_three)
        self.assertEqual(10, actual_four)

        self.mox.verify_all()

    def test_multiple_times_missing_one(self):
        """Test if MultipleTimesGroup fails if one method is missing."""
        mock_obj = self.mox.create_mock_anything()
        mock_obj.open()
        mock_obj.method(1).multiple_times().returns(9)
        mock_obj.method(2).multiple_times().returns(8)
        mock_obj.method(3).multiple_times().returns(7)
        mock_obj.method(4).returns(10)
        mock_obj.close()
        self.mox.replay_all()

        mock_obj.open()
        mock_obj.method(3)
        mock_obj.method(2)
        mock_obj.method(3)
        mock_obj.method(3)
        mock_obj.method(2)

        self.assertRaises(mox.UnexpectedMethodCallError, mock_obj.method, 4)

    def test_multiple_times_two_groups(self):
        """Test if MultipleTimesGroup works with a group after a
        MultipleTimesGroup.
        """
        mock_obj = self.mox.create_mock_anything()
        mock_obj.open()
        mock_obj.method(1).multiple_times().returns(9)
        mock_obj.method(3).multiple_times("nr2").returns(42)
        mock_obj.close()
        self.mox.replay_all()

        mock_obj.open()
        actual_one = mock_obj.method(1)
        mock_obj.method(1)
        actual_three = mock_obj.method(3)
        mock_obj.method(3)
        mock_obj.close()

        self.assertEqual(9, actual_one)
        self.assertEqual(42, actual_three)

        self.mox.verify_all()

    def test_multiple_times_two_groups_failure(self):
        """Test if MultipleTimesGroup fails with a group after a
        MultipleTimesGroup.
        """
        mock_obj = self.mox.create_mock_anything()
        mock_obj.open()
        mock_obj.method(1).multiple_times().returns(9)
        mock_obj.method(3).multiple_times("nr2").returns(42)
        mock_obj.close()
        self.mox.replay_all()

        mock_obj.open()
        mock_obj.method(1)
        mock_obj.method(1)
        mock_obj.method(3)

        self.assertRaises(mox.UnexpectedMethodCallError, mock_obj.method, 1)

    def test_with_side_effects(self):
        """Test side effect operations actually modify their target objects."""

        def modifier(mutable_list):
            mutable_list[0] = "mutated"

        mock_obj = self.mox.create_mock_anything()
        mock_obj.ConfigureInOutParameter(["original"]).with_side_effects(modifier)
        mock_obj.WorkWithParameter(["mutated"])
        self.mox.replay_all()

        local_list = ["original"]
        mock_obj.ConfigureInOutParameter(local_list)
        mock_obj.WorkWithParameter(local_list)

        self.mox.verify_all()

    def test_with_side_effects_exception(self):
        """Test side effect operations actually modify their target objects."""

        def modifier(mutable_list):
            mutable_list[0] = "mutated"

        mock_obj = self.mox.create_mock_anything()
        method = mock_obj.ConfigureInOutParameter(["original"])
        method.with_side_effects(modifier).raises(Exception("exception"))
        mock_obj.WorkWithParameter(["mutated"])
        self.mox.replay_all()

        local_list = ["original"]
        self.assertRaises(Exception, mock_obj.ConfigureInOutParameter, local_list)
        mock_obj.WorkWithParameter(local_list)

        self.mox.verify_all()

    def test_stub_out_method(self):
        """Test that a method is replaced with a MockObject."""
        test_obj = TestClass()
        method_type = type(test_obj.other_valid_call)
        # Replace other_valid_call with a mock.
        self.mox.stubout(test_obj, "other_valid_call")
        self.assertTrue(isinstance(test_obj.other_valid_call, mox.MockObject))
        self.assertFalse(type(test_obj.other_valid_call) is method_type)

        test_obj.other_valid_call().returns("foo")
        self.mox.replay_all()

        actual = test_obj.other_valid_call()

        self.mox.verify_all()
        self.mox.unset_stubs()
        self.assertEqual("foo", actual)
        self.assertTrue(type(test_obj.other_valid_call) is method_type)

    def test_stub_out_method__unbound__comparator(self):
        instance = TestClass()
        self.mox.stubout(TestClass, "other_valid_call")

        TestClass.other_valid_call(mox.IgnoreArg()).returns("foo")
        self.mox.replay_all()

        actual = TestClass.other_valid_call(instance)

        self.mox.verify_all()
        self.mox.unset_stubs()
        self.assertEqual("foo", actual)

    def test_stub_out_method__unbound__subclass__comparator(self):
        self.mox.stubout(mox_test_helper.TestClassFromAnotherModule, "value")
        mox_test_helper.TestClassFromAnotherModule.value(mox.IsA(mox_test_helper.ChildClassFromAnotherModule)).returns(
            "foo"
        )
        self.mox.replay_all()

        instance = mox_test_helper.ChildClassFromAnotherModule()
        actual = mox_test_helper.TestClassFromAnotherModule.value(instance)

        self.mox.verify_all()
        self.mox.unset_stubs()
        self.assertEqual("foo", actual)

    def test_stub_ou_method__unbound__with_optional_params(self):
        self.mox = mox.Mox()
        self.mox.stubout(TestClass, "optional_args")
        TestClass.optional_args(mox.IgnoreArg(), foo=2)
        self.mox.replay_all()

        t = TestClass()
        TestClass.optional_args(t, foo=2)

        self.mox.verify_all()
        self.mox.unset_stubs()

    def test_stub_out_method__unbound__actual_instance(self):
        instance = TestClass()
        self.mox.stubout(TestClass, "other_valid_call")

        TestClass.other_valid_call(instance).returns("foo")
        self.mox.replay_all()

        actual = TestClass.other_valid_call(instance)

        self.mox.verify_all()
        self.mox.unset_stubs()
        self.assertEqual("foo", actual)

    def test_stub_out_method__unbound__different_instance(self):
        instance = TestClass()
        self.mox.stubout(TestClass, "other_valid_call")

        TestClass.other_valid_call(instance).returns("foo")
        self.mox.replay_all()

        assert len(self.mox.stubs.cache) == 1
        # This should fail, since the instances are different
        self.assertRaises(mox.UnexpectedMethodCallError, TestClass.other_valid_call, "wrong self")
        self.assertRaises(mox.SwallowedExceptionError, self.mox.verify_all)
        assert len(self.mox.stubs.cache) == 0

    def test_stub_out_method__unbound__named_using_positional(self):
        """Check positional parameters can be matched to keyword arguments."""
        self.mox.stubout(mox_test_helper.ExampleClass, "named_params")
        instance = mox_test_helper.ExampleClass()
        mox_test_helper.ExampleClass.named_params(instance, "foo", baz=None)
        self.mox.replay_all()

        mox_test_helper.ExampleClass.named_params(instance, "foo", baz=None)

        self.mox.verify_all()
        self.mox.unset_stubs()

    def test_stub_out_method__unbound__named_using_positional__some_positional(self):
        """Check positional parameters can be matched to keyword arguments."""
        self.mox.stubout(mox_test_helper.ExampleClass, "test_method")
        instance = mox_test_helper.ExampleClass()
        mox_test_helper.ExampleClass.test_method(instance, "one", "two", "nine")
        self.mox.replay_all()

        mox_test_helper.ExampleClass.test_method(instance, "one", "two", "nine")

        self.mox.verify_all()
        self.mox.unset_stubs()

    def test_stub_out_method__unbound__special_args(self):
        self.mox.stubout(mox_test_helper.ExampleClass, "special_args")
        instance = mox_test_helper.ExampleClass()
        mox_test_helper.ExampleClass.special_args(instance, "foo", None, bar="bar")
        self.mox.replay_all()

        mox_test_helper.ExampleClass.special_args(instance, "foo", None, bar="bar")

        self.mox.verify_all()
        self.mox.unset_stubs()

    def test_stub_out_method__bound__simple_test(self):
        t = self.mox.create_mock(TestClass)

        t.method_with_args(mox.IgnoreArg(), mox.IgnoreArg()).returns("foo")
        self.mox.replay_all()

        actual = t.method_with_args(None, None)

        self.mox.verify_all()
        self.mox.unset_stubs()
        self.assertEqual("foo", actual)

    def test_stub_out_method__bound__named_using_positional(self):
        """Check positional parameters can be matched to keyword arguments."""
        self.mox.stubout(mox_test_helper.ExampleClass, "named_params")
        instance = mox_test_helper.ExampleClass()
        instance.named_params("foo", baz=None)
        self.mox.replay_all()

        instance.named_params("foo", baz=None)

        self.mox.verify_all()
        self.mox.unset_stubs()

    def test_stub_out_method__bound__named_using_positional__some_positional(self):
        """Check positional parameters can be matched to keyword arguments."""
        self.mox.stubout(mox_test_helper.ExampleClass, "test_method")
        instance = mox_test_helper.ExampleClass()
        instance.test_method(instance, "one", "two", "nine")
        self.mox.replay_all()

        instance.test_method(instance, "one", "two", "nine")

        self.mox.verify_all()
        self.mox.unset_stubs()

    def test_stub_out_method__bound__special_args(self):
        self.mox.stubout(mox_test_helper.ExampleClass, "special_args")
        instance = mox_test_helper.ExampleClass()
        instance.special_args(instance, "foo", None, bar="bar")
        self.mox.replay_all()

        instance.special_args(instance, "foo", None, bar="bar")

        self.mox.verify_all()
        self.mox.unset_stubs()

    def test_stub_out_method__func__propgates_exceptions(self):
        """Errors in a Func comparator should propagate to the calling
        method."""

        class TestException(Exception):
            pass

        def raise_exception_on_not_one(value):
            if value == 1:
                return True
            else:
                raise TestException

        test_obj = TestClass()
        self.mox.stubout(test_obj, "method_with_args")
        test_obj.method_with_args(mox.IgnoreArg(), mox.Func(raise_exception_on_not_one)).returns(1)
        test_obj.method_with_args(mox.IgnoreArg(), mox.Func(raise_exception_on_not_one)).returns(1)
        self.mox.replay_all()

        self.assertEqual(test_obj.method_with_args("ignored", 1), 1)
        self.assertRaises(TestException, test_obj.method_with_args, "ignored", 2)

        self.mox.verify_all()
        self.mox.unset_stubs()

    def test_stubout__method__explicit_contains__for__set(self):
        """Test that explicit __contains__() for a set gets mocked with
        success."""
        stub = self.mox.stubout(TestClass, "SOME_CLASS_SET")
        TestClass.SOME_CLASS_SET.__contains__("x").returns(True)

        dummy = TestClass()

        self.mox.replay_all()

        result = "x" in dummy.SOME_CLASS_SET

        self.mox.verify_all()

        self.assertTrue(result)
        assert TestClass.SOME_CLASS_SET == stub

    def test_stub_out__signature_matching_init_(self):
        stub = self.mox.stubout(mox_test_helper.ExampleClass, "__init__")
        mox_test_helper.ExampleClass.__init__(mox.IgnoreArg())
        self.mox.replay_all()

        # Create an instance of a child class, which calls the parent
        # __init__
        mox_test_helper.ChildExampleClass()

        assert mox_test_helper.ExampleClass.__init__ == stub
        self.mox.verify_all()
        self.mox.unset_stubs()

    def test_stub_out_class__old_style(self):
        """Test a mocked class whose __init__ returns a Mock."""
        stub = self.mox.stubout(mox_test_helper, "TestClassFromAnotherModule")
        self.assertIsInstance(mox_test_helper.TestClassFromAnotherModule, mox.MockObject)

        mock_instance = self.mox.create_mock(mox_test_helper.TestClassFromAnotherModule)
        mox_test_helper.TestClassFromAnotherModule().returns(mock_instance)
        mock_instance.value().returns("mock instance")

        self.mox.replay_all()

        a_mock = mox_test_helper.TestClassFromAnotherModule()
        actual = a_mock.value()

        assert mox_test_helper.TestClassFromAnotherModule == stub
        self.mox.verify_all()
        self.mox.unset_stubs()
        self.assertEqual("mock instance", actual)

    def test_stub_out_class(self):
        factory = self.mox.stubout_class(mox_test_helper, "CallableClass")

        # Instance one
        mock_one = mox_test_helper.CallableClass(1, 2)
        mock_one.value().returns("mock")

        # Instance two
        mock_two = mox_test_helper.CallableClass(8, 9)
        mock_two("one").returns("called mock")

        self.mox.replay_all()

        one = mox_test_helper.CallableClass(1, 2)
        actual_one = one.value()

        two = mox_test_helper.CallableClass(8, 9)
        actual_two = two("one")

        self.mox.verify_all()
        assert mox_test_helper.CallableClass == factory
        self.mox.unset_stubs()

        # Verify the correct mocks were returned
        self.assertEqual(mock_one, one)
        self.assertEqual(mock_two, two)

        # Verify
        self.assertEqual("mock", actual_one)
        self.assertEqual("called mock", actual_two)

    def test_stub_out_class_with_meta_class(self):
        factory = self.mox.stubout_class(mox_test_helper, "ChildClassWithMetaClass")

        mock_one = mox_test_helper.ChildClassWithMetaClass(kw=1)
        mock_one.value().returns("mock")

        self.mox.replay_all()

        one = mox_test_helper.ChildClassWithMetaClass(kw=1)
        actual_one = one.value()

        self.mox.verify_all()
        assert mox_test_helper.ChildClassWithMetaClass == factory
        self.mox.unset_stubs()

        # Verify the correct mocks were returned
        self.assertEqual(mock_one, one)

        # Verify
        self.assertEqual("mock", actual_one)
        self.assertEqual("meta", one.x)

    try:
        import abc

        # I'd use the unittest skipping decorators for this but I want to
        # support older versions of Python that don't have them.

        def test_stub_out_class__a_b_c_meta(self):
            self.mox.stubout_class(mox_test_helper, "CallableSubclassOfMyDictABC")
            mock_foo = mox_test_helper.CallableSubclassOfMyDictABC(foo="!mock bar")
            mock_foo["foo"].returns("mock bar")
            mock_spam = mox_test_helper.CallableSubclassOfMyDictABC(spam="!mock eggs")
            mock_spam("beans").returns("called mock")

            self.mox.replay_all()

            foo = mox_test_helper.CallableSubclassOfMyDictABC(foo="!mock bar")
            actual_foo_bar = foo["foo"]

            spam = mox_test_helper.CallableSubclassOfMyDictABC(spam="!mock eggs")
            actual_spam = spam("beans")

            self.mox.verify_all()
            self.mox.unset_stubs()

            # Verify the correct mocks were returned
            self.assertEqual(mock_foo, foo)
            self.assertEqual(mock_spam, spam)

            # Verify
            self.assertEqual("mock bar", actual_foo_bar)
            self.assertEqual("called mock", actual_spam)

    except ImportError:
        print("testStubOutClass_ABCMeta. ... Skipped - no abc module", file=sys.stderr)

    def test_stub_out_class__not_a_class(self):
        self.assertRaises(TypeError, self.mox.stubout_class, mox_test_helper, "MyTestFunction")

    def test_stub_out_class_not_enough_created(self):
        self.mox.stubout_class(mox_test_helper, "CallableClass")

        mox_test_helper.CallableClass(1, 2)
        mox_test_helper.CallableClass(8, 9)

        self.mox.replay_all()
        mox_test_helper.CallableClass(1, 2)

        assert len(self.mox.stubs.cache) == 1
        self.assertRaises(mox.ExpectedMockCreationError, self.mox.verify_all)
        assert len(self.mox.stubs.cache) == 0

    def test_stub_out_class_wrong_signature(self):
        factory = self.mox.stubout_class(mox_test_helper, "CallableClass")

        self.assertRaises(AttributeError, mox_test_helper.CallableClass)

        assert mox_test_helper.CallableClass == factory
        self.mox.unset_stubs()

    def test_stub_out_class_wrong_parameters(self):
        factory = self.mox.stubout_class(mox_test_helper, "CallableClass")

        mox_test_helper.CallableClass(1, 2)

        self.mox.replay_all()

        self.assertRaises(mox.UnexpectedMethodCallError, mox_test_helper.CallableClass, 8, 9)
        assert mox_test_helper.CallableClass == factory
        self.mox.unset_stubs()

    def test_stub_out_class_too_many_created(self):
        factory = self.mox.stubout_class(mox_test_helper, "CallableClass")

        mox_test_helper.CallableClass(1, 2)

        self.mox.replay_all()
        mox_test_helper.CallableClass(1, 2)
        self.assertRaises(mox.UnexpectedMockCreationError, mox_test_helper.CallableClass, 8, 9)

        assert mox_test_helper.CallableClass == factory
        self.mox.unset_stubs()

    def test_warns_user_if_mocking_mock(self):
        """Test that user is warned if they try to stub out a MockAnything."""
        stub = self.mox.stubout(TestClass, "my_static_method")
        self.assertRaises(TypeError, self.mox.stubout, TestClass, "my_static_method")
        assert TestClass.my_static_method == stub

    def test_stub_out_first_class_method_verifies_signature(self):
        stub = self.mox.stubout(mox_test_helper, "MyTestFunction")
        assert mox_test_helper.MyTestFunction == stub

        # Wrong number of arguments
        self.assertRaises(AttributeError, mox_test_helper.MyTestFunction, 1)
        self.mox.unset_stubs()

    def test_method_signature_verification(self):
        options = [
            ((), {}, True, False),
            ((), {}, True, True),
            ((1,), {}, True, False),
            ((1,), {}, True, True),
            ((), {"nine": 2}, True, False),
            ((), {"nine": 2}, True, True),
            ((1, 2), {}, False, False),
            ((1, 2), {}, False, True),
            ((1, 2, 3), {}, False, False),
            ((1, 2, 3), {}, False, True),
            ((1, 2), {"nine": 3}, False, False),
            ((1, 2), {"nine": 3}, False, True),
            ((1, 2, 3, 4), {}, True, False),
            ((1, 2, 3, 4), {}, True, True),
        ]

        for args, kwargs, raises, stub_class in options:
            if stub_class:
                self.mox.stubout(mox_test_helper.ExampleClass, "test_method")
                obj = mox_test_helper.ExampleClass()
            else:
                obj = mox_test_helper.ExampleClass()
                self.mox.stubout(obj, "test_method")

            if raises:
                self.assertRaises(AttributeError, obj.test_method, *args, **kwargs)
            else:
                obj.test_method(*args, **kwargs)
            self.mox.unset_stubs()

    def test_stub_out_object(self):
        """Test that object is replaced with a Mock."""

        class foo(object):
            def __init__(self):
                self.obj = TestClass()

        foo = foo()
        stub = self.mox.stubout(foo, "obj")
        self.assertIsInstance(foo.obj, mox.MockObject)
        foo.obj.valid_call()
        self.mox.replay_all()

        foo.obj.valid_call()

        self.mox.verify_all()
        assert foo.obj == stub
        self.mox.unset_stubs()
        self.assertNotIsInstance(foo.obj, mox.MockObject)

    def test_stub_out_re_works(self):
        stub = self.mox.stubout(re, "search")

        re.search("a", "ivan").returns("true")

        self.mox.replay_all()
        result = TestClass().re_search()
        self.mox.verify_all()

        assert re.search == stub
        self.mox.unset_stubs()

        self.assertEqual(result, "true")

    def test_forgot_replay_helpful_message(self):
        """If there is an AttributeError on a MockMethod, give users a helpful
        msg."""
        foo = self.mox.create_mock_anything()
        bar = self.mox.create_mock_anything()
        foo.getbar().returns(bar)
        bar.show_me_the_money()
        # Forgot to replay!
        try:
            foo.getbar().show_me_the_money()
        except AttributeError as e:
            self.assertEqual(
                'MockMethod has no attribute "show_me_the_money". Did you remember to put your mocks in replay mode?',
                str(e),
            )

    def test_swallowed_unknown_method_call(self):
        """Test that a swallowed UnknownMethodCallError will be re-raised."""
        dummy = self.mox.create_mock(TestClass)
        dummy._replay()

        def call():
            try:
                dummy.invalid_call()
            except mox.UnknownMethodCallError:
                pass

        # UnknownMethodCallError swallowed
        call()

        self.assertRaises(mox.SwallowedExceptionError, self.mox.verify_all)

    def test_swallowed_unexpected_mock_creation(self):
        """Test that a swallowed UnexpectedMockCreationError will be
        re-raised."""
        factory = self.mox.stubout_class(mox_test_helper, "CallableClass")
        self.mox.replay_all()

        def call():
            try:
                mox_test_helper.CallableClass(1, 2)
            except mox.UnexpectedMockCreationError:
                pass

        # UnexpectedMockCreationError swallowed
        call()

        assert mox_test_helper.CallableClass == factory
        assert len(self.mox.stubs.cache) == 1
        self.assertRaises(mox.SwallowedExceptionError, self.mox.verify_all)
        assert len(self.mox.stubs.cache) == 0

    def test_swallowed_unexpected_method_call__wrong_method(self):
        """Test that a swallowed UnexpectedMethodCallError will be re-raised.

        This case is an extraneous method call."""
        mock_obj = self.mox.create_mock_anything()
        mock_obj.open()
        self.mox.replay_all()

        def call():
            mock_obj.open()
            try:
                mock_obj.close()
            except mox.UnexpectedMethodCallError:
                pass

        # UnexpectedMethodCall swallowed
        call()

        self.assertRaises(mox.SwallowedExceptionError, self.mox.verify_all)

    def test_swallowed_unexpected_method_call__wrong_arguments(self):
        """Test that a swallowed UnexpectedMethodCallError will be re-raised.

        This case is an extraneous method call."""
        mock_obj = self.mox.create_mock_anything()
        mock_obj.open()
        self.mox.replay_all()

        def call():
            try:
                mock_obj.open(1)
            except mox.UnexpectedMethodCallError:
                pass

        # UnexpectedMethodCall swallowed
        call()

        self.assertRaises(mox.SwallowedExceptionError, self.mox.verify_all)

    def test_swallowed_unexpected_method_call__unordered_group(self):
        """Test that a swallowed UnexpectedMethodCallError will be re-raised.

        This case is an extraneous method call in an unordered group."""
        mock_obj = self.mox.create_mock_anything()
        mock_obj.open().any_order()
        mock_obj.close().any_order()
        self.mox.replay_all()

        def call():
            mock_obj.close()
            try:
                mock_obj.open(1)
            except mox.UnexpectedMethodCallError:
                pass

        # UnexpectedMethodCall swallowed
        call()

        self.assertRaises(mox.SwallowedExceptionError, self.mox.verify_all)

    def test_swallowed_unexpected_method_call__multiple_times_group(self):
        """Test that a swallowed UnexpectedMethodCallError will be re-raised.

        This case is an extraneous method call in a multiple times group."""
        mock_obj = self.mox.create_mock_anything()
        mock_obj.open().multiple_times()
        self.mox.replay_all()

        def call():
            try:
                mock_obj.open(1)
            except mox.UnexpectedMethodCallError:
                pass

        # UnexpectedMethodCall swallowed
        call()

        self.assertRaises(mox.SwallowedExceptionError, self.mox.verify_all)


class ReplayTest(unittest.TestCase):
    """Verify Replay works properly."""

    def test_replay(self):
        """Replay should put objects into replay mode."""
        mock_obj = mox.MockObject(TestClass)
        self.assertFalse(mock_obj._replay_mode)
        mox.replay(mock_obj)
        self.assertTrue(mock_obj._replay_mode)


class VerifyTest(unittest.TestCase):
    """Verify 'verify' works properly."""

    def test_verify(self):
        """Verify should be called for all objects.

        This should throw an exception because the expected behavior did not occur."""
        mock_obj = mox.MockObject(TestClass)
        mock_obj.valid_call()
        mock_obj._replay()
        self.assertRaises(mox.ExpectedMethodCallsError, mox.verify, mock_obj)


class ResetTest(unittest.TestCase):
    """Verify 'reset' works properly."""

    def test_reset(self):
        """Should empty all queues and put mocks in record mode."""
        mock_obj = mox.MockObject(TestClass)
        mock_obj.valid_call()
        self.assertFalse(mock_obj._replay_mode)
        mock_obj._replay()
        self.assertTrue(mock_obj._replay_mode)
        self.assertEqual(1, len(mock_obj._expected_calls_queue))

        mox.reset(mock_obj)
        self.assertFalse(mock_obj._replay_mode)
        self.assertEqual(0, len(mock_obj._expected_calls_queue))


if __name__ == "__main__":
    unittest.main()
