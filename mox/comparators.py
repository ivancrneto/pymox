import re
from typing import Any, Callable, Iterable

from .exceptions import Error


class Comparator:
    """Base class for all Mox comparators.

    A Comparator can be used as a parameter to a mocked method when the exact
    value is not known.  For example, the code you are testing might build up a
    long SQL string that is passed to your mock DAO. You're only interested
    that the IN clause contains the proper primary keys, so you can set your
    mock up as follows:

    mock_dao.RunQuery(StrContains('IN (1, 2, 4, 5)')).AndReturn(mock_result)

    Now whatever query is passed in must contain the string 'IN (1, 2, 4, 5)'.

    A Comparator may replace one or more parameters, for example:
    # return at most 10 rows
    mock_dao.RunQuery(StrContains('SELECT'), 10)

    or

    # Return some non-deterministic number of rows
    mock_dao.RunQuery(StrContains('SELECT'), IsA(int))
    """

    def equals(self, rhs: Any) -> bool:
        """Special equals method that all comparators must implement.

        Args:
          rhs: any python object
        """

        raise NotImplementedError

    def __eq__(self, rhs: object) -> bool:
        return self.equals(rhs)

    def __ne__(self, rhs: object) -> bool:
        return not self.equals(rhs)

    def __hash__(self) -> int:
        # __eq__ is overridden, which otherwise makes comparators unhashable in
        # Python 3.  Hash by identity so comparators can be used in sets/dicts.
        return id(self)


class Is(Comparator):
    """Comparison class used to check identity, instead of equality."""

    def __init__(self, obj: Any) -> None:
        self._obj = obj

    def equals(self, rhs: Any) -> bool:
        return rhs is self._obj

    def __repr__(self) -> str:
        return "<is %r (%s)>" % (self._obj, id(self._obj))


class IsA(Comparator):
    """This class wraps a basic Python type or class.  It is used to verify
    that a parameter is of the given type or class.

    Example:
    mock_dao.Connect(IsA(DbConnectInfo))
    """

    def __init__(self, class_name: Any) -> None:
        """Initialize IsA

        Args:
          class_name: basic python type or a class
        """

        self._class_name = class_name

    def equals(self, rhs: Any) -> bool:
        """Check to see if the RHS is an instance of class_name.

        Args:
          # rhs: the right hand side of the test
          rhs: object

        Returns:
          bool
        """

        try:
            return isinstance(rhs, self._class_name)
        except TypeError:
            # Check raw types if there was a type error.  This is helpful for
            # things like cStringIO.StringIO.
            return isinstance(rhs, type(self._class_name))

    def _is_subclass(self, clazz: Any) -> bool:
        """Check to see if the IsA comparators class is a subclass of clazz.

        Args:
          # clazz: a class object

        Returns:
          bool
        """

        try:
            return issubclass(self._class_name, clazz)
        except TypeError:
            # Check raw types if there was a type error.  This is helpful for
            # things like cStringIO.StringIO.
            return isinstance(clazz, type(self._class_name))

    def __repr__(self) -> str:
        return "mox.IsA(%s) " % str(self._class_name)

    _IsSubClass = _is_subclass


class IsAlmost(Comparator):
    """Comparison class used to check whether a parameter is nearly equal
    to a given value.  Generally useful for floating point numbers.

    Example mock_dao.SetTimeout((IsAlmost(3.9)))
    """

    def __init__(self, float_value: float, places: int = 7) -> None:
        """Initialize IsAlmost.

        Args:
          float_value: The value for making the comparison.
          places: The number of decimal places to round to.
        """

        self._float_value = float_value
        self._places = places

    def equals(self, rhs: Any) -> bool:
        """Check to see if RHS is almost equal to float_value

        Args:
          rhs: the value to compare to float_value

        Returns:
          bool
        """

        try:
            return round(rhs - self._float_value, self._places) == 0
        except Exception:
            # This is probably because either float_value or rhs is not a
            # number.
            return False

    def __repr__(self) -> str:
        return str(self._float_value)


class StrContains(Comparator):
    """Comparison class used to check whether a substring exists in a
    string parameter.  This can be useful in mocking a database with SQL
    passed in as a string parameter, for example.

    Example:
    mock_dao.RunQuery(StrContains('IN (1, 2, 4, 5)')).AndReturn(mock_result)
    """

    def __init__(self, search_string: str) -> None:
        """Initialize.

        Args:
          # search_string: the string you are searching for
          search_string: str
        """

        self._search_string = search_string

    def equals(self, rhs: Any) -> bool:
        """Check to see if the search_string is contained in the rhs string.

        Args:
          # rhs: the right hand side of the test
          rhs: object

        Returns:
          bool
        """

        try:
            return rhs.find(self._search_string) > -1
        except Exception:
            return False

    def __repr__(self) -> str:
        return "<str containing '%s'>" % self._search_string


