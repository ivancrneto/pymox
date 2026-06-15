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
# Python imports
import io
import re
import sys
import unittest

# Pip imports
import pytest

# Internal imports
import mox

from . import mox_test_helper
from .test_helpers.subpackage.faraway import FarAwayClass


OS_LISTDIR = mox_test_helper.os.listdir


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


class OrTest(unittest.TestCase):
    """Test Or correctly chains Comparators."""

    def test_valid_or(self):
        """Or should be True if either Comparator returns True."""
        self.assertEqual(mox.Or(mox.IsA(dict), mox.IsA(str)), {})
        self.assertEqual(mox.Or(mox.IsA(dict), mox.IsA(str)), "test")
        self.assertEqual(mox.Or(mox.IsA(str), mox.IsA(str)), "test")

    def test_invalid_or(self):
        """Or should be False if both Comparators return False."""
        self.assertFalse(mox.Or(mox.IsA(dict), mox.IsA(str)) == 0)


class AndTest(unittest.TestCase):
    """Test And correctly chains Comparators."""

    def test_valid_and(self):
        """And should be True if both Comparators return True."""
        self.assertEqual(mox.And(mox.IsA(str), mox.IsA(str)), "1")

    def test_clause_one_fails(self):
        """And should be False if the first Comparator returns False."""

        self.assertNotEqual(mox.And(mox.IsA(dict), mox.IsA(str)), "1")

    def test_advanced_usage(self):
        """And should work with other Comparators.

        Note: this test is reliant on In and contains_key_value.
        """
        test_dict = {"mock": "obj", "testing": "isCOOL"}
        self.assertTrue(mox.And(mox.In("testing"), mox.contains_key_value("mock", "obj")) == test_dict)

    def test_advanced_usage_fails(self):
        """Note: this test is reliant on In and contains_key_value."""
        test_dict = {"mock": "obj", "testing": "isCOOL"}
        self.assertFalse(mox.And(mox.In("NOTFOUND"), mox.contains_key_value("mock", "obj")) == test_dict)


class FuncTest(unittest.TestCase):
    """Test Func correctly evaluates based upon true-false return."""

    def test_func_true_false_evaluation(self):
        """Should return True if the validating function returns True."""

        def equals_one(x):
            return x == 1

        def always_none(x):
            return None

        self.assertEqual(mox.Func(equals_one), 1)
        self.assertNotEqual(mox.Func(equals_one), 0)

        self.assertNotEqual(mox.Func(always_none), 1)
        self.assertNotEqual(mox.Func(always_none), 0)
        self.assertFalse(mox.Func(always_none) is None)

    def test_func_exception_propagation(self):
        """Exceptions within the validating function should propagate."""

        class TestException(Exception):
            pass

        def raise_exception_on_not_one(value):
            if value != 1:
                raise TestException
            else:
                return True

        self.assertEqual(mox.Func(raise_exception_on_not_one), 1)
        self.assertRaises(TestException, mox.Func(raise_exception_on_not_one).__eq__, 2)


class SameElementsAsTest(unittest.TestCase):
    """Test SameElementsAs correctly identifies sequences with same elements."""

    def test_sorted_lists(self):
        """Should return True if two lists are exactly equal."""
        self.assertTrue(mox.SameElementsAs([1, 2.0, "c"]) == [1, 2.0, "c"])

    def test_unsorted_lists(self):
        """Should return True if two lists are unequal but have same elements."""
        self.assertTrue(mox.SameElementsAs([1, 2.0, "c"]) == [2.0, "c", 1])

    def test_unhashable_lists(self):
        """Should return True if two lists have the same unhashable elements."""
        self.assertTrue(mox.SameElementsAs([{"a": 1}, {2: "b"}]) == [{2: "b"}, {"a": 1}])

    def test_empty_lists(self):
        """Should return True for two empty lists."""
        self.assertTrue(mox.SameElementsAs([]) == [])

    def test_unequal_lists(self):
        """Should return False if the lists are not equal."""
        self.assertFalse(mox.SameElementsAs([1, 2.0, "c"]) == [2.0, "c"])

    def test_unequal_unhashable_lists(self):
        """Should return False if two lists with unhashable elements are
        unequal."""
        self.assertFalse(mox.SameElementsAs([{"a": 1}, {2: "b"}]) == [{2: "b"}])

    def test_actual_is_not_a_sequence(self):
        """Should return False if the actual object is not a sequence."""
        self.assertFalse(mox.SameElementsAs([1]) == object())

    def test_one_unhashable_object_in_actual(self):
        """Store the entire iterator for a correct comparison.

        In a previous version of SameElementsAs, iteration stopped when an
        unhashable object was encountered and then was restarted, so the actual
        list
        appeared smaller than it was.
        """
        self.assertFalse(mox.SameElementsAs([1, 2]) == iter([{}, 1, 2]))


