import re

import pytest

import mox

from . import mox_test_helper
from .test_helpers.subpackage.faraway import FarAwayClass


@pytest.fixture
def mock():
    return mox.Mox()


class TestStringimports:
    def test_existing_function(self):
        with mox.stubout("test.test_helpers.subpackage.faraway.FarAwayClass.distant_method") as mock_distant_method:
            mock_distant_method().returns(True)

        obj = FarAwayClass()
        assert obj.distant_method() is True

    def test_missing_function(self):
        with pytest.raises(AttributeError, match="type object 'FarAwayClass' has no attribute 'missing_method'"):
            with mox.stubout("test.test_helpers.subpackage.faraway.FarAwayClass.missing_method") as mock_distant_method:
                mock_distant_method().returns(True)

    def test_missing_class(self):
        with pytest.raises(
            AttributeError, match="module 'test.test_helpers.subpackage.faraway' has no attribute 'MissingClass'"
        ):
            with mox.stubout("test.test_helpers.subpackage.faraway.MissingClass.distant_method") as mock_distant_method:
                mock_distant_method().returns(True)

    def test_missing_module(self):
        with pytest.raises(AttributeError, match="module 'test.test_helpers.subpackage' has no attribute 'missing'"):
            with mox.stubout("test.test_helpers.subpackage.missing.FarAwayClass.distant_method") as mock_distant_method:
                mock_distant_method().returns(True)

    def test_missing_package(self):
        with pytest.raises(AttributeError, match="module 'test.test_helpers' has no attribute 'missing_package'"):
            with mox.stubout(
                "test.test_helpers.missing_package.faraway.FarAwayClass.distant_method"
            ) as mock_distant_method:
                mock_distant_method().returns(True)

    def test_object_resolution_error(self):
        with pytest.raises(
            mox.exceptions.ObjectResolutionError,
            match="Could not resolve class, object or module from supplied reference",
        ):
            with mox.stubout("testtest_helpersmissing_packagefarawayFarAwayClassdistant_method") as mock_distant_method:
                mock_distant_method().returns(True)


class TestMockObjectStringImports:
    """Verify that the MockObject class works as expected with string imports."""

    def test_description_mocked_object(self, mock):
        obj = FarAwayClass()

        mock.stubout("test.test_helpers.subpackage.faraway.FarAwayClass.distant_method")
        obj.distant_method().returns(True)

        mock.replay_all()
        assert obj.distant_method._description == "FarAwayClass.distant_method"
        mock.reset_all()

    def test_description_module_function(self, mock):
        mock.stubout("test.mox_test_helper.MyTestFunction")
        mox_test_helper.MyTestFunction(one=1, two=2).returns(True)

        mock.replay_all()
        assert mox_test_helper.MyTestFunction._description == "function test.mox_test_helper.MyTestFunction"
        mock.reset_all()

    def test_description_mocked_class(self, mock):
        obj = FarAwayClass()

        mock.stubout("test.test_helpers.subpackage.faraway.FarAwayClass.distant_method")
        obj.distant_method().returns(True)

        mock.replay_all()
        assert obj.distant_method._description == "FarAwayClass.distant_method"
        mock.reset_all()

    def test_description_class_method(self, mock):
        obj = mox_test_helper.SpecialClass()

        mock.stubout("test.mox_test_helper.SpecialClass.class_method")
        mox_test_helper.SpecialClass.class_method().returns(True)

        mock.replay_all()
        assert obj.class_method._description == "SpecialClass.class_method"
        mock.unset_stubs()
        mock.reset_all()

    def test_description_static_method_mock_class(self, mock):
        mock.stubout("test.mox_test_helper.SpecialClass.static_method")
        mox_test_helper.SpecialClass.static_method().returns(True)

        mock.replay_all()
        assert mox_test_helper.SpecialClass.static_method._description in [
            "SpecialClass.static_method",
            "function test.mox_test_helper.static_method",
        ]
        mock.reset_all()

    def test_description_static_method_mock_instance(self, mock):
        obj = mox_test_helper.SpecialClass()

        mock.stubout("test.mox_test_helper.SpecialClass.static_method")
        obj.static_method().returns(True)

        mock.replay_all()
        assert obj.static_method._description in [
            "SpecialClass.static_method",
            "function test.mox_test_helper.static_method",
        ]
        mock.reset_all()


