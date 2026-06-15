from .exceptions import UnexpectedMethodCallError


class MethodGroup(object):
    """Base class containing common behaviour for MethodGroups."""

    def __init__(self, group_name, exception_list):
        """Construct a new method group.

        Args:
          # group_name: the name of the method group
          # exception_list: list of exceptions; any exceptions thrown by this
          #     instance are appended to this list.
          group_name: str
          exception_list: list
        """
        self._group_name = group_name
        self._exception_list = exception_list

    def group_name(self):
        return self._group_name

    def __str__(self):
        return '<%s "%s">' % (self.__class__.__name__, self._group_name)

    def add_method(self, mock_method):
        raise NotImplementedError

    def method_called(self, mock_method):
        raise NotImplementedError

    def is_satisfied(self):
        raise NotImplementedError

    AddMethod = add_method
    MethodCalled = method_called
    IsSatisfied = is_satisfied


class UnorderedGroup(MethodGroup):
    """UnorderedGroup holds a set of method calls that may occur in any order.

    This construct is helpful for non-deterministic events, such as iterating
    over the keys of a dict.
    """

    def __init__(self, group_name, exception_list):
        super().__init__(group_name, exception_list)
        self._methods = []

    def __str__(self):
        return '%s "%s" pending calls:\n%s' % (
            self.__class__.__name__,
            self._group_name,
            "\n".join(str(method) for method in self._methods),
        )

    def add_method(self, mock_method):
        """Add a method to this group.

        Args:
          mock_method: A mock method to be added to this group.
        """

        self._methods.append(mock_method)

    def method_called(self, mock_method):
        """Remove a method call from the group.

        If the method is not in the set, an UnexpectedMethodCallError will be
        raised.

        Args:
          mock_method: a mock method that should be equal to a method in the
          group.

        Returns:
          The mock method from the group

        Raises:
          UnexpectedMethodCallError if the mock_method was not in the group.
        """

        # Check to see if this method exists, and if so, remove it from the set
        # and return it.
        for method in self._methods:
            if method == mock_method:
                # Remove the called mock_method instead of the method in the
                # group. The called method will match any comparators when
                # equality is checked during removal. The method in the group
                # could pass a comparator to another comparator during the
                # equality check.
                self._methods.remove(mock_method)

                # If this group is not empty, put it back at the head of the
                # queue.
                if not self.is_satisfied():
                    mock_method._call_queue.appendleft(self)

                return self, method

        exception = UnexpectedMethodCallError(mock_method, self)
        self._exception_list.append(exception)
        raise exception

    def is_satisfied(self):
        """Return True if there are not any methods in this group."""

        return len(self._methods) == 0

    AddMethod = add_method
    MethodCalled = method_called
    IsSatisfied = is_satisfied


class MultipleTimesGroup(MethodGroup):
    """MultipleTimesGroup holds methods that may be called any number of times.

    Note: Each method must be called at least once.

    This is helpful, if you don't know or care how many times a method is
    called.
    """

    def __init__(self, group_name, exception_list):
        super().__init__(group_name, exception_list)
        self._methods = set()
        self._methods_left = set()

    def add_method(self, mock_method):
        """Add a method to this group.

        Args:
          mock_method: A mock method to be added to this group.
        """

        self._methods.add(mock_method)
        self._methods_left.add(mock_method)

    def method_called(self, mock_method):
        """Remove a method call from the group.

        If the method is not in the set, an UnexpectedMethodCallError will be
        raised.

        Args:
          mock_method: a mock method that should be equal to a method in the
            group.

        Returns:
          The mock method from the group

        Raises:
          UnexpectedMethodCallError if the mock_method was not in the group.
        """

        # Check to see if this method exists, and if so add it to the set of
        # called methods.
        for method in self._methods:
            if method == mock_method:
                self._methods_left.discard(method)
                # Always put this group back on top of the queue, because we
                # don't know when we are done.
                mock_method._call_queue.appendleft(self)
                return self, method

        if self.is_satisfied():
            next_method = mock_method._pop_next_method()
            return next_method, None
        else:
            exception = UnexpectedMethodCallError(mock_method, self)
            self._exception_list.append(exception)
            raise exception

    def is_satisfied(self):
        """Return True if all methods in this group are called at least once."""
        return len(self._methods_left) == 0

    AddMethod = add_method
    MethodCalled = method_called
    IsSatisfied = is_satisfied
