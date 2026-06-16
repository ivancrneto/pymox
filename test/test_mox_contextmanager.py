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
"""Tests for the Mox manager via the context-manager API."""

import re
import unittest

import pytest

import mox

from . import mox_test_helper
from .mox_test_fixtures_helper import CallableClass, InheritsFromCallable, TestClass


class MoxContextManagerTest:
    """Verify Mox works correctly when using context managers."""

    __test__ = True

    def test_create_object_using_simple_imported_module_class_method(self):
        """Mox should create a mock object for a class from a module imported
        using a simple 'import module' statement"""

        with mox.stubout(mox_test_helper.ExampleClass, "class_method") as stub:
            example_obj = mox.create(mox_test_helper.ExampleClass)
            mox_test_helper.ExampleClass.class_method().returns(example_obj)

        def call_helper_class_method():
            return mox_test_helper.ExampleClass.class_method()

        expected_obj = call_helper_class_method()
        mox.verify(stub, example_obj)

        assert expected_obj == example_obj

    def test_verify_object_with_complete_replay(self):
        """Mox should replay and verify all objects it created."""

        mock_obj = mox.create(TestClass)
        with mox.expect:
            mock_obj.valid_call()
            mock_obj.valid_call_with_args(mox.is_a(TestClass))

        mock_obj.valid_call()
        mock_obj.valid_call_with_args(TestClass("some_value"))
        mox.verify(mock_obj)

    def test_verify_object_with_incomplete_replay(self):
        """Mox should raise an exception if a mock didn't replay completely."""

        mock_obj = mox.create(TestClass)
        with mox.expect:
            mock_obj.valid_call()

        # valid_call() is never made
        with pytest.raises(mox.ExpectedMethodCallsError):
            mox.verify(mock_obj)

    def test_entire_workflow(self):
        """Test the whole work flow."""
        mock_obj = mox.create(TestClass)
        with mox.expect:
            mock_obj.valid_call().returns("yes")

        ret_val = mock_obj.valid_call()
        assert ret_val == "yes"
        mox.verify(mock_obj)

    def test_signature_matching_with_comparator_as_first_arg(self):
        """Test that the first argument can be a comparator."""

        def verify_len(val):
            """This will raise an exception when not given a list.

            This exception will be raised when trying to infer/validate the
            method signature.
            """
            return len(val) != 1

        mock_obj = mox.create(TestClass)

        # This intentionally does not name the 'nine' param, so it triggers
        # deeper inspection.
        with mox.expect:
            mock_obj.method_with_args(mox.Func(verify_len), mox.IgnoreArg(), None)

        mock_obj.method_with_args([1, 2], "foo", None)

        mox.verify(mock_obj)

    def test_callable_object(self):
        """Test recording calls to a callable object works."""
        mock_obj = mox.create(CallableClass)
        with mox.expect:
            mock_obj("foo").returns("qux")

        ret_val = mock_obj("foo")
        assert "qux" == ret_val
        mox.verify(mock_obj)

    def test_inherited_callable_object(self):
        """Test recording calls to an object inheriting from a callable
        object."""
        mock_obj = mox.create(InheritsFromCallable)
        with mox.expect:
            mock_obj("foo").returns("qux")

        ret_val = mock_obj("foo")
        assert "qux" == ret_val
        mox.verify(mock_obj)

    def test_callable_object_with_bad_call(self):
        """Test verifying calls to a callable object works."""
        mock_obj = mox.create(CallableClass)
        with mox.expect:
            mock_obj("foo").returns("qux")

        with pytest.raises(mox.UnexpectedMethodCallError):
            mock_obj("ZOOBAZ")

    def test_builin_with_bad_call(self):
        """Test verifying calls to a builtin works."""
        with mox.stubout("os.getcwd") as mock_obj, mox.expect:
            mock_obj().returns("/")

        with pytest.raises(mox.UnexpectedMethodCallError, match=r'Unexpected method call "getcwd\(\) -> None"'):
            mock_obj()
            mock_obj()

    def test_callable_object_verifies_signature(self):
        mock_obj = mox.create(CallableClass)

        # Too many arguments
        with pytest.raises(AttributeError):
            mock_obj("foo", "bar")

    def test_unordered_group(self):
        """Test that using one unordered group works."""
        mock_obj = mox.create.any()
        with mox.expect:
            mock_obj.method(1).any_order()
            mock_obj.method(2).any_order()

        mock_obj.method(2)
        mock_obj.method(1)

        mox.verify(mock_obj)

    def test_unordered_groups_inline(self):
        """Unordered groups should work in the context of ordered calls."""
        mock_obj = mox.create.any()
        with mox.expect:
            mock_obj.open()
            mock_obj.method(1).any_order()
            mock_obj.method(2).any_order()
            mock_obj.close()

        mock_obj.open()
        mock_obj.method(2)
        mock_obj.method(1)
        mock_obj.close()

        mox.verify(mock_obj)

    def test_multiple_unorderd_groups(self):
        """Multiple unoreded groups should work."""
        mock_obj = mox.create.any()
        with mox.expect:
            mock_obj.method(1).any_order()
            mock_obj.method(2).any_order()
            mock_obj.foo().any_order("group2")
            mock_obj.bar().any_order("group2")

        mock_obj.method(2)
        mock_obj.method(1)
        mock_obj.bar()
        mock_obj.foo()

        mox.verify(mock_obj)

    def test_multiple_unorderd_groups_out_of_order(self):
        """Multiple unordered groups should maintain external order"""
        mock_obj = mox.create.any()
        with mox.expect:
            mock_obj.method(1).any_order()
            mock_obj.method(2).any_order()
            mock_obj.foo().any_order("group2")
            mock_obj.bar().any_order("group2")

        mock_obj.method(2)
        with pytest.raises(mox.UnexpectedMethodCallError):
            mock_obj.bar()

    def test_unordered_group_with_return_value(self):
        """Unordered groups should work with return values."""
        mock_obj = mox.create.any()
        with mox.expect:
            mock_obj.open()
            mock_obj.method(1).any_order().returns(9)
            mock_obj.method(2).any_order().returns(10)
            mock_obj.close()

        mock_obj.open()
        actual_two = mock_obj.method(2)
        actual_one = mock_obj.method(1)
        mock_obj.close()

        assert actual_one == 9
        assert actual_two == 10

        mox.verify(mock_obj)

    def test_unordered_group_with_comparator(self):
        """Unordered groups should work with comparators"""

        def verify_one(cmd):
            if not isinstance(cmd, str):
                self.fail("Unexpected type passed to comparator: " + str(cmd))
            return cmd == "test"

        def verify_two(cmd):
            return True

        mock_obj = mox.create.any()
        with mox.expect:
            mock_obj.foo(["test"], mox.Func(verify_one), bar=1).any_order().returns("yes test")
            mock_obj.foo(["test"], mox.Func(verify_two), bar=1).any_order().returns("anything")

        mock_obj.foo(["test"], "anything", bar=1)
        mock_obj.foo(["test"], "test", bar=1)

        mox.verify(mock_obj)

    def test_multiple_times(self):
        """Test if MultipleTimesGroup works."""
        mock_obj = mox.create.any()
        with mox.expect:
            mock_obj.method(1).multiple_times().returns(9)
            mock_obj.method(2).returns(10)
            mock_obj.method(3).multiple_times().returns(42)

        actual_one = mock_obj.method(1)
        second_one = mock_obj.method(1)  # This tests multiple_times.
        actual_two = mock_obj.method(2)
        actual_three = mock_obj.method(3)
        mock_obj.method(3)
        mock_obj.method(3)

        mox.verify(mock_obj)

        assert actual_one == 9

        # Repeated calls should return same number.
        assert second_one == 9
        assert actual_two == 10
        assert actual_three == 42

    def test_multiple_times_using_is_a_parameter(self):
        """Test if MultipleTimesGroup works with a is_a parameter."""
        mock_obj = mox.create.any()
        with mox.expect:
            mock_obj.open()
            mock_obj.method(mox.is_a(str)).multiple_times("is_a").returns(9)
            mock_obj.close()

        mock_obj.open()
        actual_one = mock_obj.method("1")
        second_one = mock_obj.method("2")  # This tests multiple_times.
        mock_obj.close()

        mox.verify(mock_obj)

        assert actual_one == 9

        # Repeated calls should return same number.
        assert second_one == 9

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

        mock_obj = mox.create.any()
        with mox.expect:
            mock_obj.open()
            mock_obj.method(mox.func(my_func)).multiple_times()
            mock_obj.close()

        mock_obj.open()
        mock_obj.method("foo")
        mock_obj.method("foo")
        mock_obj.method("not-foo")
        mock_obj.close()

        mox.verify(mock_obj)

        assert self.counter == 2

    def test_multiple_times_three_methods(self):
        """Test if MultipleTimesGroup works with three or more methods."""
        mock_obj = mox.create.any()
        with mox.expect:
            mock_obj.open()
            mock_obj.method(1).multiple_times().returns(9)
            mock_obj.method(2).multiple_times().returns(8)
            mock_obj.method(3).multiple_times().returns(7)
            mock_obj.method(4).returns(10)
            mock_obj.close()

        mock_obj.open()
        actual_three = mock_obj.method(3)
        mock_obj.method(1)
        actual_two = mock_obj.method(2)
        mock_obj.method(3)
        actual_one = mock_obj.method(1)
        actual_four = mock_obj.method(4)
        mock_obj.close()

        assert actual_one == 9
        assert actual_two == 8
        assert actual_three == 7
        assert actual_four == 10

        mox.verify(mock_obj)

    def test_multiple_times_missing_one(self):
        """Test if MultipleTimesGroup fails if one method is missing."""
        mock_obj = mox.create.any()
        with mox.expect:
            mock_obj.open()
            mock_obj.method(1).multiple_times().returns(9)
            mock_obj.method(2).multiple_times().returns(8)
            mock_obj.method(3).multiple_times().returns(7)
            mock_obj.method(4).returns(10)
            mock_obj.close()

        mock_obj.open()
        mock_obj.method(3)
        mock_obj.method(2)
        mock_obj.method(3)
        mock_obj.method(3)
        mock_obj.method(2)

        with pytest.raises(mox.UnexpectedMethodCallError):
            mock_obj.method(4)

    def test_multiple_times_two_groups(self):
        """Test if MultipleTimesGroup works with a group after a
        MultipleTimesGroup.
        """
        mock_obj = mox.create.any()
        with mox.expect:
            mock_obj.open()
            mock_obj.method(1).multiple_times().returns(9)
            mock_obj.method(3).multiple_times("nr2").returns(42)
            mock_obj.close()

        mock_obj.open()
        actual_one = mock_obj.method(1)
        mock_obj.method(1)
        actual_three = mock_obj.method(3)
        mock_obj.method(3)
        mock_obj.close()

        assert actual_one == 9
        assert actual_three == 42

        mox.verify(mock_obj)

    def test_multiple_times_two_groups_failure(self):
        """Test if MultipleTimesGroup fails with a group after a
        MultipleTimesGroup.
        """
        mock_obj = mox.create.any()
        with mox.expect:
            mock_obj.open()
            mock_obj.method(1).multiple_times().returns(9)
            mock_obj.method(3).multiple_times("nr2").returns(42)
            mock_obj.close()

        mock_obj.open()
        mock_obj.method(1)
        mock_obj.method(1)
        mock_obj.method(3)

        with pytest.raises(mox.UnexpectedMethodCallError):
            mock_obj.method(1)

    def test_with_side_effects(self):
        """Test side effect operations actually modify their target objects."""

        def modifier(mutable_list):
            mutable_list[0] = "mutated"

        mock_obj = mox.create.any()
        with mox.expect:
            mock_obj.configure_in_out_parameter(["original"]).with_side_effects(modifier)
            mock_obj.work_with_parameter(["mutated"])

        local_list = ["original"]
        mock_obj.configure_in_out_parameter(local_list)
        mock_obj.work_with_parameter(local_list)

        mox.verify(mock_obj)

    def test_with_side_effects_exception(self):
        """Test side effect operations actually modify their target objects."""

        def modifier(mutable_list):
            mutable_list[0] = "mutated"

        mock_obj = mox.create.any()
        with mox.expect:
            method = mock_obj.configure_in_out_parameter(["original"])
            method.with_side_effects(modifier).raises(Exception("exception"))
            mock_obj.work_with_parameter(["mutated"])

        local_list = ["original"]
        with pytest.raises(Exception):
            mock_obj.configure_in_out_parameter(local_list)
        mock_obj.work_with_parameter(local_list)

        mox.verify(mock_obj)

    def test_stub_out_method(self):
        """Test that a method is replaced with a MockObject."""
        test_obj = TestClass()
        method_type = type(test_obj.other_valid_call)
        # Replace other_valid_call with a mock.
        with mox.stubout(test_obj, "other_valid_call") as stub:
            ...

        assert isinstance(test_obj.other_valid_call, mox.MockObject)
        assert type(test_obj.other_valid_call) is not method_type

        with stub._expect:
            test_obj.other_valid_call().returns("foo")

        actual = test_obj.other_valid_call()

        mox.verify(stub)

        mox.Mox.unset_stubs_for_id(stub._mox_id)
        assert "foo" == actual
        assert type(test_obj.other_valid_call) is method_type

    def test_stub_out_many_method_another_object(self):
        """Test that a method is replaced with a MockObject when stubout.many is used."""
        from .mox_test_helper import TestClass

        test_obj = TestClass(parent=TestClass())
        test_obj.another_parent = TestClass()

        method_type = type(test_obj.valid_call)
        method_type_other = type(test_obj.other_valid_call)
        with (
            mox.stubout.many(
                ["test.mox_test_helper.TestClass.valid_call", True],
                ["test.mox_test_helper.TestClass.other_valid_call", True],
            ) as (mock_valid, mock_other_valid),
            mox.expect,
        ):
            mock_valid().returns("foo")
            mock_other_valid().returns("bar")

        assert isinstance(test_obj.valid_call, mox.MockAnything)
        assert isinstance(test_obj.other_valid_call, mox.MockAnything)
        assert type(test_obj.valid_call) is not method_type
        assert type(test_obj.other_valid_call) is not method_type_other

        actual_parent = test_obj.parent.valid_call()
        actual_another_parent = test_obj.parent.other_valid_call()

        mox.verify(mock_valid, mock_other_valid)

        mox.Mox.unset_stubs_for_id(mock_valid._mox_id)
        mox.Mox.unset_stubs_for_id(mock_other_valid._mox_id)
        assert actual_parent == "foo"
        assert actual_another_parent == "bar"
        assert type(test_obj.parent.valid_call) is method_type
        assert type(test_obj.parent.valid_call) is method_type_other

    def test_stub_out_method_another_object_not_use_mock_anything(self):
        """Test that a method is replaced with a MockObject when not using mock anything."""
        test_obj = TestClass(parent=TestClass())
        method_type = type(test_obj.parent.valid_call)
        with mox.stubout(test_obj, "parent") as stub:
            ...

        assert isinstance(test_obj.parent.valid_call, mox.MockMethod)
        assert type(test_obj.parent.valid_call) is not method_type

        with pytest.raises(
            mox.exceptions.UnknownMethodCallError, match="Method called is not a member of the object: non_existing"
        ):
            _ = test_obj.parent.non_existing

        with stub._expect:
            test_obj.parent.valid_call().returns("foo")

        actual = test_obj.parent.valid_call()

        with pytest.raises(
            mox.exceptions.SwallowedExceptionError, match="Method called is not a member of the object: non_existing"
        ):
            mox.verify(stub)

        mox.Mox.unset_stubs_for_id(stub._mox_id)
        assert actual == "foo"
        assert type(test_obj.parent.valid_call) is method_type

    def test_stub_out_method_another_object_use_mock_anything(self):
        """Test that a method is replaced with a MockMethod when using mock anything."""
        test_obj = TestClass(parent=TestClass())
        method_type = type(test_obj.parent.valid_call)
        with mox.stubout(test_obj, "parent", True) as stub:
            ...

        assert isinstance(test_obj.parent.valid_call, mox.MockMethod)
        assert isinstance(test_obj.parent.non_existing, mox.MockMethod)
        assert type(test_obj.parent.valid_call) is not method_type

        with stub._expect:
            test_obj.parent.valid_call().returns("foo")
            test_obj.parent.non_existing().returns("now it exists")

        actual = test_obj.parent.valid_call()
        exists = test_obj.parent.non_existing()

        mox.verify(stub)

        mox.Mox.unset_stubs_for_id(stub._mox_id)
        assert actual == "foo"
        assert exists == "now it exists"
        assert type(test_obj.parent.valid_call) is method_type
        with pytest.raises(AttributeError):
            _ = test_obj.parent.non_existing

    def test_stub_out_method__unbound__comparator(self):
        instance = TestClass()
        with mox.stubout(TestClass, "other_valid_call") as stub, mox.expect:
            TestClass.other_valid_call(mox.IgnoreArg()).returns("foo")

        actual = TestClass.other_valid_call(instance)

        mox.verify(stub)
        m = mox.Mox._instances[stub._mox_id]
        m.unset_stubs()
        assert "foo" == actual

    def test_stub_out_method__unbound__subclass__comparator(self):
        with mox.stubout(mox_test_helper.TestClassFromAnotherModule, "value") as stub:
            ...

        with stub._expect:
            mox_test_helper.TestClassFromAnotherModule.value(
                mox.is_a(mox_test_helper.ChildClassFromAnotherModule)
            ).returns("foo")

        instance = mox_test_helper.ChildClassFromAnotherModule()
        actual = mox_test_helper.TestClassFromAnotherModule.value(instance)

        mox.verify(stub)
        m = mox.Mox._instances[stub._mox_id]
        m.unset_stubs()
        assert "foo" == actual

    def test_stub_ou_method__unbound__with_optional_params(self):
        with mox.stubout(mox_test_helper.TestClassFromAnotherModule, "value") as stub:
            ...

        with stub._expect:
            TestClass.optional_args(mox.IgnoreArg(), foo=2)

        t = TestClass()
        TestClass.optional_args(t, foo=2)

        mox.verify(stub)
        m = mox.Mox._instances[stub._mox_id]
        m.unset_stubs()

    def test_stub_out_method__unbound__actual_instance(self):
        instance = TestClass()
        with mox.stubout(TestClass, "other_valid_call") as stub, mox.expect:
            TestClass.other_valid_call(instance).returns("foo")

        actual = TestClass.other_valid_call(instance)

        mox.verify(stub)
        m = mox.Mox._instances[stub._mox_id]
        m.unset_stubs()
        assert "foo" == actual

    def test_stub_out_method__unbound__different_instance(self):
        instance = TestClass()
        with mox.stubout(TestClass, "other_valid_call") as stub, mox.expect:
            TestClass.other_valid_call(instance).returns("foo")

        m = mox.Mox._instances[stub._mox_id]
        assert len(m.stubs.cache) == 1

        # This should fail, since the instances are different
        with pytest.raises(mox.UnexpectedMethodCallError):
            TestClass.other_valid_call("wrong self")

        with pytest.raises(mox.SwallowedExceptionError):
            m.verify_all()
        assert len(m.stubs.cache) == 0

    def test_stub_out_method__unbound__named_using_positional(self):
        """Check positional parameters can be matched to keyword arguments."""
        with mox.stubout(mox_test_helper.ExampleClass, "named_params") as stub:
            ...

        instance = mox_test_helper.ExampleClass()
        with stub._expect:
            mox_test_helper.ExampleClass.named_params(instance, "foo", baz=None)

        mox_test_helper.ExampleClass.named_params(instance, "foo", baz=None)

        mox.verify(stub)
        m = mox.Mox._instances[stub._mox_id]
        m.unset_stubs()

    def test_stub_out_method__unbound__named_using_positional__some_positional(self):
        """Check positional parameters can be matched to keyword arguments."""
        with mox.stubout(mox_test_helper.ExampleClass, "test_method") as stub:
            ...

        instance = mox_test_helper.ExampleClass()

        with stub._expect:
            mox_test_helper.ExampleClass.test_method(instance, "one", "two", "nine")

        mox_test_helper.ExampleClass.test_method(instance, "one", "two", "nine")

        mox.verify(stub)
        m = mox.Mox._instances[stub._mox_id]
        m.unset_stubs()

    def test_stub_out_method__unbound__special_args(self):
        with mox.stubout(mox_test_helper.ExampleClass, "special_args") as stub:
            ...

        instance = mox_test_helper.ExampleClass()

        with stub._expect:
            mox_test_helper.ExampleClass.special_args(instance, "foo", None, bar="bar")

        mox_test_helper.ExampleClass.special_args(instance, "foo", None, bar="bar")

        mox.verify(stub)
        m = mox.Mox._instances[stub._mox_id]
        m.unset_stubs()

    def test_stub_out_method__bound__simple_test(self):
        t = mox.create(TestClass)
        with t._expect:
            t.method_with_args(mox.IgnoreArg(), mox.IgnoreArg()).returns("foo")

        actual = t.method_with_args(None, None)

        mox.verify(t)
        m = mox.Mox._instances[t._mox_id]
        m.unset_stubs()
        assert "foo" == actual

    def test_stub_out_method__bound__named_using_positional(self):
        """Check positional parameters can be matched to keyword arguments."""
        with mox.stubout(mox_test_helper.ExampleClass, "named_params") as stub:
            ...

        instance = mox_test_helper.ExampleClass()
        with stub._expect:
            instance.named_params("foo", baz=None)

        instance.named_params("foo", baz=None)

        mox.verify(stub)
        m = mox.Mox._instances[stub._mox_id]
        m.unset_stubs()

    def test_stub_out_method__bound__named_using_positional__some_positional(self):
        """Check positional parameters can be matched to keyword arguments."""
        with mox.stubout(mox_test_helper.ExampleClass, "test_method") as stub:
            ...

        instance = mox_test_helper.ExampleClass()
        with stub._expect:
            instance.test_method(instance, "one", "two", "nine")

        instance.test_method(instance, "one", "two", "nine")

        mox.verify(stub)
        m = mox.Mox._instances[stub._mox_id]
        m.unset_stubs()

    def test_stub_out_method__bound__special_args(self):
        with mox.stubout(mox_test_helper.ExampleClass, "special_args") as stub:
            ...

        instance = mox_test_helper.ExampleClass()

        with stub._expect:
            instance.special_args(instance, "foo", None, bar="bar")

        instance.special_args(instance, "foo", None, bar="bar")

        mox.verify(stub)
        m = mox.Mox._instances[stub._mox_id]
        m.unset_stubs()

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
        with mox.stubout(test_obj, "method_with_args") as stub, mox.expect:
            test_obj.method_with_args(mox.IgnoreArg(), mox.Func(raise_exception_on_not_one)).returns(1)
            test_obj.method_with_args(mox.IgnoreArg(), mox.Func(raise_exception_on_not_one)).returns(1)

        assert test_obj.method_with_args("ignored", 1) == 1
        with pytest.raises(TestException):
            test_obj.method_with_args("ignored", 2)

        mox.verify(stub)
        m = mox.Mox._instances[stub._mox_id]
        m.unset_stubs()

    def test_stubout__method__explicit_contains__for__set(self):
        """Test that explicit __contains__() for a set gets mocked with
        success."""
        with mox.stubout(TestClass, "SOME_CLASS_SET") as stub, mox.expect:
            TestClass.SOME_CLASS_SET.__contains__("x").returns(True)

        dummy = TestClass()

        result = "x" in dummy.SOME_CLASS_SET

        mox.verify(stub)

        assert result is True

    def test_stub_out__signature_matching_init_(self):
        with mox.stubout(mox_test_helper.ExampleClass, "__init__") as stub:
            ...

        with stub._expect:
            mox_test_helper.ExampleClass.__init__(mox.IgnoreArg())

        # Create an instance of a child class, which calls the parent
        # __init__
        mox_test_helper.ChildExampleClass()

        mox.verify(stub)
        m = mox.Mox._instances[stub._mox_id]
        m.unset_stubs()

    def test_stub_out_class__old_style(self):
        """Test a mocked class whose __init__ returns a Mock."""
        with mox.stubout(mox_test_helper, "TestClassFromAnotherModule") as stub:
            ...
        assert isinstance(mox_test_helper.TestClassFromAnotherModule, mox.MockObject)

        mock_instance = mox.create(mox_test_helper.TestClassFromAnotherModule)

        with mox.expect(stub, mock_instance):
            mox_test_helper.TestClassFromAnotherModule().returns(mock_instance)
            mock_instance.value().returns("mock instance")

        a_mock = mox_test_helper.TestClassFromAnotherModule()
        actual = a_mock.value()

        m = mox.Mox._instances[stub._mox_id]
        m.verify_all()
        m.unset_stubs()
        mox.verify(mock_instance)
        assert "mock instance" == actual

    def test_stub_out_class(self):
        with mox.stubout.klass(mox_test_helper, "CallableClass") as stub:
            # Instance one
            mock_one = mox_test_helper.CallableClass(1, 2)
            # Instance two
            mock_two = mox_test_helper.CallableClass(8, 9)

            mock_one.value().returns("mock")
            mock_two("one").returns("called mock")

        one = mox_test_helper.CallableClass(1, 2)
        actual_one = one.value()

        two = mox_test_helper.CallableClass(8, 9)
        actual_two = two("one")

        m = mox.Mox._instances[stub._mox_id]
        m.verify_all()
        m.unset_stubs()

        # Verify the correct mocks were returned
        assert mock_one == one
        assert mock_two == two

        # Verify
        assert actual_one == "mock"
        assert actual_two == "called mock"

    def test_stub_out_class_with_meta_class(self):
        with mox.stubout.klass(mox_test_helper, "ChildClassWithMetaClass") as stub:
            mock_one = mox_test_helper.ChildClassWithMetaClass(kw=1)
            mock_one.value().returns("mock")

        one = mox_test_helper.ChildClassWithMetaClass(kw=1)
        actual_one = one.value()

        m = mox.Mox._instances[stub._mox_id]
        m.verify_all()
        m.unset_stubs()

        # Verify the correct mocks were returned
        assert mock_one == one

        # Verify
        assert actual_one == "mock"
        assert one.x == "meta"

    def test_stub_out_class__a_b_c_meta(self):
        with mox.stubout.klass(mox_test_helper, "CallableSubclassOfMyDictABC") as stub:
            mock_foo = mox_test_helper.CallableSubclassOfMyDictABC(foo="!mock bar")
            mock_spam = mox_test_helper.CallableSubclassOfMyDictABC(spam="!mock eggs")
            mock_foo["foo"].returns("mock bar")
            mock_spam("beans").returns("called mock")

        foo = mox_test_helper.CallableSubclassOfMyDictABC(foo="!mock bar")
        actual_foo_bar = foo["foo"]

        spam = mox_test_helper.CallableSubclassOfMyDictABC(spam="!mock eggs")
        actual_spam = spam("beans")

        m = mox.Mox._instances[stub._mox_id]
        m.verify_all()
        m.unset_stubs()

        # Verify the correct mocks were returned
        assert mock_foo == foo
        assert mock_spam == spam

        # Verify
        assert "mock bar" == actual_foo_bar
        assert "called mock" == actual_spam

    def test_stub_out_class_not_enough_created(self):
        with mox.stubout.klass(mox_test_helper, "CallableClass") as stub:
            ...

        with stub._expect:
            mox_test_helper.CallableClass(1, 2)
            mox_test_helper.CallableClass(8, 9)

        mox_test_helper.CallableClass(1, 2)

        m = mox.Mox._instances[stub._mox_id]
        len(m.stubs.cache) == 1
        with pytest.raises(mox.ExpectedMockCreationError):
            mox.verify(stub)
        len(m.stubs.cache) == 0

    def test_stub_out_class_wrong_signature(self):
        with mox.stubout.klass(mox_test_helper, "CallableClass") as stub:
            with pytest.raises(AttributeError):
                mox_test_helper.CallableClass()
        # m = mox.Mox()
        #
        # m.stubout_class(mox_test_helper, "CallableClass")
        # with pytest.raises(AttributeError):
        #     mox_test_helper.CallableClass()

        m = mox.Mox._instances[stub._mox_id]
        m.unset_stubs()

    def test_stub_out_class_wrong_parameters(self):
        with mox.stubout.klass(mox_test_helper, "CallableClass") as stub:
            ...

        with stub._expect:
            mox_test_helper.CallableClass(1, 2)

        with pytest.raises(mox.UnexpectedMethodCallError):
            mox_test_helper.CallableClass(8, 9)
        m = mox.Mox._instances[stub._mox_id]
        m.unset_stubs()

    def test_stub_out_class_too_many_created(self):
        with mox.stubout.klass(mox_test_helper, "CallableClass") as stub:
            ...

        with stub._expect:
            mox_test_helper.CallableClass(1, 2)

        mox_test_helper.CallableClass(1, 2)
        with pytest.raises(mox.UnexpectedMockCreationError):
            mox_test_helper.CallableClass(8, 9)

        m = mox.Mox._instances[stub._mox_id]
        m.unset_stubs()

    def test_warns_user_if_mocking_mock(self):
        """Test that user is warned if they try to stub out a MockAnything."""
        with mox.stubout(TestClass, "my_static_method"):
            with pytest.raises(TypeError):
                with mox.stubout(TestClass, "my_static_method"):
                    ...

    def test_stub_out_first_class_method_verifies_signature(self):
        with mox.stubout(mox_test_helper, "MyTestFunction") as stub:
            # Wrong number of arguments
            with pytest.raises(AttributeError):
                mox_test_helper.MyTestFunction(1)
        m = mox.Mox._instances[stub._mox_id]
        m.verify_all()
        m.unset_stubs()

    @pytest.mark.parametrize(
        "args,kwargs,raises,stub_class",
        [
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
        ],
    )
    def test_method_signature_verification(self, args, kwargs, raises, stub_class):
        # If stub_class is true, the test is run against a stubbed out class,
        # else the test is run against a stubbed out instance.
        if stub_class:
            with mox.stubout(mox_test_helper.ExampleClass, "test_method") as stub:
                obj = mox_test_helper.ExampleClass()
        else:
            obj = mox_test_helper.ExampleClass()
            with mox.stubout(obj, "test_method") as stub:
                ...

        with stub._expect:
            if raises:
                with pytest.raises(AttributeError):
                    obj.test_method(*args, **kwargs)
            else:
                obj.test_method(*args, **kwargs)
        m = mox.Mox._instances[stub._mox_id]
        m.unset_stubs()

    def test_stub_out_object(self):
        """Test that object is replaced with a Mock."""

        class foo(object):
            def __init__(self):
                self.obj = TestClass()

        foo = foo()
        with mox.stubout(foo, "obj") as stub:
            ...

        assert isinstance(foo.obj, mox.MockObject)

        with stub._expect:
            foo.obj.valid_call()

        foo.obj.valid_call()

        mox.verify(stub)
        m = mox.Mox._instances[stub._mox_id]
        m.unset_stubs()
        assert not isinstance(foo.obj, mox.MockObject)

    def test_stub_out_re_works(self):
        with mox.stubout(re, "search") as stub, mox.expect:
            re.search("a", "ivan").returns("true")

        result = TestClass().re_search()

        mox.verify(stub)
        m = mox.Mox._instances[stub._mox_id]
        m.unset_stubs()

        assert result == "true"

    def test_forgot_replay_helpful_message(self):
        """If there is an AttributeError on a MockMethod, give users a helpful
        msg."""
        foo = mox.create.any()
        bar = mox.create.any()

        foo.getbar().returns(bar)
        bar.show_me_the_money()

        # Forgot to replay!
        try:
            foo.getbar().show_me_the_money()
        except AttributeError as e:
            assert (
                'MockMethod has no attribute "show_me_the_money". Did you remember to put your mocks in replay mode?'
            ) == str(e)

    def test_swallowed_unknown_method_call(self):
        """Test that a swallowed UnknownMethodCallError will be re-raised."""
        dummy = mox.create(TestClass)
        dummy._replay()

        def call():
            try:
                dummy.invalid_call()
            except mox.UnknownMethodCallError:
                pass

        # UnknownMethodCallError swallowed
        call()

        with pytest.raises(mox.SwallowedExceptionError):
            mox.verify(dummy)

    def test_swallowed_unexpected_mock_creation(self):
        """Test that a swallowed UnexpectedMockCreationError will be
        re-raised."""
        with mox.stubout.klass(mox_test_helper, "CallableClass") as stub:
            ...

        def call():
            try:
                mox_test_helper.CallableClass(1, 2)
            except mox.UnexpectedMockCreationError:
                pass

        # UnexpectedMockCreationError swallowed
        call()

        m = mox.Mox._instances[stub._mox_id]
        len(m.stubs.cache) == 1
        with pytest.raises(mox.SwallowedExceptionError):
            mox.verify(stub)
        len(m.stubs.cache) == 0

    def test_swallowed_unexpected_method_call__wrong_method(self):
        """Test that a swallowed UnexpectedMethodCallError will be re-raised.

        This case is an extraneous method call."""
        mock_obj = mox.create.any()
        with mock_obj._expect:
            mock_obj.open()

        def call():
            mock_obj.open()
            try:
                mock_obj.close()
            except mox.UnexpectedMethodCallError:
                pass

        # UnexpectedMethodCall swallowed
        call()

        with pytest.raises(mox.SwallowedExceptionError):
            mox.verify(mock_obj)

    def test_swallowed_unexpected_method_call__wrong_arguments(self):
        """Test that a swallowed UnexpectedMethodCallError will be re-raised.

        This case is an extraneous method call."""
        mock_obj = mox.create.any()
        with mock_obj._expect:
            mock_obj.open()

        def call():
            try:
                mock_obj.open(1)
            except mox.UnexpectedMethodCallError:
                pass

        # UnexpectedMethodCall swallowed
        call()

        with pytest.raises(mox.SwallowedExceptionError):
            mox.verify(mock_obj)

    def test_swallowed_unexpected_method_call__unordered_group(self):
        """Test that a swallowed UnexpectedMethodCallError will be re-raised.

        This case is an extraneous method call in an unordered group."""
        mock_obj = mox.create.any()
        with mock_obj._expect:
            mock_obj.open().any_order()
            mock_obj.close().any_order()

        def call():
            mock_obj.close()
            try:
                mock_obj.open(1)
            except mox.UnexpectedMethodCallError:
                pass

        # UnexpectedMethodCall swallowed
        call()

        with pytest.raises(mox.SwallowedExceptionError):
            mox.verify(mock_obj)

    def test_swallowed_unexpected_method_call__multiple_times_group(self):
        """Test that a swallowed UnexpectedMethodCallError will be re-raised.

        This case is an extraneous method call in a multiple times group."""
        mock_obj = mox.create.any()
        with mock_obj._expect:
            mock_obj.open().multiple_times()

        def call():
            try:
                mock_obj.open(1)
            except mox.UnexpectedMethodCallError:
                pass

        # UnexpectedMethodCall swallowed
        call()

        with pytest.raises(mox.SwallowedExceptionError):
            mox.verify(mock_obj)


if __name__ == "__main__":
    unittest.main()
