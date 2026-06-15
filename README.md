Python mocking on steroids.

|         |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
|---------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Docs    | [![Docs](https://readthedocs.org/projects/pymox/badge/?version=latest)](https://github.com/ivancrneto/pymox/actions/workflows/docs-release.yml)                                                                                                                                                                                                                                                                                                                                               |
| CI/CD   | [![CI - Test](https://github.com/ivancrneto/pymox/actions/workflows/tests.yml/badge.svg)](https://github.com/ivancrneto/pymox/actions/workflows/tests.yml) [![codecov](https://codecov.io/github/ivancrneto/pymox/graph/badge.svg?token=LXkOUCeOXK)](https://codecov.io/github/ivancrneto/pymox)                                                                                                                                                                                              |
| Package | [![PyPI - Version](https://img.shields.io/pypi/v/pymox.svg?logo=pypi&label=PyPI&logoColor=gold)](https://pypi.org/project/pymox/) [![PyPI - Downloads](https://img.shields.io/pypi/dm/pymox.svg?color=blue&label=Downloads&logo=pypi&logoColor=gold)](https://pypi.org/project/pymox/) [![PyPI - Python Version](https://img.shields.io/pypi/pyversions/pymox.svg?logo=python&label=Python&logoColor=gold)](https://pypi.org/project/pymox/)                                                  |
| Meta    | [![linting - Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black) [![types - Mypy](https://img.shields.io/badge/types-Mypy-blue.svg)](https://github.com/python/mypy) [![License](https://img.shields.io/badge/License-Apache%202.0-purple.svg)](https://opensource.org/licenses/Apache-2.0) [![GitHub Sponsors](https://img.shields.io/github/sponsors/ivancrneto?logo=GitHub%20Sponsors&style=social)](https://github.com/sponsors/ivancrneto) |


<!-- summary -->

## What

Pymox is mocking on steroids. It's a powerful mock object framework for Python, providing many
tools to help with your unit tests, so you can write them in an easy, quick and intuitive way.

## Why

Why `Pymox`? Python already has batteries included. It has its own `mock` library, widely used in
Python applications.

So, why `pytest`, given we have Python's `unittest`?
Why `arrow` or `pendulum` given we have Python's `datetime`?
Why `X`, given we have Python's `Y`?

You got it 😉!

Coming Soon
* Async support

Already here
* ~~Decorator~~ (`@mox.patch`)
* ~~Pytest fixture~~ (the `mox` fixture)
* ~~Ignore args~~ (`mox.ignore_arg`)
* ~~String imports~~

## How

### Install

<!-- install -->

```bash
pip install pymox
```
<!-- end-install -->

Both import names work and refer to the exact same package (`import pymox is import mox`):
```python
import mox      # the original import name
import pymox    # same thing, matches the PyPI name
```

## Cool Stuff

<!-- new-elegant -->

### New Elegant Way
```python
# conftest.py
pytest_plugins = ("mox.testing.pytest_mox",)


# test.py
from mox import expect, stubout


class TestOs:
     def test_getcwd(self):
        with stubout(os, 'getcwd') as m_getcwd, expect:
            m_getcwd.to_be.called_with().and_return('/mox/path')

        assert os.getcwd() == '/mox/path'
        mox.verify(m_getcwd)
```
<!-- end-new-elegant -->

If you want to be less verbose:
```python
class TestOs:
     def test_getcwd(self):
        with stubout(os, 'getcwd') as m_getcwd:
            m_getcwd().returns('/mox/path')

        assert os.getcwd() == '/mox/path'
        mox.verify(m_getcwd)
```
Anything you put inside the context manager is a call expectation, so to not expect any call you can:
```python
class TestOs:
     def test_getcwd(self):
        with stubout(os, 'getcwd') as m_getcwd:
            pass

        # will raise a UnexpectedMethodCallError
        assert os.getcwd() == '/mox/path'
        mox.verify(m_getcwd)
```
### No Context Manager? No Problem

Prefer not to use a `with` block? The same expectations can be set up with a
pytest fixture or a decorator — both restore the stubs and verify the mocks for
you when the test finishes.

Using the `mox` pytest fixture (no `with`, no explicit `verify`):
```python
# conftest.py
pytest_plugins = ("mox.testing.pytest_mox",)


# test.py
import os


def test_getcwd(mox):
    m_getcwd = mox.stubout(os, 'getcwd')
    m_getcwd().returns('/mox/path')
    mox.replay(m_getcwd)

    assert os.getcwd() == '/mox/path'
    # stubs restored + mocks verified automatically on a passing test
```
The `mox` fixture is a managed `Mox`, and also exposes the module helpers, so
`mox.stubout`, `mox.replay`, `mox.verify` and comparators like `mox.is_a` are
all reachable through that single name.

Using the `@mox.patch` decorator (à la `unittest.mock.patch`):
```python
import os
import mox


@mox.patch(os, 'getcwd')
def test_getcwd(m_getcwd):
    m_getcwd().returns('/mox/path')
    mox.replay(m_getcwd)

    assert os.getcwd() == '/mox/path'
    # stubs restored + m_getcwd verified automatically


# decorators stack; mocks are injected top-to-bottom
@mox.patch(os, 'getcwd')
@mox.patch(os, 'cpu_count')
def test_two(m_getcwd, m_cpu_count):
    m_getcwd().returns('/mox/path')
    m_cpu_count().returns(8)
    mox.replay(m_getcwd, m_cpu_count)

    assert os.getcwd() == '/mox/path'
    assert os.cpu_count() == 8
```

### Dict Access
```python
class TestDict:
    def test_dict_access(self):
        config = {'env': 'dev', 'reload': True}

        # doing in another way using create, but you can do with stubout too
        mock_config = mox.create(config)

        mock_config['env'].returns('prod')
        mock_config['reload'].returns(False)

        mox.replay(mock_config)
        assert mock_config['env'] == 'prod'
        assert mock_config['reload'] is False
        mox.verify(mock_config)
```
### Comparators
```python
class Client:
    def get(self, url, params):
        return requests.get(url, params)


class Service:
    def get_contacts(self):
        url = 'https://my.reallylong.service/api/v1/contacts/'
        params = {'added': '7days', 'order_by': '-created'}
        return Client().get(url, params)


class TestSevice:
    def test_get_contacts_comparators_str_and_key_value(self):
        with stubout(Client, 'get') as m_get:
            url = mox.str_contains('/api/v1/contacts')
            params = mox.contains_key_value('added', '7days')
            m_get(url, params).returns({})

        service = Service()
        assert service.get_contacts() == {}
        mox.verify(m_get)

    def test_get_contacts_comparators_and_func_in_is_a(self):
        with stubout(Client, 'get') as m_get:
            url = mox.func(lambda v: str.startswith(v, 'https://my.reallylong.service/'))
            params = mox.and_(
                mox.is_a(dict),
                mox.in_('added'),
            )
            m_get(url, params).returns({})

        service = Service()
        assert service.get_contacts() == {}
        mox.verify(m_get)

    def test_get_contacts_comparators_ignore_arg_not(self):
        with stubout(Client, 'get') as m_get:
            url = mox.ignore_arg()
            params = mox.not_(mox.is_(None))
            m_get(url, params).returns({})

        service = Service()
        assert service.get_contacts() == {}
        mox.verify(m_get)

```
Other comparators: `contains_attribute_value`, `in_`, `is_`, `is_almost`, `or_`, `same_elements_as`, `regex`

### And Raises
```python
class TestOs:
     def test_getcwd(self):
        with stubout(os, 'getcwd') as m_getcwd:
            # .and_raise(..) also works
            os.getcwd().raises(Exception('error'))

        with pytest.raises(Exception, match='error'):
            os.getcwd()
        mox.verify(m_getcwd)
```
### Multiple Times
```python
class TestOs:
     def test_getcwd(self):
        with stubout(os, 'getcwd') as m_getcwd:
            m_getcwd().returns('/mox/path')
            # the second call will return a different value
            m_getcwd().returns('/mox/another/path')
            # the three subsequent calls will return "/"
            # if no argument is passed, multiple_times doesn't limit the number of calls
            m_getcwd().multiple_times(3).returns('/')

        assert os.getcwd() == '/mox/path'
        assert os.getcwd() == '/mox/another/path'
        mox.verify(m_getcwd)
```
### Any order
If you stub out multiple, the order os calls is enforced, unless you use `any_order`
```python
class TestOs:
    def test_getcwd(self):
        with stubout.many([os, 'getcwd'], [os, 'cpu_count']) as (m_getcwd, m_cpu_count):
            m_getcwd().returns('/mox/path')
            m_cpu_count().returns('10')

        # will raise a UnexpectedMethodCallError
        assert os.cpu_count() == '10'
        assert os.getcwd() == '/mox/path'
        mox.verify(m_getcwd, m_cpu_count)

    def test_getcwd_anyorder(self):
        with stubout.many([os, 'getcwd'], [os, 'cpu_count']) as (m_getcwd, m_cpu_count):
            m_getcwd().any_order().returns('/mox/path')
            m_cpu_count().any_order().returns('10')

        assert os.cpu_count() == '10'
        assert os.getcwd() == '/mox/path'
        mox.verify(m_getcwd, m_cpu_count)
```
### Remember/Value
The Remember and Value are comparators, but they deserve their own section. They can be useful to
retrieve some values from deeper levels of your codebase, and bring to the test for comparison.
Let's see an example:
```python
class Handler:
    def modify(self, d):
        # any integer key less than 5 is removed from the dict
        keys_to_remove = [key for key in d if isinstance(key, int) and key < 5]
        for key in keys_to_remove:
            del d[key]
        return d

    def send(self, d):
        return d


class Manager:
    def __init__(self, handlers=None):
        self.handlers = handlers or []

    def process(self, d):
        for handler in self.handlers:
            modified = handler.modify(d)
            handler.send(modified)


class TestManager(mox.MoxTestBase):
    def test_manager_process(self):
        mydict = {1: "apple", 4: "banana", 6: {2: 3, 4: {1: "orange", 7: 8}}, 8: 3}
        myvalue = mox.value()

        with mox.stubout(Handler, 'send') as mock_send:
            # so we use remember in the send call, and its value then the function is
            # called will go to `myvalue`
            mock_send(mox.remember(myvalue))

        Manager([Handler()]).process(mydict)
        mox.verify(mock_send)

        # now we can compare myvalue with what we think its value must be
        assert myvalue == {6: {2: 3, 4: {1: 'orange', 7: 8}}, 8: 3}
```

<!-- classics -->

### Classic Way

```python
import mox
import os

class TestOs:
    def test_getcwd(self):
        m = mox.Mox()

        m.stubout(os, 'getcwd')
        # calls
        os.getcwd().returns('/mox/path')

        m.replay_all()
        assert os.getcwd() == '/mox/path'
        m.verify_all()


if __name__ == '__main__':
    import unittest
    unittest.main()
```

### Jurassic Way

```python
import mox
import os


class TestOs(mox.MoxTestBase):
    def test_getcwd(self):
        self.mox.StubOutWithMock(os, 'getcwd')
        # calls
        os.getcwd().AndReturn('/mox/path')

        self.mox.ReplayAll()
        self.assertEqual(os.getcwd(), '/mox/path')
        self.mox.VerifyAll()


if __name__ == '__main__':
    import unittest
    unittest.main()
```

<!-- end-classics -->

<!-- project links -->

### Project Links
* [Stack Overflow](https://stackoverflow.com/questions/tagged/pymox)
* [PyPI](https://pypi.org/project/pymox/)
* [GitHub](https://github.com/ivancrneto/pymox/)
* [Documentation](http://pymox.rtfd.io/)
* [Changelog](https://github.com/ivancrneto/pymox/blob/main/CHANGELOG.md)
