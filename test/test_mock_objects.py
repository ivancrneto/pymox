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
"""Tests for MockMethod, MockAnything and MockObject (classic API)."""

import unittest

import pytest

import mox

from . import mox_test_helper
from .mox_test_fixtures_helper import ChildClass, SubscribtableNonIterableClass, TestClass
from .test_helpers.subpackage.faraway import FarAwayClass


class MockMethodTest(unittest.TestCase):
    """Test class to verify that the MockMethod class is working correctly."""

    def setUp(self):
        self.expected_method = mox.MockMethod("test_method", [], [], False)(["original"])
        self.mock_method = mox.MockMethod("test_method", [self.expected_method], [], True)

    def test_name_attribute(self):
        """Should provide a __name__ attribute."""
        self.assertEqual("test_method", self.mock_method.__name__)

    def test_and_return_none_by_default(self):
        """Should return None by default."""
        return_value = self.mock_method(["original"])
        self.assertTrue(return_value is None)

    def test_returns_value(self):
        """Should return a specified return value."""
        expected_return_value = "test"
        self.expected_method.returns(expected_return_value)
        return_value = self.mock_method(["original"])
        self.assertEqual(return_value, expected_return_value)

    def test_returns_value_with_and_return(self):
        """Should return a specified return value."""
        expected_return_value = "test"
        self.expected_method.and_return(expected_return_value)
        return_value = self.mock_method(["original"])
        assert return_value == expected_return_value

    def test_raises_exception(self):
        """Should raise a specified exception."""
        expected_exception = Exception("test exception")
        self.expected_method.raises(expected_exception)
        self.assertRaises(Exception, self.mock_method)

    def test_raises_exception_with_and_raise(self):
        """Should raise a specified exception with `and_raise`."""
        expected_exception = Exception("test exception")
        self.expected_method.and_raise(expected_exception)

        with pytest.raises(Exception, match="test exception"):
            self.mock_method(["original"])

    def test_with_side_effects(self):
        """Should call state modifier."""
        local_list = ["original"]

        def modifier(mutable_list):
            self.assertTrue(local_list is mutable_list)
            mutable_list[0] = "mutation"

        self.expected_method.with_side_effects(modifier).returns(1)
        self.mock_method(local_list)
        self.assertEqual("mutation", local_list[0])

    def test_with_returning_side_effects(self):
        """Should call state modifier and propagate its return value."""
        local_list = ["original"]
        expected_return = "expected_return"

        def modifier_with_return(mutable_list):
            self.assertTrue(local_list is mutable_list)
            mutable_list[0] = "mutation"
            return expected_return

        self.expected_method.with_side_effects(modifier_with_return)
        actual_return = self.mock_method(local_list)
        self.assertEqual("mutation", local_list[0])
        self.assertEqual(expected_return, actual_return)

    def test_with_returning_side_effects_with_and_return(self):
        """Should call state modifier and ignore its return value."""
        local_list = ["original"]
        expected_return = "expected_return"
        unexpected_return = "unexpected_return"

        def modifier_with_return(mutable_list):
            self.assertTrue(local_list is mutable_list)
            mutable_list[0] = "mutation"
            return unexpected_return

        self.expected_method.with_side_effects(modifier_with_return).returns(expected_return)
        actual_return = self.mock_method(local_list)
        self.assertEqual("mutation", local_list[0])
        self.assertEqual(expected_return, actual_return)

    def test_with_returning_side_effects_with_explicit_none_return(self):
        """An explicit and_return(None) must win over the side effect's return."""
        local_list = ["original"]

        def modifier_with_return(mutable_list):
            mutable_list[0] = "mutation"
            return "unexpected_return"

        self.expected_method.with_side_effects(modifier_with_return).returns(None)
        actual_return = self.mock_method(local_list)
        self.assertEqual("mutation", local_list[0])
        self.assertIsNone(actual_return)

    def test_equality_no_params_equal(self):
        """Methods with the same name and without params should be equal."""
        expected_method = mox.MockMethod("test_method", [], [], False)
        self.assertEqual(self.mock_method, expected_method)

    def test_equality_no_params_not_equal(self):
        """Methods with different names and without params should not be
        equal."""
        expected_method = mox.MockMethod("other_method", [], [], False)
        self.assertNotEqual(self.mock_method, expected_method)

    def test_equality_params_equal(self):
        """Methods with the same name and parameters should be equal."""
        params = [1, 2, 3]
        expected_method = mox.MockMethod("test_method", [], [], False)
        expected_method._params = params

        self.mock_method._params = params
        self.assertEqual(self.mock_method, expected_method)

    def test_equality_params_not_equal(self):
        """Methods with the same name and different params should not be
        equal."""
        expected_method = mox.MockMethod("test_method", [], [], False)
        expected_method._params = [1, 2, 3]

        self.mock_method._params = ["a", "b", "c"]
        self.assertNotEqual(self.mock_method, expected_method)

    def test_equality_named_params_equal(self):
        """Methods with the same name and same named params should be equal."""
        named_params = {"input1": "test", "input2": "params"}
        expected_method = mox.MockMethod("test_method", [], [], False)
        expected_method._named_params = named_params

        self.mock_method._named_params = named_params
        self.assertEqual(self.mock_method, expected_method)

    def test_equality_named_params_not_equal(self):
        """Methods with the same name and diff named params should not be equal."""
        expected_method = mox.MockMethod("test_method", [], [], False)
        expected_method._named_params = {"input1": "test", "input2": "params"}

        self.mock_method._named_params = {"input1": "test2", "input2": "params2"}
        self.assertNotEqual(self.mock_method, expected_method)

    def test_equality_wrong_type(self):
        """Method should not be equal to an object of a different type."""
        self.assertNotEqual(self.mock_method, "string?")

    def test_object_equality(self):
        """Equality of objects should work without a Comparator"""
        inst_a = TestClass()
        inst_b = TestClass()

        params = [
            inst_a,
        ]
        expected_method = mox.MockMethod("test_method", [], [], False)
        expected_method._params = params

        self.mock_method._params = [
            inst_b,
        ]
        self.assertEqual(self.mock_method, expected_method)

    def test_str_conversion(self):
        method = mox.MockMethod("f", [], [], False)
        method(1, 2, "st", n1=8, n2="st2")
        self.assertEqual(str(method), "f(1, 2, 'st', n1=8, n2='st2') -> None")

        method = mox.MockMethod("test_method", [], [], False)
        method(1, 2, "only positional")
        self.assertEqual(str(method), "test_method(1, 2, 'only positional') -> None")

        method = mox.MockMethod("test_method", [], [], False)
        method(a=1, b=2, c="only named")
        self.assertEqual(str(method), "test_method(a=1, b=2, c='only named') -> None")

        method = mox.MockMethod("test_method", [], [], False)
        method()
        self.assertEqual(str(method), "test_method() -> None")

        method = mox.MockMethod("test_method", [], [], False)
        method(x="only 1 parameter")
        self.assertEqual(str(method), "test_method(x='only 1 parameter') -> None")

        method = mox.MockMethod("test_method", [], [], False)
        method().returns("return_value")
        self.assertEqual(str(method), "test_method() -> 'return_value'")

        method = mox.MockMethod("test_method", [], [], False)
        method().returns(("a", {1: 2}))
        self.assertEqual(str(method), "test_method() -> ('a', {1: 2})")