class ContainsKeyValueTest(unittest.TestCase):
    """Test contains_key_value correctly identifies key/value pairs in a dict."""

    def test_valid_pair(self):
        """Should return True if the key value is in the dict."""
        self.assertTrue(mox.contains_key_value("key", 1) == {"key": 1})

    def test_invalid_value(self):
        """Should return False if the value is not correct."""
        self.assertFalse(mox.contains_key_value("key", 1) == {"key": 2})

    def test_invalid_key(self):
        """Should return False if they key is not in the dict."""
        self.assertFalse(mox.contains_key_value("qux", 1) == {"key": 2})


class ContainsAttributeValueTest(unittest.TestCase):
    """Test contains_attribute_value correctly identifies properties in an
    object."""

    def setUp(self):
        """Create an object to test with."""

        class TestObject(object):
            key = 1

        self.test_object = TestObject()

    def test_valid_pair(self):
        """Should return True if the object has the key attribute and it
        matches."""
        self.assertTrue(mox.contains_attribute_value("key", 1) == self.test_object)

    def test_invalid_value(self):
        """Should return False if the value is not correct."""
        self.assertFalse(mox.contains_key_value("key", 2) == self.test_object)

    def test_invalid_key(self):
        """Should return False if they the object doesn't have the property."""
        self.assertFalse(mox.contains_key_value("qux", 1) == self.test_object)


class InTest(unittest.TestCase):
    """Test In correctly identifies a key in a list/dict"""

    def test_item_in_list(self):
        """Should return True if the item is in the list."""
        self.assertTrue(mox.In(1) == [1, 2, 3])

    def test_key_in_dict(self):
        """Should return True if the item is a key in a dict."""
        self.assertTrue(mox.In("test") == {"test": "module"})

    def test_item_in_tuple(self):
        """Should return True if the item is in the list."""
        self.assertTrue(mox.In(1) == (1, 2, 3))

    def test_tuple_in_tuple_of_tuples(self):
        self.assertTrue(mox.In((1, 2, 3)) == ((1, 2, 3), (1, 2)))

    def test_item_not_in_list(self):
        self.assertFalse(mox.In(1) == [2, 3])

    def test_tuple_not_in_tuple_of_tuples(self):
        self.assertFalse(mox.In((1, 2)) == ((1, 2, 3), (4, 5)))


class NotTest(unittest.TestCase):
    """Test Not correctly identifies False predicates."""

    def test_item_in_list(self):
        """Should return True if the item is NOT in the list."""
        self.assertTrue(mox.Not(mox.In(42)) == [1, 2, 3])

    def test_key_in_dict(self):
        """Should return True if the item is NOT a key in a dict."""
        self.assertTrue(mox.Not(mox.In("foo")) == {"key": 42})

    def test_invalid_key_with_not(self):
        """Should return False if they key is NOT in the dict."""
        self.assertTrue(mox.Not(mox.contains_key_value("qux", 1)) == {"key": 2})


class StrContainsTest(unittest.TestCase):
    """Test StrContains correctly checks for substring occurrence of a
    parameter."""

    def test_valid_substring_at_start(self):
        """Should return True if the substring is at the start of the
        string."""
        self.assertTrue(mox.StrContains("hello") == "hello world")

    def test_valid_substring_in_middle(self):
        """Should return True if the substring is in the middle of the
        string."""
        self.assertTrue(mox.StrContains("lo wo") == "hello world")

    def test_valid_substring_at_end(self):
        """Should return True if the substring is at the end of the string."""
        self.assertTrue(mox.StrContains("ld") == "hello world")

    def test_invaild_substring(self):
        """Should return False if the substring is not in the string."""
        self.assertFalse(mox.StrContains("AAA") == "hello world")

    def test_multiple_matches(self):
        """Should return True if there are multiple occurances of substring."""
        self.assertTrue(mox.StrContains("abc") == "ababcabcabcababc")


