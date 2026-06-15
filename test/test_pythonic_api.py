"""Tests for the context-manager-free entry points: the ``@mox.patch``
decorator and the ``mox`` pytest fixture."""

# Python imports
import os

# Pip imports
import pytest

# Internal imports
import mox

from . import mox_test_helper


# ---------------------------------------------------------------------------
# @mox.patch decorator
# ---------------------------------------------------------------------------


@mox.patch(os, "getcwd")
def test_patch_basic(m_getcwd):
    m_getcwd().returns("/mox/path")
    mox.replay(m_getcwd)
    assert os.getcwd() == "/mox/path"


@mox.patch("os.getcwd")
def test_patch_string_path(m_getcwd):
    m_getcwd().returns("/from/string")
    mox.replay(m_getcwd)
    assert os.getcwd() == "/from/string"


@mox.patch(os, "getcwd")
@mox.patch(os, "cpu_count")
def test_patch_stacked_injects_top_to_bottom(m_getcwd, m_cpu_count):
    m_getcwd().returns("/p")
    m_cpu_count().returns(4)
    mox.replay(m_getcwd, m_cpu_count)
    assert os.getcwd() == "/p"
    assert os.cpu_count() == 4


def test_patch_verifies_unmet_expectation():
    @mox.patch(os, "getcwd")
    def inner(m_getcwd):
        m_getcwd().returns("/never/called")
        mox.replay(m_getcwd)
        # deliberately do not call os.getcwd()

    with pytest.raises(mox.ExpectedMethodCallsError):
        inner()


def test_patch_restores_stub_on_success():
    original = os.getcwd

    @mox.patch(os, "getcwd")
    def inner(m_getcwd):
        m_getcwd().returns("/x")
        mox.replay(m_getcwd)
        assert os.getcwd() == "/x"
        assert os.getcwd is not original

    inner()
    assert os.getcwd is original


def test_patch_restores_stub_on_failure():
    original = os.getcwd

    @mox.patch(os, "getcwd")
    def inner(m_getcwd):
        raise ValueError("boom")

    with pytest.raises(ValueError, match="boom"):
        inner()
    # Stub must be restored even though the body raised...
    assert os.getcwd is original
    # ...and a failing body must not leak a verification error on top.


@mox.patch(os, "getcwd", use_mock_anything=True)
def test_patch_use_mock_anything(m_getcwd):
    m_getcwd().returns("/anything")
    mox.replay(m_getcwd)
    assert os.getcwd() == "/anything"


@mox.patch_class(mox_test_helper, "CallableClass")
def test_patch_class_factory(factory):
    instance = mox_test_helper.CallableClass(1, 2)
    instance.value().returns("mocked")
    mox.replay(factory)

    produced = mox_test_helper.CallableClass(1, 2)
    assert produced.value() == "mocked"


def test_patch_does_not_leak_instances():
    before = len(mox.Mox._instances)

    @mox.patch(os, "getcwd")
    def inner(m_getcwd):
        m_getcwd().returns("/x")
        mox.replay(m_getcwd)
        assert os.getcwd() == "/x"

    inner()
    assert len(mox.Mox._instances) == before


# ---------------------------------------------------------------------------
# mox pytest fixture
# ---------------------------------------------------------------------------


def test_mox_fixture_records_and_replays(mox):
    m_getcwd = mox.stubout(os, "getcwd")
    m_getcwd().returns("/fixture/path")
    mox.replay(m_getcwd)
    assert os.getcwd() == "/fixture/path"
    # No explicit verify(): the fixture verifies on teardown.


def test_mox_verify_alias_still_works(mox_verify):
    # ``mox_verify`` is the historical fixture name, kept as an alias of ``mox``.
    m = mox_verify.stubout(os, "getcwd")
    m().returns("/alias")
    mox_verify.replay(m)
    assert os.getcwd() == "/alias"


def test_mox_fixture_verifies_on_pass(pytester):
    pytester.makeconftest('pytest_plugins = ("mox.testing.pytest_mox",)')
    pytester.makepyfile(
        """
        import os
        import mox

        def test_unmet(mox):
            m = mox.stubout(os, "cpu_count")
            m().returns(4)
            mox.replay(m)
            # never call os.cpu_count() -> verify fails this otherwise-passing test
        """
    )
    result = pytester.runpytest_subprocess()
    # An unmet expectation surfaces from the fixture finalizer, which pytest
    # classifies as a teardown error (the test body itself still passed).
    result.assert_outcomes(passed=1, errors=1)
    result.stdout.fnmatch_lines(["*Expected methods never called*"])


def test_mox_fixture_does_not_mask_failure(pytester):
    pytester.makeconftest('pytest_plugins = ("mox.testing.pytest_mox",)')
    pytester.makepyfile(
        """
        import os
        import mox

        def test_body_fails(mox):
            m = mox.stubout(os, "cpu_count")
            m().returns(4)
            mox.replay(m)
            assert os.cpu_count() == 4
            assert False, "the real failure"
        """
    )
    result = pytester.runpytest_subprocess()
    result.assert_outcomes(failed=1)
    # The original assertion is what surfaces, not a verification error.
    result.stdout.fnmatch_lines(["*the real failure*"])


def test_mox_fixture_restores_stubs_between_tests(pytester):
    pytester.makeconftest('pytest_plugins = ("mox.testing.pytest_mox",)')
    pytester.makepyfile(
        """
        import os
        import mox

        def test_one(mox):
            m = mox.stubout(os, "getcwd")
            m().returns("/one")
            mox.replay(m)
            assert os.getcwd() == "/one"

        def test_two_sees_real_getcwd(mox):
            # If stubs leaked from test_one, os.getcwd would still be a mock.
            assert isinstance(os.getcwd(), str)
            assert os.getcwd() != "/one"
        """
    )
    result = pytester.runpytest_subprocess()
    result.assert_outcomes(passed=2)