class MockAnythingTest(unittest.TestCase):
    """Verify that the MockAnything class works as expected."""

    def setUp(self):
        self.mock_object = mox.MockAnything()

    def test_repr(self):
        """Calling repr on a MockAnything instance must work."""
        self.assertEqual("<MockAnything instance>", repr(self.mock_object))

    def test_is_hashable(self):
        """A MockAnything must be usable as a dict key / set member."""
        other = mox.MockAnything()
        self.assertEqual(hash(self.mock_object), id(self.mock_object))
        mapping = {self.mock_object: 1, other: 2}
        self.assertEqual(mapping[self.mock_object], 1)
        self.assertIn(other, {self.mock_object, other})

    def test_can_mock_str(self):
        self.mock_object.__str__().returns("foo")
        self.mock_object._replay()
        actual = str(self.mock_object)
        self.mock_object._verify()
        self.assertEqual("foo", actual)

    def test_setup_mode(self):
        """Verify the mock will accept any call."""
        self.mock_object.NonsenseCall()
        self.assertEqual(len(self.mock_object._expected_calls_queue), 1)

    def test_replay_with_expected_call(self):
        """Verify the mock replays method calls as expected."""
        self.mock_object.valid_call()  # setup method call
        self.mock_object._replay()  # start replay mode
        self.mock_object.valid_call()  # make method call

    def test_replay_with_unexpected_call(self):
        """Unexpected method calls should raise UnexpectedMethodCallError."""
        self.mock_object.valid_call()  # setup method call
        self.mock_object._replay()  # start replay mode
        self.assertRaises(mox.UnexpectedMethodCallError, self.mock_object.other_valid_call)

    def test_verify_with_complete_replay(self):
        """Verify should not raise an exception for a valid replay."""
        self.mock_object.valid_call()  # setup method call
        self.mock_object._replay()  # start replay mode
        self.mock_object.valid_call()  # make method call
        self.mock_object._verify()

    def test_verify_with_incomplete_replay(self):
        """Verify should raise an exception if the replay was not complete."""
        self.mock_object.valid_call()  # setup method call
        self.mock_object._replay()  # start replay mode
        # valid_call() is never made
        self.assertRaises(mox.ExpectedMethodCallsError, self.mock_object._verify)

    def test_special_class_method(self):
        """Verify should not raise an exception when special methods are
        used."""
        self.mock_object[1].returns(True)
        self.mock_object._replay()
        returned_val = self.mock_object[1]
        self.assertTrue(returned_val)
        self.mock_object._verify()

    def test_nonzero(self):
        """You should be able to use the mock object in an if."""
        self.mock_object._replay()
        if self.mock_object:
            pass

    def test_not_none(self):
        """Mock should be comparable to None."""
        self.mock_object._replay()
        if self.mock_object is not None:
            pass

        if self.mock_object is None:
            pass

    def test_equal(self):
        """A mock should be able to compare itself to another object."""
        self.mock_object._replay()
        self.assertEqual(self.mock_object, self.mock_object)

    def test_equal_mock_failure(self):
        """Verify equals identifies unequal objects."""
        self.mock_object.silly_call()
        self.mock_object._replay()
        self.assertNotEqual(self.mock_object, mox.MockAnything())

    def test_equal_instance_failure(self):
        """Verify equals identifies that objects are different instances."""
        self.mock_object._replay()
        self.assertNotEqual(self.mock_object, TestClass())

    def test_not_equal(self):
        """Verify not equals works."""
        self.mock_object._replay()
        self.assertFalse(self.mock_object != self.mock_object)

    def test_nested_mock_calls_recorded_serially(self):
        """Test that nested calls work when recorded serially."""
        self.mock_object.call_inner().returns(1)
        self.mock_object.call_outer(1)
        self.mock_object._replay()

        self.mock_object.call_outer(self.mock_object.call_inner())

        self.mock_object._verify()

    def test_nested_mock_calls_recorded_nested(self):
        """Test that nested cals work when recorded in a nested fashion."""
        self.mock_object.call_outer(self.mock_object.call_inner().returns(1))
        self.mock_object._replay()

        self.mock_object.call_outer(self.mock_object.call_inner())

        self.mock_object._verify()

    def test_is_callable(self):
        """Test that MockAnything can even mock a simple callable.

        This is handy for "stubbing out" a method in a module with a mock, and
        verifying that it was called.
        """
        self.mock_object().returns("mox0rd")
        self.mock_object._replay()

        self.assertEqual("mox0rd", self.mock_object())

        self.mock_object._verify()

    def test_is_callable_with_called_with(self):
        """Test is_callable, this time using .called_with()"""
        self.mock_object.called_with().returns("mox0rd")
        self.mock_object._replay()

        self.assertEqual("mox0rd", self.mock_object())

        self.mock_object._verify()

    def test_is_reprable(self):
        """Test that MockAnythings can be repr'd without causing a failure."""
        self.assertIn("MockAnything", repr(self.mock_object))

    def test_to_be(self):
        """Test that to_be returns the same instance"""
        assert self.mock_object.to_be == self.mock_object