class RegexTest(unittest.TestCase):
    """Test Regex correctly matches regular expressions."""

    def test_identify_bad_syntax_during_init(self):
        """The user should know immediately if a regex has bad syntax."""
        self.assertRaises(re.error, mox.Regex, "(a|b")

    def test_pattern_in_middle(self):
        """Should return True if the pattern matches at the middle of the
        string.

        This ensures that re.search is used (instead of re.find).
        """
        self.assertTrue(mox.Regex(r"a\s+b") == "x y z a b c")

    def test_non_match_pattern(self):
        """Should return False if the pattern does not match the string."""
        self.assertFalse(mox.Regex(r"a\s+b") == "x y z")

    def test_flags_passed_correctly(self):
        """Should return True as we pass IGNORECASE flag."""
        self.assertTrue(mox.Regex(r"A", re.IGNORECASE) == "a")

    def test_repr_without_flags(self):
        """repr should return the regular expression pattern."""
        self.assertEqual(repr(mox.Regex(rb"a\s+b")), r"<regular expression 'a\s+b'>")

    def test_repr_with_flags(self):
        """repr should return the regular expression pattern and flags."""
        self.assertEqual(repr(mox.Regex(rb"a\s+b", flags=4)), r"<regular expression 'a\s+b', flags=4>")


class IsTest(unittest.TestCase):
    """Verify Is correctly checks equality based upon identity, not value"""

    class AlwaysComparesTrue(object):
        def __eq__(self, other):
            return True

        def __cmp__(self, other):
            return 0

        def __ne__(self, other):
            return False

    def test_equality_valid(self):
        o1 = self.AlwaysComparesTrue()
        self.assertTrue(mox.Is(o1), o1)

    def test_equality_invalid(self):
        o1 = self.AlwaysComparesTrue()
        o2 = self.AlwaysComparesTrue()
        self.assertTrue(o1 == o2)
        # but...
        self.assertFalse(mox.Is(o1) == o2)

    def test_inequality_valid(self):
        o1 = self.AlwaysComparesTrue()
        o2 = self.AlwaysComparesTrue()
        self.assertTrue(mox.Is(o1) != o2)

    def test_inequality_invalid(self):
        o1 = self.AlwaysComparesTrue()
        self.assertFalse(mox.Is(o1) != o1)

    def test_equality_in_list_valid(self):
        o1 = self.AlwaysComparesTrue()
        o2 = self.AlwaysComparesTrue()
        isa_list = [mox.Is(o1), mox.Is(o2)]
        str_list = [o1, o2]
        self.assertTrue(isa_list == str_list)

    def test_equailty_in_list_invalid(self):
        o1 = self.AlwaysComparesTrue()
        o2 = self.AlwaysComparesTrue()
        isa_list = [mox.Is(o1), mox.Is(o2)]
        mixed_list = [o2, o1]
        self.assertFalse(isa_list == mixed_list)


class IsATest(unittest.TestCase):
    """Verify IsA correctly checks equality based upon class type, not
    value."""

    def test_equality_valid(self):
        """Verify that == correctly identifies objects of the same type."""
        self.assertTrue(mox.IsA(str) == "test")

    def test_equality_invalid(self):
        """Verify that == correctly identifies objects of different types."""
        self.assertFalse(mox.IsA(str) == 10)

    def test_inequality_valid(self):
        """Verify that != identifies objects of different type."""
        self.assertTrue(mox.IsA(str) != 10)

    def test_inequality_invalid(self):
        """Verify that != correctly identifies objects of the same type."""
        self.assertFalse(mox.IsA(str) != "test")

    def test_equality_in_list_valid(self):
        """Verify list contents are properly compared."""
        isa_list = [mox.IsA(str), mox.IsA(str)]
        str_list = ["abc", "def"]
        self.assertTrue(isa_list == str_list)

    def test_equailty_in_list_invalid(self):
        """Verify list contents are properly compared."""
        isa_list = [mox.IsA(str), mox.IsA(str)]
        mixed_list = ["abc", 123]
        self.assertFalse(isa_list == mixed_list)

    def test_special_types(self):
        """Verify that IsA can handle objects like cStringIO.StringIO."""
        isA = mox.IsA(io.StringIO())
        stringIO = io.StringIO()
        self.assertTrue(isA == stringIO)


class IsAlmostTest(unittest.TestCase):
    """Verify IsAlmost correctly checks equality of floating point numbers."""

    def test_equality_valid(self):
        """Verify that == correctly identifies nearly equivalent floats."""
        self.assertEqual(mox.IsAlmost(1.8999999999), 1.9)

    def test_equality_invalid(self):
        """Verify that == correctly identifies non-equivalent floats."""
        self.assertNotEqual(mox.IsAlmost(1.899), 1.9)

    def test_equality_with_places(self):
        """Verify that specifying places has the desired effect."""
        self.assertNotEqual(mox.IsAlmost(1.899), 1.9)
        self.assertEqual(mox.IsAlmost(1.899, places=2), 1.9)

    def test_non_numeric_types(self):
        """Verify that IsAlmost handles non-numeric types properly."""

        self.assertNotEqual(mox.IsAlmost(1.8999999999), "1.9")
        self.assertNotEqual(mox.IsAlmost("1.8999999999"), 1.9)
        self.assertNotEqual(mox.IsAlmost("1.8999999999"), "1.9")


