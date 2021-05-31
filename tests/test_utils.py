import pathlib
import pytest

import bgraph.utils


def test_recurse():

    # Empty mapping
    assert list(bgraph.utils.recurse({})) == []

    # Classic mapping
    mapping = {"a": "b", "c": "d"}
    for key, value in bgraph.utils.recurse(mapping):
        assert key in mapping
        assert value in mapping.values()

    # Finally, the recurse itself
    mapping = {"A": "b", "c": {"D": 0, "e": {"F": 0, "H": 1}}}
    expected_keys = {"A", "D", "F", "H"}
    for key, _ in bgraph.utils.recurse(mapping):
        assert key in expected_keys
        expected_keys.discard(key)

    assert len(expected_keys) == 0


def test_clean_mirror_path():

    # First, test if path/url is detected
    assert (
        type(bgraph.utils.clean_mirror_path("http://android.googlesource.com")) is str
    )
    assert isinstance(
        bgraph.utils.clean_mirror_path("/mnt/mirror/mirror_dir"), pathlib.Path
    )

    # Check if the last '/' is removed
    assert (
        bgraph.utils.clean_mirror_path("https://android.googlesource.com/")
        == "https://android.googlesource.com"
    )


def test_create_logger():

    logger = bgraph.utils.create_logger("bgraph.test_logger")
    assert logger
    assert len(logger.handlers) == 1

    logger2 = bgraph.utils.create_logger("bgraph.test_logger")
    assert logger2
    assert len(logger2.handlers) == 1

    logger3 = bgraph.utils.create_logger("bgraph.another_test_logger")
    assert logger3
    assert logger3 != logger2


def test_no_except():
    @bgraph.utils.no_except
    def func():
        raise ZeroDivisionError

    try:
        func()
    except ZeroDivisionError:
        pytest.fail("Exception should not have been raised")