class Regex(Comparator):
    """Checks if a string matches a regular expression.

    This uses a given regular expression to determine equality.
    """

    def __init__(self, pattern: Any, flags: int = 0) -> None:
        """Initialize.

        Args:
          # pattern is the regular expression to search for
          pattern: str
          # flags passed to re.compile function as the second argument
          flags: int
        """

        self.regex = re.compile(pattern, flags=flags)

    def equals(self, rhs: Any) -> bool:
        """Check to see if rhs matches regular expression pattern.

        Returns:
          bool
        """

        try:
            return self.regex.search(rhs) is not None
        except Exception:
            return False

    def __repr__(self) -> str:
        pattern = self.regex.pattern
        if isinstance(pattern, bytes):
            pattern = pattern.decode()
        s = "<regular expression '{}'".format(pattern)
        if self.regex.flags:
            s += ", flags=%d" % self.regex.flags
        s += ">"
        return s


class In(Comparator):
    """Checks whether an item (or key) is in a list (or dict) parameter.

    Example:
    mock_dao.GetUsersInfo(In('expectedUserName')).AndReturn(mock_result)
    """

    def __init__(self, key: Any) -> None:
        """Initialize.

        Args:
          # key is anything that could be in a list or a key in a dict
        """

        self._key = key

    def equals(self, rhs: Any) -> bool:
        """Check to see whether key is in rhs.

        Args:
          rhs: dict

        Returns:
          bool
        """

        try:
            return self._key in rhs
        except Exception:
            return False

    def __repr__(self) -> str:
        return "<sequence or map containing '%s'>" % str(self._key)


class Not(Comparator):
    """Checks whether a predicates is False.

    Example:
      mock_dao.UpdateUsers(Not(ContainsKeyValue('stevepm', stevepm_user_info)))
    """

    def __init__(self, predicate: "Comparator") -> None:
        """Initialize.

        Args:
          # predicate: a Comparator instance.
        """

        if not isinstance(predicate, Comparator):
            raise Error("predicate %r must be a Comparator." % predicate)
        self._predicate = predicate

    def equals(self, rhs: Any) -> bool:
        """Check to see whether the predicate is False.

        Args:
          rhs: A value that will be given in argument of the predicate.

        Returns:
          bool
        """

        try:
            return not self._predicate.equals(rhs)
        except Exception:
            return False

    def __repr__(self) -> str:
        return "<not '%s'>" % self._predicate


class ContainsKeyValue(Comparator):
    """Checks whether a key/value pair is in a dict parameter.

    Example:
    mock_dao.UpdateUsers(ContainsKeyValue('stevepm', stevepm_user_info))
    """

    def __init__(self, key: Any, value: Any) -> None:
        """Initialize.

        Args:
          # key: a key in a dict
          # value: the corresponding value
        """

        self._key = key
        self._value = value

    def equals(self, rhs: Any) -> bool:
        """Check whether the given key/value pair is in the rhs dict.

        Returns:
          bool
        """

        try:
            return rhs[self._key] == self._value
        except Exception:
            return False

    def __repr__(self) -> str:
        return "<map containing the entry '%s: %s'>" % (
            str(self._key),
            str(self._value),
        )


class ContainsAttributeValue(Comparator):
    """Checks whether a passed parameter contains attributes with a given
    value.

    Example:
    mock_dao.UpdateSomething(ContainsAttribute('stevepm', stevepm_user_info))
    """

    def __init__(self, key: str, value: Any) -> None:
        """Initialize.

        Args:
          # key: an attribute name of an object
          # value: the corresponding value
        """

        self._key = key
        self._value = value

    def equals(self, rhs: Any) -> bool:
        """Check whether the given attribute has a matching value in the rhs
        object.

        Returns:
          bool
        """

        try:
            return getattr(rhs, self._key) == self._value
        except Exception:
            return False


class SameElementsAs(Comparator):
    """Checks whether sequences contain the same elements (ignoring order).

    Example:
    mock_dao.ProcessUsers(SameElementsAs('stevepm', 'salomaki'))
    """

    def __init__(self, expected_seq: Iterable[Any]) -> None:
        """Initialize.

        Args:
          expected_seq: a sequence
        """
        # Store in case expected_seq is an iterator.
        self._expected_list = list(expected_seq)

    def equals(self, actual_seq: Any) -> bool:
        """Check to see whether actual_seq has same elements as expected_seq.

        Args:
          actual_seq: sequence

        Returns:
          bool
        """
        try:
            # Store in case actual_seq is an iterator.  We potentially iterate
            # twice: once to make the dict, once in the list fallback.
            actual_list = list(actual_seq)
        except TypeError:
            # actual_seq cannot be read as a sequence.
            #
            # This happens because Mox uses __eq__ both to check object
            # equality (in MethodSignatureChecker) and to invoke Comparators.
            return False

        expected: Any
        actual: Any
        try:
            expected = dict([(element, None) for element in self._expected_list])
            actual = dict([(element, None) for element in actual_list])
        except TypeError:
            # Fall back to slower list-compare if any of the objects are
            # unhashable.
            expected = self._expected_list
            actual = actual_list
            for element in actual:
                if element not in expected:
                    return False
            for element in expected:
                if element not in actual:
                    return False
            return True
        else:
            return set(actual_list) == set(self._expected_list)

    def __repr__(self) -> str:
        return "<sequence with same elements as '%s'>" % self._expected_list


