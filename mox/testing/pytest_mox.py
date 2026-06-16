import pytest


class _MoxFixture:
    """Thin facade yielded by the ``mox`` fixture.

    Because the fixture is named ``mox``, it shadows the ``mox`` module inside a
    test. This facade keeps the whole API reachable through that one name: it
    forwards to the managed :class:`mox.Mox` instance first (``stubout``,
    ``replay_all``, ``create_mock`` ...) and falls back to the ``mox`` module
    for everything else (``replay``, ``verify``, comparators like ``is_a`` ...).
    """

    def __init__(self, mox_obj):
        self._mox = mox_obj

    def __getattr__(self, name):
        try:
            return getattr(self._mox, name)
        except AttributeError:
            import mox

            return getattr(mox, name)


@pytest.fixture
def mox(request):
    """Yield a managed Mox for context-manager-free mocking.

    Record expectations, call ``mox.replay(...)`` (or ``mox.replay_all()``),
    then exercise your code::

        def test_getcwd(mox):
            m = mox.stubout(os, "getcwd")
            m().returns("/mox/path")
            mox.replay(m)
            assert os.getcwd() == "/mox/path"

    Stubs are always restored when the test finishes. On a passing test the
    mocks are verified automatically, so no explicit ``verify`` call is needed.
    """
    from mox import Mox

    mox_obj = Mox()
    try:
        yield _MoxFixture(mox_obj)
    finally:
        try:
            mox_obj.unset_stubs()
            if not _test_failed(request.node):
                mox_obj.verify_all()
        finally:
            Mox.forget(mox_obj)


# Backwards-compatible alias for the historical fixture name.
@pytest.fixture
def mox_verify(mox):
    return mox


def _test_failed(node):
    """Whether the test body (or its setup) failed, per the stored report."""
    return getattr(node, "_mox_setup_failed", False) or getattr(node, "_mox_call_failed", False)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Record per-phase pass/fail so the ``mox`` fixture can skip verification
    on a failing test (verifying then would mask the real failure)."""
    outcome = yield
    report = outcome.get_result()
    setattr(item, "_mox_%s_failed" % report.when, report.failed)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_teardown(item):
    """Global cleanup for the context-manager API (``mox.expect`` / ``mox.create``).

    Runs as a hook *wrapper* so the post-yield cleanup happens after fixture
    finalizers (including the ``mox`` fixture's own verify); otherwise clearing
    the registry first would empty the fixture's mocks before they are verified.
    """
    yield

    import mox

    try:
        mox.Mox.global_unset_stubs()
    finally:
        # Forget every tracked Mox so instances neither leak for the life of the
        # process nor get re-verified during a later test's teardown.
        mox.Mox.reset_instances()
