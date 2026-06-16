"""Decorator entry points for stubbing without a context manager.

``mox.patch`` mirrors the ergonomics of ``unittest.mock.patch``: decorate a
test function, receive the mock as an extra argument, record your expectations,
call ``mox.replay(...)`` and exercise the code. Stubs are restored and (on a
passing test) the mock is verified automatically when the function returns::

    @mox.patch(os, "getcwd")
    def test_getcwd(m_getcwd):
        m_getcwd().returns("/mox/path")
        mox.replay(m_getcwd)
        assert os.getcwd() == "/mox/path"
        # stubs restored + m_getcwd verified automatically

Decorators stack, and the mocks are injected in the order the decorators are
written (top to bottom)::

    @mox.patch(os, "getcwd")
    @mox.patch(os, "cpu_count")
    def test_two(m_getcwd, m_cpu_count):
        ...
"""

import functools
import inspect
from typing import Any, Callable, Optional, TypeVar


F = TypeVar("F", bound=Callable[..., Any])


def _apply(target: Any, attr_name: Optional[str], use_mock_anything: bool, klass: bool, func: F) -> F:
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        from mox.mox import Mox

        m = Mox()
        if klass:
            stub = m.stubout_class(target, attr_name)
        else:
            stub = m.stubout(target, attr_name, use_mock_anything=use_mock_anything)

        try:
            result = func(*args, stub, **kwargs)
        except BaseException:
            # The test failed; restore stubs but do not verify - a verification
            # error here would mask the real failure.
            m.unset_stubs()
            Mox.forget(m)
            raise

        try:
            m.unset_stubs()
            m.verify_all()
        finally:
            Mox.forget(m)
        return result

    # The mock is injected as the wrapped function's last positional parameter.
    # Hide that parameter from introspection (notably pytest's fixture
    # resolution) so test runners don't try to supply it themselves. Stacked
    # decorators each peel off one more trailing parameter.
    try:
        signature = inspect.signature(func)
        parameters = list(signature.parameters.values())
        if parameters:
            wrapper.__signature__ = signature.replace(parameters=parameters[:-1])  # type: ignore[attr-defined]
    except (TypeError, ValueError):  # pragma: no cover - exotic callables
        pass

    return wrapper  # type: ignore[return-value]


def patch(target: Any, attr_name: Optional[str] = None, *, use_mock_anything: bool = False) -> Callable[[F], F]:
    """Stub out ``target.attr_name`` for the duration of the decorated test.

    Args:
      target: object, class, module, or a string import path (e.g.
        ``"os.getcwd"`` or ``"os"`` with ``attr_name="getcwd"``).
      attr_name: str. Name of the attribute to replace. May be omitted when
        ``target`` is a full string path.
      use_mock_anything: bool. Replace with a ``MockAnything`` (accepts any
        call) instead of a interface-mirroring ``MockObject``.

    The created mock is passed to the test as an extra positional argument.
    """

    def decorator(func: F) -> F:
        return _apply(target, attr_name, use_mock_anything, False, func)

    return decorator


def patch_class(target: Any, attr_name: Optional[str] = None) -> Callable[[F], F]:
    """Like :func:`patch`, but replaces a class with a mock factory.

    See ``Mox.stubout_class`` for the factory semantics.
    """

    def decorator(func: F) -> F:
        return _apply(target, attr_name, False, True, func)

    return decorator