class TestMockObjectContextManagerStringImports:
    """Verify that the MockObject class works as expected with context managers and string imports."""

    def test_description_mocked_object(self):
        obj = FarAwayClass()

        with mox.stubout("test.test_helpers.subpackage.faraway.FarAwayClass.distant_method") as stub, mox.expect:
            obj.distant_method().returns(True)

        assert obj.distant_method._description == "FarAwayClass.distant_method"

        mox.reset(stub)

    def test_description_module_function(self):
        with mox.stubout("test.mox_test_helper.MyTestFunction") as stub, mox.expect:
            mox_test_helper.MyTestFunction(one=1, two=2).returns(True)

        assert mox_test_helper.MyTestFunction._description == "function test.mox_test_helper.MyTestFunction"

        mox.reset(stub)

    def test_description_mocked_class(self):
        obj = FarAwayClass()

        with mox.stubout("test.test_helpers.subpackage.faraway.FarAwayClass.distant_method") as stub, mox.expect:
            obj.distant_method().returns(True)

        assert obj.distant_method._description == "FarAwayClass.distant_method"

        mox.reset(stub)

    def test_description_class_method(self):
        obj = mox_test_helper.SpecialClass()

        with mox.stubout("test.mox_test_helper.SpecialClass.class_method") as stub, mox.expect:
            mox_test_helper.SpecialClass.class_method().returns(True)

        assert obj.class_method._description == "SpecialClass.class_method"

        mox.reset(stub)

    def test_description_static_method_mock_class(self):
        with mox.stubout("test.mox_test_helper.SpecialClass.static_method") as stub, mox.expect:
            mox_test_helper.SpecialClass.static_method().returns(True)

        assert mox_test_helper.SpecialClass.static_method._description in [
            "SpecialClass.static_method",
            "function test.mox_test_helper.static_method",
        ]

        mox.reset(stub)

    def test_description_static_method_mock_instance(self):
        obj = mox_test_helper.SpecialClass()

        with mox.stubout("test.mox_test_helper.SpecialClass.static_method") as stub, mox.expect:
            obj.static_method().returns(True)

        assert obj.static_method._description in [
            "SpecialClass.static_method",
            "function test.mox_test_helper.static_method",
        ]

        mox.reset(stub)


