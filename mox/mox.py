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

"""Mox, an object-mocking framework for Python.

Mox works in the record-replay-verify paradigm.  When you first create
a mock object, it is in record mode.  You then programmatically set
the expected behavior of the mock object (what methods are to be
called on it, with what parameters, what they should return, and in
what order).

Once you have set up the expected mock behavior, you put it in replay
mode.  Now the mock responds to method calls just as you told it to.
If an unexpected method (or an expected method with unexpected
parameters) is called, then an exception will be raised.

Once you are done interacting with the mock, you need to verify that
all the expected interactions occured.  (Maybe your code exited
prematurely without calling some cleanup method!)  The verify phase
ensures that every expected method was called; otherwise, an exception
will be raised.

WARNING! Mock objects created by Mox are not thread-safe.  If you are
call a mock in multiple threads, it should be guarded by a mutex.

TODO(stevepm): Add the option to make mocks thread-safe!

Suggested usage / workflow:

  # Create Mox factory
  my_mox = Mox()

  # Create a mock data access object
  mock_dao = my_mox.create_mock(DAOClass)

  # Set up expected behavior
  mock_dao.retrieve_person_with_identifier("1").and_return(person)
  mock_dao.delete_person(person)

  # Put mocks in replay mode
  my_mox.replay_all()

  # Inject mock object and run test
  controller.set_dao(mock_dao)
  controller.delete_person_by_id("1")

  # Verify all methods were called as expected
  my_mox.verify_all()
"""
# Python imports
import abc
import inspect
import types
from collections import deque
from re import search as re_search

from . import stubbingout
from .comparators import IsA
from .exceptions import (
    Error,
    ExpectedMethodCallsError,
    ExpectedMockCreationError,
    PrivateAttributeError,
    SwallowedExceptionError,
    UnexpectedMethodCallError,
    UnexpectedMockCreationError,
    UnknownMethodCallError,
)
from .groups import MethodGroup, MultipleTimesGroup, UnorderedGroup
from .helpers import resolve_object


