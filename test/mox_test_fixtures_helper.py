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
"""Shared fixture classes used across the split mox test modules."""

import re


class TestClass:
    """This class is used only for testing the mock framework"""

    # Not a pytest test class despite the "Test" prefix; suppress collection.
    __test__ = False

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
