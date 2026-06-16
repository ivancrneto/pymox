#!/usr/bin/env python
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

"""A very basic test class derived from mox.MoxTestBase, used by mox_test.py.

The class defined in this module is used to test the features of
MoxTestBase and is not intended to be a standalone test.  It needs to
be in a separate module, because otherwise the tests in this class
(which should not all pass) would be executed as part of the
mox_test.py test suite.

See mox_test.MoxTestBaseTest for how this class is actually used.
"""

import abc
import os
import re

import mox


class ExampleMoxTestMixin(object):
    """Mix-in class for mox test case class.

    It stubs out the same function as one of the test methods in
    the example test case.  Both tests must pass as meta class wraps
    test methods in all base classes.
    """

    def test_stat(self):
        self.mox.stubout(os, "stat")
        os.stat(self.DIR_PATH)
        self.mox.replay_all()
        os.stat(self.DIR_PATH)


class ExampleMoxTest(mox.MoxTestBase, ExampleMoxTestMixin):
    __test__ = False

    DIR_PATH = "/path/to/some/directory"

    def test_success(self):
        self.mox.stubout(os, "listdir")
        os.listdir(self.DIR_PATH)
        self.mox.replay_all()
        os.listdir(self.DIR_PATH)

    def test_expected_not_called(self):
        self.mox.stubout(os, "listdir")
        os.listdir(self.DIR_PATH)
        self.mox.replay_all()

    def test_unexpected_call(self):
        self.mox.stubout(os, "listdir")
        os.listdir(self.DIR_PATH)
        self.mox.replay_all()
        os.listdir("/path/to/some/other/directory")
        os.listdir(self.DIR_PATH)

    def test_failure(self):
        self.assertTrue(False)

    def test_stat_other(self):
        self.mox.stubout(os, "stat")
        os.stat(self.DIR_PATH)
        self.mox.replay_all()
        os.stat(self.DIR_PATH)

    def test_has_stubs(self):
        listdir_list = []

        def mock_listdir(directory):
            listdir_list.append(directory)

        self.stubs.set(os, "listdir", mock_listdir)
        os.listdir(self.DIR_PATH)
        self.assertEqual([self.DIR_PATH], listdir_list)

    def test_raises_with_statement(self):
        self.mox.stubout(CallableClass, "decision")

        CallableClass.decision().returns("raise")

        self.mox.replay_all()
        with self.assertRaises(Exception):
            call = CallableClass(1, 2)
            call.conditional_function()


class TestClassFromAnotherModule(object):
    def __init__(self):
        return None

    def value(self):
        return "Not mock"


class ChildClassFromAnotherModule(TestClassFromAnotherModule):
    """A child class of TestClassFromAnotherModule.

    Used to test stubbing out unbound methods, where child classes
    are eventually bound.
    """

    def __init__(self):
        TestClassFromAnotherModule.__init__(self)


class MetaClassFromAnotherModule(type):
    def __new__(mcs, name, bases, attrs):
        new_class = super(MetaClassFromAnotherModule, mcs).__new__(mcs, name, bases, attrs)

        new_class.x = "meta"
        return new_class


class ChildClassWithMetaClass(TestClassFromAnotherModule, metaclass=MetaClassFromAnotherModule):
    """A child class with MetaClassFromAnotherModule.

    Used to test corner cases usually only happening with meta classes.
    """

    def value():
        return "Not mock"

    def __init__(self, kw=None):
        super(ChildClassWithMetaClass, self).__init__()


class CallableClass(object):
    def __init__(self, one, two, nine=None):
        pass

    def __call__(self, one):
        return "Not mock"

    def value():
        return "Not mock"

    def decision(self):
        return

    def conditional_function(self):
        decision = self.decision()
        if decision == "raise":
            raise Exception("exception raised")


class MyDictABC(object):
    __metaclass__ = abc.ABCMeta


try:
    MyDictABC.register(dict)
except AttributeError:
    pass


class CallableSubclassOfMyDictABC(MyDictABC):
    def __call__(self, one):
        return "Not mock"

    def __getitem__(self, key, default=None):
        return "Not mock"


def MyTestFunction(one, two, nine=None):
    pass


class ExampleClass(object):
    def __init__(self, foo="bar"):
        pass

    def test_method(self, one, two, nine=None):
        pass

    def named_params(self, ignore, foo="bar", baz="qux"):
        pass

    def special_args(self, *args, **kwargs):
        pass

    @classmethod
    def class_method(cls):
        pass


class SpecialClass(object):
    @classmethod
    def class_method(cls):
        pass

    @staticmethod
    def static_method():
        pass


# This class is used to test stubbing out __init__ of a parent class.
class ChildExampleClass(ExampleClass):
    def __init__(self):
        ExampleClass.__init__(self)


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


class SimpleCallableClass(object):
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


class InheritsFromCallable(SimpleCallableClass):
    """This class should also be mockable; it inherits from a callable class."""

    pass