class _MoxManagerMeta(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        instance = super(_MoxManagerMeta, cls).__call__(*args, **kwargs)
        cls.track(instance)
        return instance

    def track(cls, instance):
        """Register a Mox instance in the global registry.

        Construction registers automatically; the context-manager singletons
        (``mox.create``) also call this on each use so they re-register after a
        test teardown has cleared the registry.
        """
        cls._instances[id(instance)] = instance

    def unset_stubs_for_id(cls, mox_id):
        mox_instance = cls._instances.get(mox_id)
        if mox_instance is not None:
            mox_instance.unset_stubs()

    def global_unset_stubs(cls):
        for mox_instance in list(cls._instances.values()):
            mox_instance.stubs.unset_all()
            mox_instance.stubs.smart_unset_all()

    def global_replay(cls):
        for mox_instance in list(cls._instances.values()):
            mox_instance.replay_all()

    def global_verify(cls):
        for mox_instance in list(cls._instances.values()):
            mox_instance.verify_all()

    def reset_instances(cls):
        """Forget all tracked Mox instances.

        The context-manager API (``mox.expect``) and the pytest plugin operate
        on every registered Mox instance via ``global_*``. Without clearing the
        registry between tests, those instances would live for the whole
        process (a memory leak) and - worse - a later test's global teardown
        would re-verify mocks recorded by earlier tests, leaking failures
        across unrelated tests. Test harnesses call this once their own
        teardown is complete.
        """
        # Also drop accumulated mocks from the long-lived context-manager
        # singletons (e.g. mox.create's shared Mox), so a prior test's leftover
        # expectations can't be re-verified - and fail - during a later test.
        for instance in cls._instances.values():
            instance._mock_objects.clear()
        cls._instances.clear()


class Mox(metaclass=_MoxManagerMeta):
    """Mox: a factory for creating mock objects."""

    # A list of types that should be stubbed out with MockObjects (as
    # opposed to MockAnythings).
    _USE_MOCK_OBJECT = [
        getattr(types, "ClassType", type),
        types.FunctionType,
        getattr(types, "InstanceType", object),
        types.ModuleType,
        getattr(types, "ObjectType", object),
        getattr(types, "TypeType", type),
        types.MethodType,
        getattr(types, "UnboundMethodType", types.FunctionType),
    ]

    # A list of types that may be stubbed out with a MockObjectFactory.
    _USE_MOCK_FACTORY = [
        getattr(types, "ClassType", type),
        getattr(types, "ObjectType", object),
        getattr(types, "TypeType", type),
        abc.ABCMeta,
    ]

    def __init__(self):
        """Initialize a new Mox."""

        self._mock_objects = []
        self.stubs = stubbingout.StubOutForTesting()

    def create_mock(self, class_to_mock, attrs=None):
        """Create a new mock object.

        Args:
          # class_to_mock: the class to be mocked
          class_to_mock: class
          attrs: dict of attribute names to values that will be set on the mock
            object.  Only public attributes may be set.

        Returns:
          MockObject that can be used as the class_to_mock would be.
        """
        if attrs is None:
            attrs = {}
        new_mock = MockObject(class_to_mock, attrs=attrs, _mox_id=id(self))
        self._mock_objects.append(new_mock)
        return new_mock

    def create_mock_anything(self, description=None):
        """Create a mock that will accept any method calls.

        This does not enforce an interface.

        Args:
          description: str. Optionally, a descriptive name for the mock object
            being created, for debugging output purposes.
        """
        new_mock = MockAnything(description=description, _mox_id=id(self))
        self._mock_objects.append(new_mock)
        return new_mock

    @property
    def expect(self):
        # Internal imports
        from mox.contextmanagers import Expect

        return Expect.from_mox(mox_obj=self)

    def replay_all(self):
        """Set all mock objects to replay mode."""

        for mock_obj in self._mock_objects:
            mock_obj._replay()

    def verify_all(self):
        """Call verify on all mock objects created."""

        exceptions_thrown = []
        for mock_obj in self._mock_objects:
            try:
                mock_obj._verify()
            except Error as e:
                exceptions_thrown.append(e)

        if exceptions_thrown:
            self.unset_stubs()
            raise exceptions_thrown[0]

    def reset_all(self):
        """Call reset on all mock objects.  This does not unset stubs."""

        for mock_obj in self._mock_objects:
            mock_obj._reset()

    @resolve_object
    def stubout(self, obj, attr_name, use_mock_anything=False):
        """Replace a method, attribute, etc. with a Mock.

        This will replace a class or module with a MockObject, and everything
        else (method, function, etc) with a MockAnything.  This can be
        overridden to always use a MockAnything by setting use_mock_anything to
        True.

        Args:
          obj: A Python object (class, module, instance, callable).
          attr_name: str.  The name of the attribute to replace with a mock.
          use_mock_anything: bool. True if a MockAnything should be used
            regardless of the type of attribute.
        """

        attr_to_replace = getattr(obj, attr_name)
        attr_type = type(attr_to_replace)

        if attr_type == MockAnything or attr_type == MockObject:
            raise TypeError("Cannot mock a MockAnything! Did you remember to call unset_stubs in your previous test?")

        if (
            attr_type in self._USE_MOCK_OBJECT
            or
            # isinstance(attr_type, tuple(self._USE_MOCK_OBJECT)) or
            isinstance(attr_to_replace, object)
            or inspect.isclass(attr_to_replace)
        ) and not use_mock_anything:
            stub = self.create_mock(attr_to_replace)
        else:
            stub = self.create_mock_anything(description="Stub for %s" % attr_to_replace)
            stub.__name__ = attr_name

        self.stubs.set(obj, attr_name, stub)
        return stub

    @resolve_object
    def stubout_class(self, obj, attr_name):
        """Replace a class with a "mock factory" that will create mock objects.

        This is useful if the code-under-test directly instantiates
        dependencies.  Previously some boilerplate was necessary to
        create a mock that would act as a factory.  Using
        stubout_class, once you've stubbed out the class you may
        use the stubbed class as you would any other mock created by mox:
        during the record phase, new mock instances will be created, and
        during replay, the recorded mocks will be returned.

        In replay mode

        # Example using stubout (the old, clunky way):

        mock1 = mox.create_mock(my_import.FooClass)
        mock2 = mox.create_mock(my_import.FooClass)
        foo_factory = mox.stubout(my_import, 'FooClass', use_mock_anything=True)
        foo_factory(1, 2).returns(mock1)
        foo_factory(9, 10).returns(mock2)
        mox.replay_all()

        my_import.FooClass(1, 2)   # Returns mock1 again.
        my_import.FooClass(9, 10)  # Returns mock2 again.
        mox.verify_all()

        # Example using stubout_class:

        mox.stubout_class(my_import, 'FooClass')
        mock1 = my_import.FooClass(1, 2)   # Returns a new mock of FooClass
        mock2 = my_import.FooClass(9, 10)  # Returns another mock instance
        mox.replay_all()

        my_import.FooClass(1, 2)   # Returns mock1 again.
        my_import.FooClass(9, 10)  # Returns mock2 again.
        mox.verify_all()
        """
        attr_to_replace = getattr(obj, attr_name)
        attr_type = type(attr_to_replace)

        if attr_type == MockAnything or attr_type == MockObject:
            raise TypeError("Cannot mock a MockAnything! Did you remember to call unset_stubs in your previous test?")

        if not inspect.isclass(attr_to_replace):
            raise TypeError("Given attr is not a Class. Use stubout.")

        factory = _MockObjectFactory(attr_to_replace, self)
        self._mock_objects.append(factory)
        self.stubs.set(obj, attr_name, factory)
        return factory

    def unset_stubs(self):
        """Restore stubs to their original state."""

        self.stubs.unset_all()
        self.stubs.smart_unset_all()

    CreateMock = create_mock
    CreateMockAnything = create_mock_anything
    ReplayAll = replay_all
    VerifyAll = verify_all
    ResetAll = reset_all
    StubOutWithMock = stubout
    StubOutClassWithMocks = stubout_class
    UnsetStubs = unset_stubs


def replay(*args):
    """Put mocks into Replay mode.

    Args:
      # args is any number of mocks to put into replay mode.
    """

    for mock in args:
        mock._replay()


Replay = replay


def verify(*args):
    """Verify mocks.

    Args:
      # args is any number of mocks to be verified.
    """

    for mock in args:
        mock._verify()


Verify = verify


def reset(*args):
    """Reset mocks.

    Args:
      # args is any number of mocks to be reset.
    """

    for mock in args:
        mock._reset()


Reset = reset


class MockAnything:
    """A mock that can be used to mock anything.

    This is helpful for mocking classes that do not provide a public interface.
    """

    def __init__(self, description=None, _mox_id=None):
        """Initialize a new MockAnything.

        Args:
          description: str. Optionally, a descriptive name for the mock object
            being created, for debugging output purposes.
        """
        self._description = description
        self._exceptions_thrown = []
        self._mox_id = _mox_id
        self._reset()

    def __bases__(self):
        pass

    def __members__(self):
        pass

    def __methods__(self):
        pass

    def __repr__(self):
        if self._description:
            return "<MockAnything instance of %s>" % self._description
        else:
            return "<MockAnything instance>"

    def __str__(self):
        return self._create_mock_method("__str__")()

    def __call__(self, *args, **kwargs):
        return self._create_mock_method("__call__")(*args, **kwargs)

    def __getitem__(self, i):
        return self._create_mock_method("__getitem__")(i)

    def __getattr__(self, method_name):
        """Intercept method calls on this object.

         A new MockMethod is returned that is aware of the MockAnything's
         state (record or replay).  The call will be recorded or replayed
         by the MockMethod's __call__.

        Args:
          # method name: the name of the method being called.
          method_name: str

        Returns:
          A new MockMethod aware of MockAnything's state (record or replay).
        """
        if method_name == "__dir__":
            return self.__class__.__dir__.__get__(self, self.__class__)

        return self._create_mock_method(method_name)

    def _create_mock_method(self, method_name, method_to_mock=None):
        """Create a new mock method call and return it.

        Args:
          # method_name: the name of the method being called.
          # method_to_mock: The actual method being mocked, used for
          #   introspection.
          method_name: str
          method_to_mock: a method object

        Returns:
          A new MockMethod aware of MockAnything's state (record or replay).
        """

        return MockMethod(
            method_name,
            self._expected_calls_queue,
            self._exceptions_thrown,
            self._replay_mode,
            method_to_mock=method_to_mock,
            description=self._description,
        )

    def __nonzero__(self):
        """Return 1 for nonzero so the mock can be used as a conditional."""

        return 1

    def __eq__(self, rhs):
        """Provide custom logic to compare objects."""

        return (
            isinstance(rhs, MockAnything)
            and self._replay_mode == rhs._replay_mode
            and self._expected_calls_queue == rhs._expected_calls_queue
        )

    def __ne__(self, rhs):
        """Provide custom logic to compare objects."""

        return not self == rhs

    def __hash__(self):
        """Hash by identity.

        __eq__ is overridden (and is value-based), which by default makes
        instances unhashable in Python 3.  Mocks frequently stand in for
        objects that code-under-test uses as dict keys or set members, so we
        restore hashability using object identity - the same approach taken by
        MockMethod.
        """
        return id(self)

    @property
    def _expect(self):
        # Internal imports
        from mox.contextmanagers import Expect

        return Expect(self)

    def _replay(self):
        """Start replaying expected method calls."""

        self._replay_mode = True

    def _verify(self):
        """Verify that all the expected calls have been made.

        Raises:
          ExpectedMethodCallsError: if there are still more method calls in the
            expected queue.
          any exception previously raised by this object: if _Verify was called
          afterwards anyway.  (This detects tests passing erroneously.)
        """

        # If any exceptions were thrown, re-raise them.  (This should only
        # happen if the original exception was swallowed, in which case it's
        # necessary to re-raise it so that the test will fail.  See Issue #16.)
        if self._exceptions_thrown:
            raise SwallowedExceptionError(self._exceptions_thrown)
        # If the list of expected calls is not empty, raise an exception
        if self._expected_calls_queue:
            # The last MultipleTimesGroup is not popped from the queue.
            is_multiple_times_group = isinstance(self._expected_calls_queue[0], MultipleTimesGroup)

            if (
                len(self._expected_calls_queue) == 1
                and is_multiple_times_group
                and self._expected_calls_queue[0].is_satisfied()
            ):
                pass
            else:
                raise ExpectedMethodCallsError(self._expected_calls_queue)

    def _reset(self):
        """Reset the state of this mock to record mode with an empty queue."""

        # Maintain a list of method calls we are expecting
        self._expected_calls_queue = deque()

        # Make sure we are in setup mode, not replay mode
        self._replay_mode = False

    @property
    def to_be(self):
        return self

    def called_with(self, *args, **kwargs):
        return self(*args, **kwargs)

    _Replay = _replay
    _Verify = _verify
    _Reset = _reset


class MockObject(MockAnything, object):
    """A mock object that simulates the public/protected interface of a class."""

    def __init__(self, class_to_mock, attrs=None, _mox_id=None):
        """Initialize a mock object.

        This determines the methods and properties of the class and stores
        them.

        Args:
          # class_to_mock: class to be mocked
          class_to_mock: class
          attrs: dict of attribute names to values that will be set on the mock
            object.  Only public attributes may be set.

        Raises:
          PrivateAttributeError: if a supplied attribute is not public.
          ValueError: if an attribute would mask an existing method.
        """
        if attrs is None:
            attrs = {}

        # This is used to hack around the mixin/inheritance of MockAnything,
        # which is not a proper object (it can be anything. :-)
        MockAnything.__dict__["__init__"](self, _mox_id=_mox_id)

        # Get a list of all the public and special methods we should mock.
        self._known_methods = set()
        self._known_vars = set()
        self._class_to_mock = class_to_mock
        try:
            if inspect.isclass(self._class_to_mock):
                self._description = class_to_mock.__name__
            elif inspect.ismethod(self._class_to_mock):
                method_name = class_to_mock.__func__.__name__
                class_name = class_to_mock.__self__.__class__.__name__
                if class_name == "type":
                    class_name = class_to_mock.__self__.__name__
                self._description = "{}.{}".format(class_name, method_name)
            elif inspect.isbuiltin(self._class_to_mock):
                self._description = class_to_mock.__name__
            else:
                search_string = (
                    r"<(?P<extra>function|((un)?bound )?method) (?P<class>\w*)" r"(\.(?P<method>\w*))?( at \w+)?>"
                )
                search = re_search(search_string, str(repr(class_to_mock)))

                self._description = "{}.{}".format(search.group("class"), search.group("method"))

                if search.group("extra") == "function" and not search.group("class") or not search.group("method"):
                    to_use = search.group("class") or search.group("method")
                    if inspect.isfunction(self._class_to_mock):
                        self._description = "function {}.{}".format(self._class_to_mock.__module__, to_use)
        except Exception:
            try:
                self._description = type(class_to_mock).__name__
            except Exception:
                self._description = "Unknown description"

        for method in dir(class_to_mock):
            try:
                attr = getattr(class_to_mock, method)
            except AttributeError:
                continue
            if callable(attr):
                self._known_methods.add(method)
            elif not (isinstance(attr, property)):
                # treating properties as class vars makes little sense.
                self._known_vars.add(method)

        # Set additional attributes at instantiation time; this is quicker
        # than manually setting attributes that are normally created in
        # __init__.
        for attr, value in attrs.items():
            if attr.startswith("_"):
                raise PrivateAttributeError(attr)
            elif attr in self._known_methods:
                raise ValueError("'%s' is a method of '%s' objects." % (attr, class_to_mock))
            else:
                setattr(self, attr, value)

    def __getattr__(self, name):
        """Intercept attribute request on this object.

        If the attribute is a public class variable, it will be returned and
        not recorded as a call.

        If the attribute is not a variable, it is handled like a method
        call. The method name is checked against the set of mockable
        methods, and a new MockMethod is returned that is aware of the
        MockObject's state (record or replay).  The call will be recorded
        or replayed by the MockMethod's __call__.

        Args:
          # name: the name of the attribute being requested.
          name: str

        Returns:
          Either a class variable or a new MockMethod that is aware of the
          state of the mock (record or replay).

        Raises:
          UnknownMethodCallError if the MockObject does not mock the requested
              method.
        """
        if name in self._known_vars:
            return getattr(self._class_to_mock, name)

        if name in self._known_methods:
            return self._create_mock_method(name, method_to_mock=getattr(self._class_to_mock, name))

        exception = UnknownMethodCallError(name)
        self._exceptions_thrown.append(exception)
        raise exception

    def __eq__(self, rhs):
        """Provide custom logic to compare objects."""

        return (
            isinstance(rhs, MockObject)
            and self._class_to_mock == rhs._class_to_mock
            and self._replay_mode == rhs._replay_mode
            and self._expected_calls_queue == rhs._expected_calls_queue
        )

    # Defining __eq__ resets __hash__ to None in this class, so restore the
    # identity-based hash inherited from MockAnything.
    __hash__ = MockAnything.__hash__

    def __setitem__(self, key, value):
        """Provide custom logic for mocking classes that support item
        assignment.

        Args:
          key: Key to set the value for.
          value: Value to set.

        Returns:
          Expected return value in replay mode.  A MockMethod object for the
          __setitem__ method that has already been called if not in replay
          mode.

        Raises:
          TypeError if the underlying class does not support item assignment.
          UnexpectedMethodCallError if the object does not expect the call to
            __setitem__.

        """
        # Verify the class supports item assignment.
        if "__setitem__" not in dir(self._class_to_mock):
            raise TypeError("object does not support item assignment")

        # If we are in replay mode then simply call the mock __setitem__
        # method.
        if self._replay_mode:
            return MockMethod(
                "__setitem__",
                self._expected_calls_queue,
                self._exceptions_thrown,
                self._replay_mode,
            )(key, value)

        # Otherwise, create a mock method __setitem__.
        return self._create_mock_method("__setitem__")(key, value)

    def __getitem__(self, key):
        """Provide custom logic for mocking classes that are subscriptable.

        Args:
          key: Key to return the value for.

        Returns:
          Expected return value in replay mode.  A MockMethod object for the
          __getitem__ method that has already been called if not in replay
          mode.

        Raises:
          TypeError if the underlying class is not subscriptable.
          UnexpectedMethodCallError if the object does not expect the call to
            __getitem__.

        """
        # Verify the class supports item assignment.
        if "__getitem__" not in dir(self._class_to_mock):
            raise TypeError("unsubscriptable object")

        # If we are in replay mode then simply call the mock __getitem__
        # method.
        if self._replay_mode:
            return MockMethod(
                "__getitem__",
                self._expected_calls_queue,
                self._exceptions_thrown,
                self._replay_mode,
            )(key)

        # Otherwise, create a mock method __getitem__.
        return self._create_mock_method("__getitem__")(key)

    def __iter__(self):
        """Provide custom logic for mocking classes that are iterable.

        Returns:
          Expected return value in replay mode.  A MockMethod object for the
          __iter__ method that has already been called if not in replay mode.

        Raises:
          TypeError if the underlying class is not iterable.
          UnexpectedMethodCallError if the object does not expect the call to
            __iter__.

        """
        methods = dir(self._class_to_mock)

        # Verify the class supports iteration.
        if "__iter__" not in methods:
            # If it doesn't have iter method and we are in replay method, then
            # try to iterate using subscripts.
            if "__getitem__" not in methods or not self._replay_mode:
                raise TypeError("not iterable object")
            else:
                results = []
                index = 0
                try:
                    while True:
                        results.append(self[index])
                        index += 1
                except IndexError:
                    return iter(results)

        # If we are in replay mode then simply call the mock __iter__ method.
        if self._replay_mode:
            return MockMethod(
                "__iter__",
                self._expected_calls_queue,
                self._exceptions_thrown,
                self._replay_mode,
            )()

        # Otherwise, create a mock method __iter__.
        return self._create_mock_method("__iter__")()

    def __contains__(self, key):
        """Provide custom logic for mocking classes that contain items.

        Args:
          key: Key to look in container for.

        Returns:
          Expected return value in replay mode.  A MockMethod object for the
          __contains__ method that has already been called if not in replay
          mode.

        Raises:
          TypeError if the underlying class does not implement __contains__
          UnexpectedMethodCaller if the object does not expect the call to
          __contains__.

        """
        contains = getattr(self._class_to_mock, "__contains__", None)

        if contains is None:
            raise TypeError("unsubscriptable object")

        if self._replay_mode:
            return MockMethod(
                "__contains__",
                self._expected_calls_queue,
                self._exceptions_thrown,
                self._replay_mode,
            )(key)

        return self._create_mock_method("__contains__")(key)

    def __call__(self, *params, **named_params):
        """Provide custom logic for mocking classes that are callable."""

        # Verify the class we are mocking is callable.
        callable = hasattr(self._class_to_mock, "__call__")
        # callable = callable and str(
        #     type(self._class_to_mock.__call__)) not in [
        #         "<class 'method-wrapper'>",  # python 3
        #         "<type 'method-wrapper'>"  # python 2
        #     ]
        if not callable:
            raise TypeError("Not callable")

        # Because the call is happening directly on this object instead of a
        # method, the call on the mock method is made right here

        # If we are mocking a Function, then use the function, and not the
        # __call__ method
        method = None
        if type(self._class_to_mock) in (types.FunctionType, types.MethodType):
            method = self._class_to_mock
        else:
            method = getattr(self._class_to_mock, "__call__")
        mock_method = self._create_mock_method("__call__", method_to_mock=method)

        try:
            return mock_method(*params, **named_params)
        except (AttributeError, Error) as e:
            Mox.unset_stubs_for_id(self._mox_id)
            raise e

    @property
    def __class__(self):
        """Return the class that is being mocked."""

        return self._class_to_mock

    @property
    def __name__(self):
        """Return the name that is being mocked."""
        return self._description


class _MockObjectFactory(MockObject):
    """A MockObjectFactory creates mocks and verifies __init__ params.

    A MockObjectFactory removes the boilerplate code that was previously
    necessary to stub out direction instantiation of a class.

    The MockObjectFactory creates new MockObjects when called and verifies the
    __init__ params are correct when in record mode.  When replaying, existing
    mocks are returned, and the __init__ params are verified.

    See StubOutWithMock vs StubOutClassWithMocks for more detail.
    """

    def __init__(self, class_to_mock, mox_instance):
        MockObject.__init__(self, class_to_mock)
        self._mox = mox_instance
        self._mox_id = id(mox_instance)
        self._instance_queue = deque()

    def __call__(self, *params, **named_params):
        """Instantiate and record that a new mock has been created."""

        method = getattr(self._class_to_mock, "__init__")
        mock_method = self._create_mock_method("__init__", method_to_mock=method)
        # Note: calling mock_method() is deferred in order to catch the
        # empty instance_queue first.

        if self._replay_mode:
            if not self._instance_queue:
                exception = UnexpectedMockCreationError(self._class_to_mock, *params, **named_params)
                self._exceptions_thrown.append(exception)
                raise exception

            mock_method(*params, **named_params)

            return self._instance_queue.pop()
        else:
            mock_method(*params, **named_params)

            instance = self._mox.create_mock(self._class_to_mock)
            self._instance_queue.appendleft(instance)
            return instance

    def _verify(self):
        """Verify that all mocks have been created."""
        if self._instance_queue:
            raise ExpectedMockCreationError(self._instance_queue)
        super(_MockObjectFactory, self)._verify()

    _Verify = _verify


class MethodSignatureChecker(object):
    """Ensures that methods are called correctly."""

    _NEEDED, _DEFAULT, _GIVEN = range(3)

    def __init__(self, method):
        """Creates a checker.

        Args:
          # method: A method to check.
          method: function

        Raises:
          ValueError: method could not be inspected, so checks aren't possible.
            Some methods and functions like built-ins can't be inspected.
        """
        try:
            self._args, varargs, varkw, defaults = getattr(inspect, "getfullargspec")(method)[:4]
        except TypeError:
            raise ValueError("Could not get argument specification for %r" % (method,))
        self._method = method
        if inspect.ismethod(self._method) or ("." in repr(self._method)) or (self._args and self._args[0] == "self"):
            self._args = self._args[1:]  # Skip 'self'.
        self._instance = None  # May contain the instance this is bound to.

        self._has_varargs = varargs is not None
        self._has_varkw = varkw is not None
        if defaults is None:
            self._required_args = self._args
            self._default_args = []
        else:
            self._required_args = self._args[: -len(defaults)]
            self._default_args = self._args[-len(defaults):]

    def _record_argument_given(self, arg_name, arg_status):
        """Mark an argument as being given.

        Args:
          # arg_name: The name of the argument to mark in arg_status.
          # arg_status: Maps argument names to one of _NEEDED, _DEFAULT,
          #  _GIVEN.
          arg_name: string
          arg_status: dict

        Raises:
          AttributeError: arg_name is already marked as _GIVEN.
        """
        if arg_status.get(arg_name, None) == MethodSignatureChecker._GIVEN:
            raise AttributeError("%s provided more than once" % (arg_name,))
        arg_status[arg_name] = MethodSignatureChecker._GIVEN

    def check(self, params, named_params):
        """Ensures that the parameters used while recording a call are valid.

        Args:
          # params: A list of positional parameters.
          # named_params: A dict of named parameters.
          params: list
          named_params: dict

        Raises:
          AttributeError: the given parameters don't work with the given
          method.
        """
        arg_status = dict((a, MethodSignatureChecker._NEEDED) for a in self._required_args)
        for arg in self._default_args:
            arg_status[arg] = MethodSignatureChecker._DEFAULT

        # WARNING: Suspect hack ahead.
        #
        # Check to see if this is an unbound method, where the instance
        # should be bound as the first argument.  We try to determine if
        # the first argument (param[0]) is an instance of the class, or it
        # is equivalent to the class (used to account for Comparators).
        #
        # NOTE: If a Func() comparator is used, and the signature is not
        # correct, this will cause extra executions of the function.
        # NOTE: '.' in repr(self._method) is very bad way to check if it's a
        # bound method. Improve it as soon as possible.
        if inspect.ismethod(self._method) or "." in repr(self._method):
            # The extra param accounts for the bound instance.
            if len(params) > len(self._required_args):
                expected = getattr(self._method, "im_class", None)
                if not expected:
                    search = re_search(
                        r"<(function|method) (?P<class>\w+)\.\w+ at \w+>",
                        str(repr(self._method)),
                    )
                    if search:
                        class_ = search.group("class")
                        members = dict(inspect.getmembers(self._method))
                        expected = members.get(class_, members.get("__globals__", {})).get(class_, None)
                if not expected:
                    search = re_search(
                        r"<(?P<method>((un)?bound method ))(?P<class>\w+)"
                        r"\.\w+ of <?(?P<module>\w+\.)(?P<class2>\w+) object "
                        r"at [A-Za-z0-9]+>?>",
                        str(repr(self._method)),
                    )

                    if search:
                        for _, class_ in search.groupdict().items():
                            members = dict(inspect.getmembers(self._method))
                            expected = members.get(class_, members.get("__globals__", {})).get(class_, None)
                            if expected:
                                break
                if not expected:
                    expected = dict(inspect.getmembers(self._method))["__self__"].__class__

                # Check if the param is an instance of the expected class,
                # or check equality (useful for checking Comparators).

                # This is a hack to work around the fact that the first
                # parameter can be a Comparator, and the comparison may raise
                # an exception during this comparison, which is OK.
                try:
                    param_equality = params[0] == expected
                except BaseException:
                    param_equality = False

                if isinstance(params[0], expected) or param_equality:
                    params = params[1:]
                # If the IsA() comparator is being used, we need to check the
                # inverse of the usual case - that the given instance is a
                # subclass of the expected class.  For example, the code under
                # test does late binding to a subclass.
                elif isinstance(params[0], IsA) and params[0]._IsSubClass(expected):
                    params = params[1:]

        # Check that each positional param is valid.
        for i in range(len(params)):
            try:
                arg_name = self._args[i]
            except IndexError:
                if not self._has_varargs:
                    raise AttributeError(
                        "%s does not take %d or more positional arguments" % (self._method.__name__, i)
                    )
            else:
                self._record_argument_given(arg_name, arg_status)

        # Check each keyword argument.
        for arg_name in named_params:
            if arg_name not in arg_status and not self._has_varkw:
                raise AttributeError("%s is not expecting keyword argument %s" % (self._method.__name__, arg_name))
            self._record_argument_given(arg_name, arg_status)

        # Ensure all the required arguments have been given.
        still_needed = [k for k, v in arg_status.items() if v == MethodSignatureChecker._NEEDED]
        if still_needed:
            raise AttributeError("No values given for arguments: %s" % (" ".join(sorted(still_needed))))

    _RecordArgumentGiven = _record_argument_given
    Check = check


class _Unset:
    """Sentinel marking that no return value has been configured.

    Distinguishes "no return value set" from an explicit ``and_return(None)``,
    so a side effect's return value does not silently override an intended None.
    """

    def __repr__(self):  # pragma: no cover - debugging aid only
        return "<unset>"


_UNSET = _Unset()


class MockMethod(object):
    """Callable mock method.

    A MockMethod should act exactly like the method it mocks, accepting
    parameters and returning a value, or throwing an exception (as specified).
    When this method is called, it can optionally verify whether the called
    method (name and signature) matches the expected method.
    """

    def __init__(
        self,
        method_name,
        call_queue,
        exception_list,
        replay_mode,
        method_to_mock=None,
        description=None,
    ):
        """Construct a new mock method.

        Args:
          # method_name: the name of the method
          # call_queue: deque of calls, verify this call against the head, or
          #     add this call to the queue.
          # exception_list: list of exceptions; any exceptions thrown by this
          #     instance are appended to this list.
          # replay_mode: False if we are recording, True if we are verifying
          #     calls against the call queue.
          # method_to_mock: The actual method being mocked, used for
          #     introspection.
          # description: optionally, a descriptive name for this method.
          #     Typically this is equal to the descriptive name of the method's
          #     class.
          method_name: str
          call_queue: list or deque
          exception_list: list
          replay_mode: bool
          method_to_mock: a method object
          description: str or None
        """

        self._name = method_name
        self.__name__ = method_name
        self._call_queue = call_queue
        if not isinstance(call_queue, deque):
            self._call_queue = deque(self._call_queue)
        self._exception_list = exception_list
        self._replay_mode = replay_mode
        self._description = description

        self._params = None
        self._named_params = None
        self._return_value = _UNSET
        self._exception = None
        self._side_effects = None

        try:
            self._checker = MethodSignatureChecker(method_to_mock)
        except ValueError:
            self._checker = None

    def __call__(self, *params, **named_params):
        """Log parameters and return the specified return value.

        If the Mock(Anything/Object) associated with this call is in record
        mode, this MockMethod will be pushed onto the expected call queue. If
        the mock is in replay mode, this will pop a MockMethod off the top of
        the queue and verify this call is equal to the expected call.

        Raises:
          UnexpectedMethodCall if this call is supposed to match an expected
            method call and it does not.
        """

        self._params = params
        self._named_params = named_params

        if not self._replay_mode:
            if self._checker is not None:
                self._checker.check(params, named_params)
            self._call_queue.append(self)
            return self

        expected_method = self._verify_method_call()

        if expected_method._side_effects:
            result = expected_method._side_effects(*params, **named_params)
            if expected_method._return_value is _UNSET:
                expected_method._return_value = result

        if expected_method._exception:
            raise expected_method._exception

        if expected_method._return_value is _UNSET:
            return None
        return expected_method._return_value

    def __getattr__(self, name):
        """Raise an AttributeError with a helpful message."""

        raise AttributeError(
            'MockMethod has no attribute "%s". Did you remember to put your mocks in replay mode?' % name
        )

    def __iter__(self):
        """Raise a TypeError with a helpful message."""
        raise TypeError("MockMethod cannot be iterated. Did you remember to put your mocks in replay mode?")

    def __next__(self):
        """Raise a TypeError with a helpful message."""
        raise TypeError("MockMethod cannot be iterated. Did you remember to put your mocks in replay mode?")

    next = __next__

    def _pop_next_method(self):
        """Pop the next method from our call queue."""
        try:
            return self._call_queue.popleft()
        except IndexError:
            exception = UnexpectedMethodCallError(self, None)
            self._exception_list.append(exception)
            raise exception

    def _verify_method_call(self):
        """Verify the called method is expected.

        This can be an ordered method, or part of an unordered set.

        Returns:
          The expected mock method.

        Raises:
          UnexpectedMethodCall if the method called was not expected.
        """

        expected = self._pop_next_method()

        # Loop here, because we might have a MethodGroup followed by another
        # group.
        while isinstance(expected, MethodGroup):
            expected, method = expected.method_called(self)
            if method is not None:
                return method

        # This is a mock method, so just check equality.
        if expected != self:
            exception = UnexpectedMethodCallError(self, expected)
            self._exception_list.append(exception)
            raise exception

        return expected

    def __str__(self):
        params = ", ".join(
            [repr(p) for p in self._params or []] + ["%s=%r" % x for x in sorted((self._named_params or {}).items())]
        )
        # An unconfigured return value is reported as None, matching what a call
        # with no configured return actually yields.
        return_value = None if self._return_value is _UNSET else self._return_value
        if self._description and self._name == "__call__":
            return "%s(%s) -> %r" % (self._description, params, return_value)

        full_desc = "%s(%s) -> %r" % (self._name, params, return_value)
        if self._description:
            full_desc = "%s.%s" % (self._description, full_desc)
        return full_desc

    def __eq__(self, rhs):
        """Test whether this MockMethod is equivalent to another MockMethod.

        Args:
          # rhs: the right hand side of the test
          rhs: MockMethod
        """

        return (
            isinstance(rhs, MockMethod)
            and self._name == rhs._name
            and self._params == rhs._params
            and self._named_params == rhs._named_params
        )

    def __hash__(self):
        return id(self)

    def __ne__(self, rhs):
        """Test whether this MockMethod is not equivalent to another MockMethod.

        Args:
          # rhs: the right hand side of the test
          rhs: MockMethod
        """

        return not self == rhs

    def get_possible_group(self):
        """Returns a possible group from the end of the call queue or None if no
        other methods are on the stack.
        """

        # Remove this method from the tail of the queue so we can add it to a
        # group.
        this_method = self._call_queue.pop()
        if this_method != self:
            raise Error("Current method is not at the end of the call queue.")

        # Determine if the tail of the queue is a group, or just a regular
        # ordered mock method.
        group = None
        try:
            group = self._call_queue[-1]
        except IndexError:
            pass

        return group

    def _check_and_create_new_group(self, group_name, group_class):
        """Checks if the last method (a possible group) is an instance of our
        group_class. Adds the current method to this group or creates a new
        one.

        Args:

          group_name: the name of the group.
          group_class: the class used to create instance of this new group
        """
        group = self.get_possible_group()

        # If this is a group, and it is the correct group, add the method.
        if isinstance(group, group_class) and group.group_name() == group_name:
            group.add_method(self)
            return self

        # Create a new group and add the method.
        new_group = group_class(group_name, self._exception_list)
        new_group.add_method(self)
        self._call_queue.append(new_group)
        return self

    def any_order(self, group_name="default"):
        """Move this method into a group of unordered calls.

        A group of unordered calls must be defined together, and must be
        executed in full before the next expected method can be called. There
        can be multiple groups that are expected serially, if they are given
        different group names.  The same group name can be reused if there is a
        standard method call, or a group with a different name, spliced between
        usages.

        Args:
          group_name: the name of the unordered group.

        Returns:
          self
        """
        return self._check_and_create_new_group(group_name, UnorderedGroup)

    def multiple_times(self, group_name="default"):
        """Move this method into group of calls which may be called multiple
        times.

        A group of repeating calls must be defined together, and must be
        executed in full before the next expected method can be called.

        Args:
          group_name: the name of the unordered group.

        Returns:
          self
        """
        return self._check_and_create_new_group(group_name, MultipleTimesGroup)

    def returns(self, return_value):
        """Set the value to return when this method is called.

        Args:
          # return_value can be anything.
        """

        self._return_value = return_value
        return return_value

    def and_return(self, return_value):
        """Semantic sugar for returns."""
        return self.returns(return_value)

    def raises(self, exception):
        """Set the exception to raise when this method is called.

        Args:
          # exception: the exception to raise when this method is called.
          exception: Exception
        """

        self._exception = exception

    def and_raise(self, exception):
        """Semantic sugar for raises."""
        return self.raises(exception)

    def with_side_effects(self, side_effects):
        """Set the side effects that are simulated when this method is called.

        Args:
          side_effects: A callable which modifies the parameters or other
            relevant state which a given test case depends on.

        Returns:
          Self for chaining with AndReturn and AndRaise.
        """
        self._side_effects = side_effects
        return self

    _PopNextMethod = _pop_next_method
    _VerifyMethodCall = _verify_method_call
    GetPossibleGroup = get_possible_group
    _CheckAndCreateNewGroup = _check_and_create_new_group
    InAnyOrder = any_order
    MultipleTimes = multiple_times
    AndReturn = returns
    AndRaise = raises
    WithSideEffects = with_side_effects