class TestMoxStringImports:
    """Verify Mox works correctly with string imports."""

    def test_stub_out_method__unbound__subclass__comparator(self, mock):
        mock_value = mock.stubout("test.mox_test_helper.TestClassFromAnotherModule.value")
        mock_value(mox.is_a(mox_test_helper.ChildClassFromAnotherModule)).returns("foo")
        mock.replay_all()

        instance = mox_test_helper.ChildClassFromAnotherModule()
        actual = mox_test_helper.TestClassFromAnotherModule.value(instance)

        mock.verify_all()
        mock.unset_stubs()
        assert actual == "foo"

    def test_stub_out__signature_matching_init_(self, mock):
        mock_init = mock.stubout("test.mox_test_helper.ExampleClass.__init__")
        mock_init(mox.IgnoreArg())

        mock.replay_all()
        # Create an instance of a child class, which calls the parent
        # __init__
        mox_test_helper.ChildExampleClass()
        mock.verify_all()
        mock.unset_stubs()

    def test_stub_out_class(self, mock):
        factory = mock.stubout_class("test.mox_test_helper.CallableClass")

        # Instance one
        mock_one = factory(1, 2)
        mock_one.value().returns("mock")

        # Instance two
        mock_two = factory(8, 9)
        mock_two("one").returns("called mock")

        mock.replay_all()

        one = mox_test_helper.CallableClass(1, 2)
        actual_one = one.value()

        two = mox_test_helper.CallableClass(8, 9)
        actual_two = two("one")

        mock.verify_all()
        assert mox_test_helper.CallableClass == factory
        mock.unset_stubs()

        # Verify the correct mocks were returned
        assert mock_one == one
        assert mock_two == two

        # Verify
        assert "mock" == actual_one
        assert "called mock" == actual_two

    def test_stub_out_class_with_meta_class(self, mock):
        factory = mock.stubout_class(mox_test_helper, "ChildClassWithMetaClass")

        mock_one = mox_test_helper.ChildClassWithMetaClass(kw=1)
        mock_one.value().returns("mock")

        mock.replay_all()

        one = mox_test_helper.ChildClassWithMetaClass(kw=1)
        actual_one = one.value()

        mock.verify_all()
        assert mox_test_helper.ChildClassWithMetaClass == factory
        mock.unset_stubs()

        # Verify the correct mocks were returned
        assert mock_one == one

        # Verify
        assert "mock" == actual_one
        assert "meta" == one.x

    def test_stub_out_class__a_b_c_meta(self, mock):
        mock.stubout_class("test.mox_test_helper.CallableSubclassOfMyDictABC")

        mock_foo = mox_test_helper.CallableSubclassOfMyDictABC(foo="!mock bar")
        mock_foo["foo"].returns("mock bar")
        mock_spam = mox_test_helper.CallableSubclassOfMyDictABC(spam="!mock eggs")
        mock_spam("beans").returns("called mock")

        mock.replay_all()

        foo = mox_test_helper.CallableSubclassOfMyDictABC(foo="!mock bar")
        actual_foo_bar = foo["foo"]

        spam = mox_test_helper.CallableSubclassOfMyDictABC(spam="!mock eggs")
        actual_spam = spam("beans")

        mock.verify_all()
        mock.unset_stubs()

        # Verify the correct mocks were returned
        assert mock_foo == foo
        assert mock_spam == spam

        # Verify
        assert "mock bar" == actual_foo_bar
        assert "called mock" == actual_spam

    def test_stub_out_class__not_a_class(self, mock):
        with pytest.raises(TypeError):
            mock.stubout_class("test.mox_test_helper.MyTestFunction")

    def test_stub_out_class_not_enough_created(self, mock):
        mock.stubout_class("test.mox_test_helper.CallableClass")

        mox_test_helper.CallableClass(1, 2)
        mox_test_helper.CallableClass(8, 9)

        mock.replay_all()
        mox_test_helper.CallableClass(1, 2)

        assert len(mock.stubs.cache) == 1
        with pytest.raises(mox.ExpectedMockCreationError):
            mock.verify_all()
        assert len(mock.stubs.cache) == 0

    def test_stub_out_class_wrong_signature(self, mock):
        factory = mock.stubout_class("test.mox_test_helper.CallableClass")

        with pytest.raises(AttributeError):
            mox_test_helper.CallableClass()

        assert mox_test_helper.CallableClass == factory
        mock.unset_stubs()

    def test_stub_out_class_wrong_parameters(self, mock):
        factory = mock.stubout_class("test.mox_test_helper.CallableClass")

        mox_test_helper.CallableClass(1, 2)

        mock.replay_all()

        with pytest.raises(mox.UnexpectedMethodCallError):
            mox_test_helper.CallableClass(8, 9)
        assert mox_test_helper.CallableClass == factory
        mock.unset_stubs()

    def test_stub_out_class_too_many_created(self, mock):
        factory = mock.stubout_class("test.mox_test_helper.CallableClass")

        mox_test_helper.CallableClass(1, 2)

        mock.replay_all()
        mox_test_helper.CallableClass(1, 2)
        with pytest.raises(mox.UnexpectedMockCreationError):
            mox_test_helper.CallableClass(8, 9)

        assert mox_test_helper.CallableClass == factory
        mock.unset_stubs()

    def test_stub_out_first_class_method_verifies_signature(self, mock):
        stub = mock.stubout("test.mox_test_helper.MyTestFunction")
        assert mox_test_helper.MyTestFunction == stub

        # Wrong number of arguments
        with pytest.raises(AttributeError):
            mox_test_helper.MyTestFunction(1)
        mock.unset_stubs()

    def test_method_signature_verification(self, mock):
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
                mock.stubout("test.mox_test_helper.ExampleClass.test_method")
                obj = mox_test_helper.ExampleClass()
            else:
                obj = mox_test_helper.ExampleClass()
                mock.stubout(obj, "test_method")

            if raises:
                with pytest.raises(AttributeError):
                    obj.test_method(*args, **kwargs)
            else:
                obj.test_method(*args, **kwargs)
            mock.unset_stubs()

    def test_stub_out_re_works(self, mock):
        stub = mock.stubout("re.search")

        re.search("a", "ivan").returns("true")

        mock.replay_all()
        result = mox_test_helper.TestClass().re_search()
        mock.verify_all()

        assert re.search == stub
        mock.unset_stubs()

        assert result == "true"

    def test_swallowed_unexpected_mock_creation(self, mock):
        """Test that a swallowed UnexpectedMockCreationError will be re-raised."""
        factory = mock.stubout_class("test.mox_test_helper.CallableClass")
        mock.replay_all()

        def call():
            try:
                mox_test_helper.CallableClass(1, 2)
            except mox.UnexpectedMockCreationError:
                pass

        # UnexpectedMockCreationError swallowed
        call()

        assert mox_test_helper.CallableClass == factory
        assert len(mock.stubs.cache) == 1
        with pytest.raises(mox.SwallowedExceptionError):
            mock.verify_all()
        assert len(mock.stubs.cache) == 0


