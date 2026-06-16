import difflib


class ObjectResolutionError(TypeError):
    def __init__(self, path):
        message = f"Could not resolve class, object or module from supplied reference: {path!r}"
        super().__init__(message)


class Error(AssertionError):
    """Base exception for this module."""

    pass


class ExpectedMethodCallsError(Error):
    """Raised when Verify() is called before all expected methods have been
    called
    """

    def __init__(self, expected_methods):
        """Init exception.

        Args:
          # expected_methods: A sequence of MockMethod objects that should have
          #   been called.

          expected_methods: [MockMethod]

        Raises:
          ValueError: if expected_methods contains no methods.
        """

        if not expected_methods:
            raise ValueError("There must be at least one expected method")
        Error.__init__(self)
        self._expected_methods = expected_methods

    def __str__(self):
        calls = "\n".join(["%3d.  %s" % (i, m) for i, m in enumerate(self._expected_methods)])
        return "Verify: Expected methods never called:\n%s" % (calls,)


class UnexpectedMethodCallError(Error):
    """Raised when an unexpected method is called.

    This can occur if a method is called with incorrect parameters, or out of
    the specified order.
    """

    def __init__(self, unexpected_method, expected):
        """Init exception.

        Args:
          # unexpected_method: MockMethod that was called but was not at the
          #   head of the expected_method queue.
          # expected: MockMethod or UnorderedGroup the method should have
          #   been in.
          unexpected_method: MockMethod
          expected: MockMethod or UnorderedGroup
        """

        Error.__init__(self)
        if expected is None:
            self._str = 'Unexpected method call "%s"' % (unexpected_method,)
        else:
            differ = difflib.Differ()
            diff = differ.compare(str(unexpected_method).splitlines(True), str(expected).splitlines(True))
            self._str = "Unexpected method call.  unexpected:-  expected:+\n%s" % (
                "\n".join(line.rstrip() for line in diff),
            )

    def __str__(self):
        return self._str


class UnknownMethodCallError(Error):
    """Raised if an unknown method is requested of the mock object."""

    def __init__(self, unknown_method_name):
        """Init exception.

        Args:
          # unknown_method_name: Method call that is not part of the mocked
          #   class's public interface.
          unknown_method_name: str
        """

        Error.__init__(self)
        self._unknown_method_name = unknown_method_name

    def __str__(self):
        return "Method called is not a member of the object: %s" % self._unknown_method_name


class PrivateAttributeError(Error):
    """
    Raised if a MockObject is passed a private additional attribute name.
    """

    def __init__(self, attr):
        Error.__init__(self)
        self._attr = attr

    def __str__(self):
        return "Attribute '%s' is private and should not be available in a  mock object." % self._attr


class ExpectedMockCreationError(Error):
    """Raised if mocks should have been created by StubOutClassWithMocks."""

    def __init__(self, expected_mocks):
        """Init exception.

        Args:
          # expected_mocks: A sequence of MockObjects that should have been
          #   created

        Raises:
          ValueError: if expected_mocks contains no methods.
        """

        if not expected_mocks:
            raise ValueError("There must be at least one expected method")
        Error.__init__(self)
        self._expected_mocks = expected_mocks

    def __str__(self):
        mocks = "\n".join(["%3d.  %s" % (i, m) for i, m in enumerate(self._expected_mocks)])
        return "Verify: Expected mocks never created:\n%s" % (mocks,)


class UnexpectedMockCreationError(Error):
    """Raised if too many mocks were created by StubOutClassWithMocks."""

    def __init__(self, instance, *params, **named_params):
        """Init exception.

        Args:
          # instance: the type of obejct that was created
          # params: parameters given during instantiation
          # named_params: named parameters given during instantiation
        """

        Error.__init__(self)
        self._instance = instance
        self._params = params
        self._named_params = named_params

    def __str__(self):
        args = ", ".join(["%s" % v for i, v in enumerate(self._params)])
        error = "Unexpected mock creation: %s(%s" % (self._instance, args)

        if self._named_params:
            error += ", " + ", ".join(["%s=%s" % (k, v) for k, v in self._named_params.items()])

        error += ")"
        return error


class SwallowedExceptionError(Error):
    """Raised when verify() is called after something already threw an
    exception.

    This means that the exception that was thrown was somehow swallowed,
    allowing the test to continue when it should not have.
    """

    def __init__(self, previous_exceptions):
        """Init exception.

        Args:
          # previous_exceptions: A sequence of Error objects that were raised.
          previous_exceptions: [Error]
        """

        Error.__init__(self)
        self._previous_exceptions = previous_exceptions

    def __str__(self):
        exceptions = "\n".join(
            ["%3d.  %s: %s" % (i, e.__class__.__name__, e) for i, e in enumerate(self._previous_exceptions)]
        )
        return "Previous exceptions thrown:\n%s" % (exceptions,)
