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
"""Tests for mox comparators."""

# Python imports
import io
import re
import unittest

# Internal imports
import mox


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

    def test_is_hashable(self):
        """A comparator must remain hashable despite overriding __eq__."""
        comparator = mox.IsA(str)
        self.assertEqual(hash(comparator), id(comparator))
        self.assertIn(comparator, {comparator})


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


if __name__ == "__main__":
    unittest.main()