class MethodCheckerTest(unittest.TestCase):
    """Tests MockMethod's use of MethodChecker method."""

    def test_no_parameters(self):
        method = mox.MockMethod("no_parameters", [], [], False, CheckCallTestClass.no_parameters)
        method()
        self.assertRaises(AttributeError, method, 1)
        self.assertRaises(AttributeError, method, 1, 2)
        self.assertRaises(AttributeError, method, a=1)
        self.assertRaises(AttributeError, method, 1, b=2)

    def test_one_parameter(self):
        method = mox.MockMethod("one_parameter", [], [], False, CheckCallTestClass.one_parameter)
        self.assertRaises(AttributeError, method)
        method(1)
        method(a=1)
        self.assertRaises(AttributeError, method, b=1)
        self.assertRaises(AttributeError, method, 1, 2)
        self.assertRaises(AttributeError, method, 1, a=2)
        self.assertRaises(AttributeError, method, 1, b=2)

    def test_two_parameters(self):
        method = mox.MockMethod("two_parameters", [], [], False, CheckCallTestClass.two_parameters)
        self.assertRaises(AttributeError, method)
        self.assertRaises(AttributeError, method, 1)
        self.assertRaises(AttributeError, method, a=1)
        self.assertRaises(AttributeError, method, b=1)
        method(1, 2)
        method(1, b=2)
        method(a=1, b=2)
        method(b=2, a=1)
        self.assertRaises(AttributeError, method, b=2, c=3)
        self.assertRaises(AttributeError, method, a=1, b=2, c=3)
        self.assertRaises(AttributeError, method, 1, 2, 3)
        self.assertRaises(AttributeError, method, 1, 2, 3, 4)
        self.assertRaises(AttributeError, method, 3, a=1, b=2)

    def test_one_default_value(self):
        method = mox.MockMethod("one_default_value", [], [], False, CheckCallTestClass.one_default_value)
        method()
        method(1)
        method(a=1)
        self.assertRaises(AttributeError, method, b=1)
        self.assertRaises(AttributeError, method, 1, 2)
        self.assertRaises(AttributeError, method, 1, a=2)
        self.assertRaises(AttributeError, method, 1, b=2)

    def test_two_default_values(self):
        method = mox.MockMethod("two_default_values", [], [], False, CheckCallTestClass.two_default_values)
        self.assertRaises(AttributeError, method)
        self.assertRaises(AttributeError, method, c=3)
        self.assertRaises(AttributeError, method, 1)
        self.assertRaises(AttributeError, method, 1, d=4)
        self.assertRaises(AttributeError, method, 1, d=4, c=3)
        method(1, 2)
        method(a=1, b=2)
        method(1, 2, 3)
        method(1, 2, 3, 4)
        method(1, 2, c=3)
        method(1, 2, c=3, d=4)
        method(1, 2, d=4, c=3)
        method(d=4, c=3, a=1, b=2)
        self.assertRaises(AttributeError, method, 1, 2, 3, 4, 5)
        self.assertRaises(AttributeError, method, 1, 2, e=9)
        self.assertRaises(AttributeError, method, a=1, b=2, e=9)

    def test_args(self):
        method = mox.MockMethod("args", [], [], False, CheckCallTestClass.args)
        self.assertRaises(AttributeError, method)
        self.assertRaises(AttributeError, method, 1)
        method(1, 2)
        method(a=1, b=2)
        method(1, 2, 3)
        method(1, 2, 3, 4)
        self.assertRaises(AttributeError, method, 1, 2, a=3)
        self.assertRaises(AttributeError, method, 1, 2, c=3)

    def test_kwargs(self):
        method = mox.MockMethod("kwargs", [], [], False, CheckCallTestClass.kwargs)
        self.assertRaises(AttributeError, method)
        method(1)
        method(1, 2)
        method(a=1, b=2)
        method(b=2, a=1)
        self.assertRaises(AttributeError, method, 1, 2, 3)
        self.assertRaises(AttributeError, method, 1, 2, a=3)
        method(1, 2, c=3)
        method(a=1, b=2, c=3)
        method(c=3, a=1, b=2)
        method(a=1, b=2, c=3, d=4)
        self.assertRaises(AttributeError, method, 1, 2, 3, 4)

    def test_args_and_kwargs(self):
        method = mox.MockMethod("args_and_kwargs", [], [], False, CheckCallTestClass.args_and_kwargs)
        self.assertRaises(AttributeError, method)
        method(1)
        method(1, 2)
        method(1, 2, 3)
        method(a=1)
        method(1, b=2)
        self.assertRaises(AttributeError, method, 1, a=2)
        method(b=2, a=1)
        method(c=3, b=2, a=1)
        method(1, 2, c=3)

    def test_far_away_class_with_instantiated_object(self):
        obj = FarAwayClass()
        method = mox.MockMethod("distant_method", [], [], False, obj.distant_method)
        self.assertRaises(AttributeError, method, 1)
        self.assertRaises(AttributeError, method, a=1)
        self.assertRaises(AttributeError, method, b=1)
        self.assertRaises(AttributeError, method, 1, 2)
        self.assertRaises(AttributeError, method, 1, b=2)
        self.assertRaises(AttributeError, method, a=1, b=2)
        self.assertRaises(AttributeError, method, b=2, a=1)
        self.assertRaises(AttributeError, method, b=2, c=3)
        self.assertRaises(AttributeError, method, a=1, b=2, c=3)
        self.assertRaises(AttributeError, method, 1, 2, 3)
        self.assertRaises(AttributeError, method, 1, 2, 3, 4)
        self.assertRaises(AttributeError, method, 3, a=1, b=2)
        method()