class TestMoxContextManagerStringimports:
    """Verify Mox works correctly when using context managers and string imports."""

    def test_create_object_using_simple_imported_module_class_method(self):
        """Mox should create a mock object for a class from a module imported
        using a simple 'import module' statement"""

        with mox.stubout("test.mox_test_helper.ExampleClass.class_method") as stub:
            example_obj = mox.create(mox_test_helper.ExampleClass)
            mox_test_helper.ExampleClass.class_method().returns(example_obj)

        def call_helper_class_method():
            return mox_test_helper.ExampleClass.class_method()

        expected_obj = call_helper_class_method()
        mox.verify(stub, example_obj)

        assert expected_obj == example_obj

    def test_stub_out_method__unbound__subclass__comparator(self):
        with mox.stubout("test.mox_test_helper.TestClassFromAnotherModule.value") as stub:
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
        with mox.stubout("test.mox_test_helper.TestClassFromAnotherModule.value") as stub:
            ...

        with stub._expect:
            mox_test_helper.TestClass.optional_args(mox.IgnoreArg(), foo=2)

        t = mox_test_helper.TestClass()
        mox_test_helper.TestClass.optional_args(t, foo=2)

        mox.verify(stub)
        m = mox.Mox._instances[stub._mox_id]
        m.unset_stubs()

    def test_stub_out_method__unbound__named_using_positional(self):
        """Check positional parameters can be matched to keyword arguments."""
        with mox.stubout("test.mox_test_helper.ExampleClass.named_params") as stub:
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
        with mox.stubout("test.mox_test_helper.ExampleClass.test_method") as stub:
            ...

        instance = mox_test_helper.ExampleClass()

        with stub._expect:
            mox_test_helper.ExampleClass.test_method(instance, "one", "two", "nine")

        mox_test_helper.ExampleClass.test_method(instance, "one", "two", "nine")

        mox.verify(stub)
        m = mox.Mox._instances[stub._mox_id]
        m.unset_stubs()

    def test_stub_out_method__unbound__special_args(self):
        with mox.stubout("test.mox_test_helper.ExampleClass.special_args") as stub:
            ...

        instance = mox_test_helper.ExampleClass()

        with stub._expect:
            mox_test_helper.ExampleClass.special_args(instance, "foo", None, bar="bar")

        mox_test_helper.ExampleClass.special_args(instance, "foo", None, bar="bar")

        mox.verify(stub)
        m = mox.Mox._instances[stub._mox_id]
        m.unset_stubs()

    def test_stub_out_method__bound__simple_test(self):
        t = mox.create(mox_test_helper.TestClass)
        with t._expect:
            t.method_with_args(mox.IgnoreArg(), mox.IgnoreArg()).returns("foo")

        actual = t.method_with_args(None, None)

        mox.verify(t)
        m = mox.Mox._instances[t._mox_id]
        m.unset_stubs()
        assert "foo" == actual

    def test_stub_out_method__bound__named_using_positional(self):
        """Check positional parameters can be matched to keyword arguments."""
        with mox.stubout("test.mox_test_helper.ExampleClass.named_params") as stub:
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
        with mox.stubout("test.mox_test_helper.ExampleClass.test_method") as stub:
            ...

        instance = mox_test_helper.ExampleClass()
        with stub._expect:
            instance.test_method(instance, "one", "two", "nine")

        instance.test_method(instance, "one", "two", "nine")

        mox.verify(stub)
        m = mox.Mox._instances[stub._mox_id]
        m.unset_stubs()

    def test_stub_out_method__bound__special_args(self):
        with mox.stubout("test.mox_test_helper.ExampleClass.special_args") as stub:
            ...

        instance = mox_test_helper.ExampleClass()

        with stub._expect:
            instance.special_args(instance, "foo", None, bar="bar")

        instance.special_args(instance, "foo", None, bar="bar")

        mox.verify(stub)
        m = mox.Mox._instances[stub._mox_id]
        m.unset_stubs()

    def test_stub_out__signature_matching_init_(self):
        with mox.stubout("test.mox_test_helper.ExampleClass.__init__") as stub:
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
        with mox.stubout("test.mox_test_helper.TestClassFromAnotherModule") as stub:
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
        with mox.stubout.klass("test.mox_test_helper.CallableClass") as stub:
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
        with mox.stubout.klass("test.mox_test_helper.ChildClassWithMetaClass") as stub:
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
        with mox.stubout.klass("test.mox_test_helper.CallableSubclassOfMyDictABC") as stub:
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
        with mox.stubout.klass("test.mox_test_helper.CallableClass") as stub:
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
        with mox.stubout.klass("test.mox_test_helper.CallableClass") as stub:
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
        with mox.stubout.klass("test.mox_test_helper.CallableClass") as stub:
            ...

        with stub._expect:
            mox_test_helper.CallableClass(1, 2)

        with pytest.raises(mox.UnexpectedMethodCallError):
            mox_test_helper.CallableClass(8, 9)
        m = mox.Mox._instances[stub._mox_id]
        m.unset_stubs()

    def test_stub_out_class_too_many_created(self):
        with mox.stubout.klass("test.mox_test_helper.CallableClass") as stub:
            ...

        with stub._expect:
            mox_test_helper.CallableClass(1, 2)

        mox_test_helper.CallableClass(1, 2)
        with pytest.raises(mox.UnexpectedMockCreationError):
            mox_test_helper.CallableClass(8, 9)

        m = mox.Mox._instances[stub._mox_id]
        m.unset_stubs()

    # def test_warns_user_if_mocking_mock(self):
    #     """Test that user is warned if they try to stub out a MockAnything."""
    #     with mox.stubout("TestClass.my_static_method"):
    #         with pytest.raises(TypeError):
    #             with mox.stubout("TestClass.my_static_method"):
    #                 ...

    def test_stub_out_first_class_method_verifies_signature(self):
        with mox.stubout("test.mox_test_helper.MyTestFunction") as stub:
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
            with mox.stubout("test.mox_test_helper.ExampleClass.test_method") as stub:
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

    def test_stub_out_re_works(self):
        with mox.stubout("re.search") as stub, mox.expect:
            re.search("a", "ivan").returns("true")

        result = mox_test_helper.TestClass().re_search()

        mox.verify(stub)
        m = mox.Mox._instances[stub._mox_id]
        m.unset_stubs()

        assert result == "true"

    def test_swallowed_unexpected_mock_creation(self):
        """Test that a swallowed UnexpectedMockCreationError will be re-raised."""
        with mox.stubout.klass("test.mox_test_helper.CallableClass") as stub:
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
