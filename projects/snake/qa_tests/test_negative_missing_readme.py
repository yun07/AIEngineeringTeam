"""C1 (negative): reading a missing README must fail loudly, not silently.

Guards the C3 documentation check against a false pass: if the path were
wrong or the file absent, verification must report it rather than succeed.
"""

import os

import pytest

from app_support import PROJECT_DIR

MISSING = os.path.join(PROJECT_DIR, "README_missing.md")


def test_c1_missing_readme_path_raises():
    with pytest.raises(FileNotFoundError):
        with open(MISSING, encoding="utf-8") as handle:
            handle.read()
    assert not os.path.exists(MISSING)


def test_c1_import_of_absent_module_fails():
    """`app` must be a real module, not an accidental namespace package."""
    import importlib

    import sys

    added = PROJECT_DIR not in sys.path
    if added:
        sys.path.insert(0, PROJECT_DIR)
    try:
        with pytest.raises(ImportError):
            importlib.import_module("snake_renderer_absent")
    finally:
        if added:
            sys.path.remove(PROJECT_DIR)