class CheckCallTestClass(object):
    def no_parameters(self):
        pass

    def one_parameter(self, a):
        pass

    def two_parameters(self, a, b):
        pass

    def one_default_value(self, a=1):
        pass

    def two_default_values(self, a, b, c=1, d=2):
        pass

    def args(self, a, b, *args):
        pass

    def kwargs(self, a, b=2, **kwargs):
        pass

    def args_and_kwargs(self, a, *args, **kwargs):
        pass


class MockObjectTest(unittest.TestCase):
    """Verify that the MockObject class works as expected."""

    def setUp(self):
        self.mock_object = mox.MockObject(TestClass)
        self.mock = mox.Mox()

    def test_is_hashable(self):
        """A MockObject must be usable as a dict key / set member."""
        other = mox.MockObject(TestClass)
        self.assertEqual(hash(self.mock_object), id(self.mock_object))
        mapping = {self.mock_object: 1, other: 2}
        self.assertEqual(mapping[self.mock_object], 1)
        self.assertIn(other, {self.mock_object, other})

    def test_description(self):
        self.assertEqual(self.mock_object._description, "TestClass")

        mock_object = mox.MockObject(FarAwayClass.distant_method)
        self.assertEqual(mock_object._description, "FarAwayClass.distant_method")

        mock_object = mox.MockObject(mox_test_helper.MyTestFunction)
        self.assertEqual(mock_object._description, "function test.mox_test_helper.MyTestFunction")

    def test_description_mocked_object(self):
        obj = FarAwayClass()

        self.mock.stubout(obj, "distant_method")
        obj.distant_method().returns(True)

        self.mock.replay_all()
        self.assertEqual(obj.distant_method._description, "FarAwayClass.distant_method")
        self.mock.reset_all()

    def test_description_module_function(self):
        self.mock.stubout(mox_test_helper, "MyTestFunction")
        mox_test_helper.MyTestFunction(one=1, two=2).returns(True)

        self.mock.replay_all()
        self.assertEqual(
            mox_test_helper.MyTestFunction._description,
            "function test.mox_test_helper.MyTestFunction",
        )
        self.mock.reset_all()

    def test_description_mocked_class(self):
        obj = FarAwayClass()

        self.mock.stubout(FarAwayClass, "distant_method")
        obj.distant_method().returns(True)

        self.mock.replay_all()
        self.assertEqual(obj.distant_method._description, "FarAwayClass.distant_method")
        self.mock.reset_all()

    def test_description_class_method(self):
        obj = mox_test_helper.SpecialClass()

        self.mock.stubout(mox_test_helper.SpecialClass, "class_method")
        mox_test_helper.SpecialClass.class_method().returns(True)

        self.mock.replay_all()
        self.assertEqual(obj.class_method._description, "SpecialClass.class_method")
        self.mock.unset_stubs()
        self.mock.reset_all()

    def test_description_static_method_mock_class(self):
        self.mock.stubout(mox_test_helper.SpecialClass, "static_method")
        mox_test_helper.SpecialClass.static_method().returns(True)

        self.mock.replay_all()
        self.assertIn(
            mox_test_helper.SpecialClass.static_method._description,
            ["SpecialClass.static_method", "function test.mox_test_helper.static_method"],
        )
        self.mock.reset_all()

    def test_description_static_method_mock_instance(self):
        obj = mox_test_helper.SpecialClass()

        self.mock.stubout(obj, "static_method")
        obj.static_method().returns(True)

        self.mock.replay_all()
        self.assertIn(
            obj.static_method._description,
            ["SpecialClass.static_method", "function test.mox_test_helper.static_method"],
        )
        self.mock.reset_all()

    def test_description_builtin(self):
        mock_getcwd = self.mock.stubout("os.getcwd")
        mock_getcwd().returns("/")

        self.mock.replay_all()
        assert mock_getcwd._description == "getcwd"
        self.mock.reset_all()

    def test_mox_id(self):
        mock = mox.MockObject(TestClass)
        assert mock._mox_id is None

        mock = mox.MockObject(TestClass, _mox_id=id(self.mock))
        assert mock._mox_id == id(self.mock)

        mock_anything = mox.MockAnything()
        assert mock_anything._mox_id is None

        mock_anything = mox.MockAnything(_mox_id=id(self.mock))
        assert mock_anything._mox_id == id(self.mock)

    def test_setup_mode_with_valid_call(self):
        """Verify the mock object properly mocks a basic method call."""
        self.mock_object.valid_call()
        self.assertEqual(len(self.mock_object._expected_calls_queue), 1)

    def test_setup_mode_with_invalid_call(self):
        """UnknownMethodCallError should be raised if a non-member method is
        called."""
        # Note: assertRaises does not catch exceptions thrown by MockObject's
        # __getattr__
        try:
            self.mock_object.invalid_call()
            self.fail("No exception thrown, expected UnknownMethodCallError")
        except mox.UnknownMethodCallError:
            pass
        except Exception:
            self.fail("Wrong exception type thrown, expected UnknownMethodCallError")

    def test_replay_with_invalid_call(self):
        """UnknownMethodCallError should be raised if a non-member method is
        called."""
        self.mock_object.valid_call()  # setup method call
        self.mock_object._replay()  # start replay mode
        # Note: assertRaises does not catch exceptions thrown by MockObject's
        # __getattr__
        try:
            self.mock_object.invalid_call()
            self.fail("No exception thrown, expected UnknownMethodCallError")
        except mox.UnknownMethodCallError:
            pass
        except Exception:
            self.fail("Wrong exception type thrown, expected UnknownMethodCallError")

    def test_is_instance(self):
        """Mock should be able to pass as an instance of the mocked class."""
        self.assertIsInstance(self.mock_object, TestClass)

    def test_find_valid_methods(self):
        """Mock should be able to mock all public methods."""
        self.assertIn("valid_call", self.mock_object._known_methods)
        self.assertIn("other_valid_call", self.mock_object._known_methods)
        self.assertIn("my_class_method", self.mock_object._known_methods)
        self.assertIn("my_static_method", self.mock_object._known_methods)
        self.assertIn("_protected_call", self.mock_object._known_methods)
        self.assertNotIn("__private_call", self.mock_object._known_methods)
        self.assertIn("_TestClass__private_call", self.mock_object._known_methods)

    def test_finds_superclass_methods(self):
        """Mock should be able to mock superclasses methods."""
        self.mock_object = mox.MockObject(ChildClass)
        self.assertIn("valid_call", self.mock_object._known_methods)
        self.assertIn("other_valid_call", self.mock_object._known_methods)
        self.assertIn("my_class_method", self.mock_object._known_methods)
        self.assertIn("child_valid_call", self.mock_object._known_methods)

    def test_access_class_variables(self):
        """Class variables should be accessible through the mock."""
        self.assertIn("SOME_CLASS_VAR", self.mock_object._known_vars)
        self.assertIn("SOME_CLASS_SET", self.mock_object._known_vars)
        self.assertIn("_PROTECTED_CLASS_VAR", self.mock_object._known_vars)
        self.assertEqual("test_value", self.mock_object.SOME_CLASS_VAR)
        self.assertEqual({"a", "b", "c"}, self.mock_object.SOME_CLASS_SET)

    def test_equal(self):
        """A mock should be able to compare itself to another object."""
        self.mock_object._replay()
        self.assertEqual(self.mock_object, self.mock_object)

    def test_equal_mock_failure(self):
        """Verify equals identifies unequal objects."""
        self.mock_object.valid_call()
        self.mock_object._replay()
        self.assertNotEqual(self.mock_object, mox.MockObject(TestClass))

    def test_equal_instance_failure(self):
        """Verify equals identifies that objects are different instances."""
        self.mock_object._replay()
        self.assertNotEqual(self.mock_object, TestClass())

    def test_not_equal(self):
        """Verify not equals works."""
        self.mock_object._replay()
        self.assertFalse(self.mock_object != self.mock_object)

    def test_mock_set_item__expected_set_item__success(self):
        """Test that __setitem__() gets mocked in Dummy.

        In this test, _verify() succeeds.
        """
        dummy = mox.MockObject(TestClass)
        dummy["X"] = "Y"

        dummy._replay()

        dummy["X"] = "Y"

        dummy._verify()

    def test_mock_set_item__expected_set_item__no_success(self):
        """Test that __setitem__() gets mocked in Dummy.

        In this test, _verify() fails.
        """
        dummy = mox.MockObject(TestClass)
        dummy["X"] = "Y"

        dummy._replay()

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
        # NOT doing dummy['X'] = 'Y'

        dummy._replay()

        # NOT doing dummy['X'] = 'Y'

        dummy._verify()

    def test_mock_set_item__expected_set_item__nonmatching_parameters(self):
        """Test that __setitem__() fails if other parameters are expected."""
        dummy = mox.MockObject(TestClass)
        dummy["X"] = "Y"

        dummy._replay()

        def call():
            dummy["wrong"] = "Y"

        self.assertRaises(mox.UnexpectedMethodCallError, call)

        self.assertRaises(mox.SwallowedExceptionError, dummy._verify)

    def test_mock_set_item__with_sub_class_of_new_style_class(self):
        class NewStyleTestClass(object):
            def __init__(self):
                self.my_dict = {}

            def __setitem__(self, key, value):
                self.my_dict[key] = value

        class TestSubClass(NewStyleTestClass):
            pass

        dummy = mox.MockObject(TestSubClass)
        dummy[1] = 2
        dummy._replay()
        dummy[1] = 2
        dummy._verify()

    def test_mock_get_item__expected_get_item__success(self):
        """Test that __getitem__() gets mocked in Dummy.

        In this test, _verify() succeeds.
        """
        dummy = mox.MockObject(TestClass)
        dummy["X"].returns("value")

        dummy._replay()

        self.assertEqual(dummy["X"], "value")

        dummy._verify()

    def test_mock_get_item__expected_get_item__no_success(self):
        """Test that __getitem__() gets mocked in Dummy.

        In this test, _verify() fails.
        """
        dummy = mox.MockObject(TestClass)
        dummy["X"].returns("value")

        dummy._replay()

        # NOT doing dummy['X']

        self.assertRaises(mox.ExpectedMethodCallsError, dummy._verify)

    def test_mock_get_item__expected_no_get_item__no_success(self):
        """Test that __getitem__() gets mocked in Dummy."""
        dummy = mox.MockObject(TestClass)
        # NOT doing dummy['X']

        dummy._replay()

        def call():
            return dummy["X"]

        self.assertRaises(mox.UnexpectedMethodCallError, call)

    def test_mock_get_item__expected_get_item__nonmatching_parameters(self):
        """Test that __getitem__() fails if other parameters are expected."""
        dummy = mox.MockObject(TestClass)
        dummy["X"].returns("value")

        dummy._replay()

        def call():
            return dummy["wrong"]

        self.assertRaises(mox.UnexpectedMethodCallError, call)

        self.assertRaises(mox.SwallowedExceptionError, dummy._verify)

    def test_mock_get_item__with_sub_class_of_new_style_class(self):
        class NewStyleTestClass(object):
            def __getitem__(self, key):
                return {1: "1", 2: "2"}[key]

        class TestSubClass(NewStyleTestClass):
            pass

        dummy = mox.MockObject(TestSubClass)
        dummy[1].returns("3")

        dummy._replay()
        self.assertEqual("3", dummy.__getitem__(1))
        dummy._verify()

    def test_mock_iter__expected_iter__success(self):
        """Test that __iter__() gets mocked in Dummy.

        In this test, _verify() succeeds.
        """
        dummy = mox.MockObject(TestClass)
        iter(dummy).returns(iter(["X", "Y"]))

        dummy._replay()

        self.assertEqual([x for x in dummy], ["X", "Y"])

        dummy._verify()

    def test_mock_contains__expected_contains__success(self):
        """Test that __contains__ gets mocked in Dummy.

        In this test, _verify() succeeds.
        """
        dummy = mox.MockObject(TestClass)
        dummy.__contains__("X").returns(True)

        dummy._replay()

        self.assertIn("X", dummy)

        dummy._verify()

    def test_mock_contains__expected_contains__no_success(self):
        """Test that __contains__() gets mocked in Dummy.

        In this test, _verify() fails.
        """
        dummy = mox.MockObject(TestClass)
        dummy.__contains__("X").returns("True")

        dummy._replay()

        # NOT doing 'X' in dummy

        self.assertRaises(mox.ExpectedMethodCallsError, dummy._verify)

    def test_mock_contains__expected_contains__nonmatching_parameter(self):
        """Test that __contains__ fails if other parameters are expected."""
        dummy = mox.MockObject(TestClass)
        dummy.__contains__("X").returns(True)

        dummy._replay()

        def call():
            return "Y" in dummy

        self.assertRaises(mox.UnexpectedMethodCallError, call)

        self.assertRaises(mox.SwallowedExceptionError, dummy._verify)

    def test_mock_iter__expected_iter__no_success(self):
        """Test that __iter__() gets mocked in Dummy.

        In this test, _verify() fails.
        """
        dummy = mox.MockObject(TestClass)
        iter(dummy).returns(iter(["X", "Y"]))

        dummy._replay()

        # NOT doing self.assertEqual([x for x in dummy], ['X', 'Y'])

        self.assertRaises(mox.ExpectedMethodCallsError, dummy._verify)

    def test_mock_iter__expected_no_iter__no_success(self):
        """Test that __iter__() gets mocked in Dummy."""
        dummy = mox.MockObject(TestClass)
        # NOT doing iter(dummy)

        dummy._replay()

        def call():
            return [x for x in dummy]

        self.assertRaises(mox.UnexpectedMethodCallError, call)

    def test_mock_iter__expected_get_item__success(self):
        """Test that __iter__() gets mocked in Dummy using getitem."""
        dummy = mox.MockObject(SubscribtableNonIterableClass)
        dummy[0].returns("a")
        dummy[1].returns("b")
        dummy[2].raises(IndexError)

        dummy._replay()
        self.assertEqual(["a", "b"], [x for x in dummy])
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
        class NewStyleTestClass(object):
            def __iter__(self):
                return iter([1, 2, 3])

        class TestSubClass(NewStyleTestClass):
            pass

        dummy = mox.MockObject(TestSubClass)
        iter(dummy).returns(iter(["a", "b"]))
        dummy._replay()
        self.assertEqual(["a", "b"], [x for x in dummy])
        dummy._verify()

    def test_instantiation_with_additional_attributes(self):
        mock_object = mox.MockObject(TestClass, attrs={"attr1": "value"})
        self.assertEqual(mock_object.attr1, "value")

    def test_cant_override_methods_with_attributes(self):
        self.assertRaises(ValueError, mox.MockObject, TestClass, attrs={"valid_call": "value"})

    def test_cant_mock_non_public_attributes(self):
        self.assertRaises(
            mox.PrivateAttributeError,
            mox.MockObject,
            TestClass,
            attrs={"_protected": "value"},
        )
        self.assertRaises(
            mox.PrivateAttributeError,
            mox.MockObject,
            TestClass,
            attrs={"__private": "value"},
        )


if __name__ == "__main__":
    unittest.main()