class ValueRememberTest(unittest.TestCase):
    """Verify comparing argument against remembered value."""

    def test_value_equal(self):
        """Verify that value will compare to stored value."""
        value = mox.value()
        value.store_value("hello world")
        self.assertEqual(value, "hello world")

    def test_no_value(self):
        """Verify that uninitialized value does not compare to "empty"
        values."""
        value = mox.value()
        self.assertNotEqual(value, None)
        self.assertNotEqual(value, False)
        self.assertNotEqual(value, 0)
        self.assertNotEqual(value, "")
        self.assertNotEqual(value, ())
        self.assertNotEqual(value, [])
        self.assertNotEqual(value, {})
        self.assertNotEqual(value, object())
        self.assertNotEqual(value, set())

    def test_remember_value(self):
        """Verify that comparing against remember will store argument."""
        value = mox.value()
        remember = mox.Remember(value)
        # value not yet stored.
        self.assertNotEqual(value, "hello world")

        # store value here.
        self.assertEqual(remember, "hello world")

        # compare against stored value.
        self.assertEqual(value, "hello world")


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
        # Python imports
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
                'MockMethod has no attribute "show_me_the_money". '
                "Did you remember to put your mocks in replay "
                "mode?",
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
        with mox.stubout.many(
            ["test.mox_test_helper.TestClass.valid_call", True],
            ["test.mox_test_helper.TestClass.other_valid_call", True],
        ) as (mock_valid, mock_other_valid), mox.expect:
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
                'MockMethod has no attribute "show_me_the_money". Did you remember to ' "put your mocks in replay mode?"
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


class ReplayTest(unittest.TestCase):
    """Verify Replay works properly."""

    def test_replay(self):
        """Replay should put objects into replay mode."""
        mock_obj = mox.MockObject(TestClass)
        self.assertFalse(mock_obj._replay_mode)
        mox.replay(mock_obj)
        self.assertTrue(mock_obj._replay_mode)


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


class TestClass:
    """This class is used only for testing the mock framework"""

    SOME_CLASS_SET = {"a", "b", "c"}
    SOME_CLASS_VAR = "test_value"
    _PROTECTED_CLASS_VAR = "protected value"

    def __init__(self, ivar=None, parent=None):
        self.__ivar = ivar
        self.parent = parent

    def __eq__(self, rhs):
        return self.__ivar == rhs

    def __ne__(self, rhs):
        return not self.__eq__(rhs)

    def valid_call(self):
        pass

    def method_with_args(self, one, two, nine=None):
        pass

    def other_valid_call(self):
        pass

    def optional_args(self, foo="boom"):
        pass

    def valid_call_with_args(self, *args, **kwargs):
        pass

    @classmethod
    def my_class_method(cls):
        pass

    @staticmethod
    def my_static_method():
        pass

    def _protected_call(self):
        pass

    def __private_call(self):
        pass

    def __do_not_mock(self):
        pass

    def __getitem__(self, key):
        """Return the value for key."""
        return self.d[key]

    def __setitem__(self, key, value):
        """Set the value for key to value."""
        self.d[key] = value

    def __contains__(self, key):
        """Returns True if d contains the key."""
        return key in self.d

    def __iter__(self):
        pass

    def re_search(self):
        return re.search("a", "ivan")


class ChildClass(TestClass):
    """This inherits from TestClass."""

    def __init__(self):
        TestClass.__init__(self)

    def child_valid_call(self):
        pass


class CallableClass(object):
    """This class is callable, and that should be mockable!"""

    def __init__(self):
        pass

    def __call__(self, param):
        return param


class ClassWithProperties(object):
    def setter_attr(self, value):
        pass

    def getter_attr(self):
        pass

    prop_attr = property(getter_attr, setter_attr)


class SubscribtableNonIterableClass(object):
    def __getitem__(self, index):
        raise IndexError


class InheritsFromCallable(CallableClass):
    """This class should also be mockable; it inherits from a callable class."""

    pass


if __name__ == "__main__":
    unittest.main()
