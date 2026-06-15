# Python imports
import unittest


class MoxMetaTestBase(type):
    """Metaclass to add mox cleanup and verification to every test.
    As the mox unit testing class is being constructed (MoxTestBase or a
    subclass), this metaclass will modify all test functions to call the
    CleanUpMox method of the test class after they finish. This means that
    unstubbing and verifying will happen for every test with no additional
    code, and any failures will result in test failures as opposed to errors.
    """

    def __init__(cls, name, bases, d):
        super().__init__(name, bases, d)
        # type.__init__(cls, name, bases, d)

        # also get all the attributes from the base classes to account
        # for a case when test class is not the immediate child of MoxTestBase
        for base in bases:
            for attr_name in dir(base):
                if attr_name not in d:
                    try:  # pragma: nocover
                        d[attr_name] = getattr(base, attr_name)
                    except AttributeError:
                        continue

        for func_name, func in d.items():
            if func_name.startswith("test") and callable(func):
                setattr(cls, func_name, MoxMetaTestBase.clean_up_test(cls, func))

    @staticmethod
    def clean_up_test(cls, func):
        """Adds Mox cleanup code to any MoxTestBase method.
        Always unsets stubs after a test. Will verify all mocks for tests that
        otherwise pass.
        Args:
          cls: MoxTestBase or subclass; the class whose test method we are
            altering.
          func: method; the method of the MoxTestBase test class we wish to
            alter.
        Returns:
          The modified method.
        """
        # Internal imports
        from mox import Mox, stubbingout

        def new_method(self, *args, **kwargs):
            mox_obj = getattr(self, "mox", None)
            stubout_obj = getattr(self, "stubs", None)
            cleanup_mox = False
            cleanup_stubout = False
            if mox_obj and isinstance(mox_obj, Mox):
                cleanup_mox = True
            if stubout_obj and isinstance(stubout_obj, stubbingout.StubOutForTesting):
                cleanup_stubout = True
            try:
                try:
                    func(self, *args, **kwargs)
                finally:
                    if cleanup_mox:
                        mox_obj.unset_stubs()
                    if cleanup_stubout:
                        stubout_obj.unset_all()
                        stubout_obj.smart_unset_all()
                if cleanup_mox:
                    mox_obj.verify_all()
            finally:
                # Don't let this test's Mox instances linger in the global
                # registry, where they would leak and contaminate later tests.
                Mox.reset_instances()

        new_method.__name__ = func.__name__
        new_method.__doc__ = func.__doc__
        new_method.__module__ = func.__module__
        return new_method

    CleanUpTest = clean_up_test


_MoxTestBase = MoxMetaTestBase("_MoxTestBase", (unittest.TestCase,), {})


class MoxTestBase(_MoxTestBase):
    # class MoxTestBase(unittest.TestCase, metaclass=MoxMetaTestBase):
    """Convenience test class to make stubbing easier.
    Sets up a "mox" attribute which is an instance of Mox (any mox tests will
    want this), and a "stubs" attribute that is an instance of
    StubOutForTesting (needed at times). Also automatically unsets any stubs
    and verifies that all mock methods have been called at the end of each
    test, eliminating boilerplate code.
    """

    def setUp(self):
        # Internal imports
        from mox import Mox, stubbingout

        super().setUp()
        self.mox = Mox()
        self.stubs = stubbingout.StubOutForTesting()