class And(Comparator):
    """Evaluates one or more Comparators on RHS and returns an AND of the
    results.
    """

    def __init__(self, *args: "Comparator") -> None:
        """Initialize.

        Args:
          *args: One or more Comparator
        """

        self._comparators = args

    def equals(self, rhs: Any) -> bool:
        """Checks whether all Comparators are equal to rhs.

        Args:
          # rhs: can be anything

        Returns:
          bool
        """

        for comparator in self._comparators:
            if not comparator.equals(rhs):
                return False

        return True

    def __repr__(self) -> str:
        return "<AND %s>" % str(self._comparators)


class Or(Comparator):
    """Evaluates one or more Comparators on RHS and returns an OR of the
    results.
    """

    def __init__(self, *args: "Comparator") -> None:
        """Initialize.

        Args:
          *args: One or more Mox comparators
        """

        self._comparators = args

    def equals(self, rhs: Any) -> bool:
        """Checks whether any Comparator is equal to rhs.

        Args:
          # rhs: can be anything

        Returns:
          bool
        """

        for comparator in self._comparators:
            if comparator.equals(rhs):
                return True

        return False

    def __repr__(self) -> str:
        return "<OR %s>" % str(self._comparators)


class Func(Comparator):
    """Call a function that should verify the parameter passed in is correct.

    You may need the ability to perform more advanced operations on the
    parameter in order to validate it.  You can use this to have a callable
    validate any parameter. The callable should return either True or False.


    Example:

    def myParamValidator(param):
      # Advanced logic here
      return True

    mock_dao.DoSomething(Func(myParamValidator), true)
    """

    def __init__(self, func: Callable[[Any], Any]) -> None:
        """Initialize.

        Args:
          func: callable that takes one parameter and returns a bool
        """

        self._func = func

    def equals(self, rhs: Any) -> bool:
        """Test whether rhs passes the function test.

        rhs is passed into func.

        Args:
          rhs: any python object

        Returns:
          the result of func(rhs)
        """

        return self._func(rhs)

    def __repr__(self) -> str:
        return str(self._func)


class IgnoreArg(Comparator):
    """Ignore an argument.

    This can be used when we don't care about an argument of a method call.

    Example:
    # Check if CastMagic is called with 3 as first arg and 'disappear' as
    third. mymock.CastMagic(3, IgnoreArg(), 'disappear')
    """

    def equals(self, unused_rhs: Any) -> bool:
        """Ignores arguments and returns True.

        Args:
          unused_rhs: any python object

        Returns:
          always returns True
        """

        return True

    def __repr__(self) -> str:
        return "<IgnoreArg>"


class Value(Comparator):
    """Compares argument against a remembered value.

    To be used in conjunction with Remember comparator.  See Remember()
    for example.
    """

    def __init__(self) -> None:
        self._value: Any = None
        self._has_value = False

    def store_value(self, rhs: Any) -> None:
        self._value = rhs
        self._has_value = True

    def equals(self, rhs: Any) -> bool:
        if not self._has_value:
            return False
        else:
            return rhs == self._value

    def __repr__(self) -> str:
        if self._has_value:
            return "<Value %r>" % self._value
        else:
            return "<Value>"


class Remember(Comparator):
    """Remembers the argument to a value store.

    To be used in conjunction with Value comparator.

    Example:
    # Remember the argument for one method call.
    users_list = Value()
    mock_dao.ProcessUsers(Remember(users_list))

    # Check argument against remembered value.
    mock_dao.ReportUsers(users_list)
    """

    def __init__(self, value_store: "Value") -> None:
        if not isinstance(value_store, Value):
            raise TypeError("value_store is not an instance of the Value class")
        self._value_store = value_store

    def equals(self, rhs: Any) -> bool:
        self._value_store.store_value(rhs)
        return True

    def __repr__(self) -> str:
        return "<Remember %d>" % id(self._value_store)


is_ = Is
is_a = IsA
is_almost = IsAlmost
str_contains = StrContains
regex = Regex
in_ = In
not_ = Not
contains_key_value = ContainsKeyValue
contains_attribute_value = ContainsAttributeValue
same_elements_as = SameElementsAs
and_ = And
or_ = Or
func = Func
ignore_arg = IgnoreArg
value = Value
remember = Remember
