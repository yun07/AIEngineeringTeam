"""C2 (negative): module-level tkinter import must be detected by the guard.

Proves the AST guard in test_app_lazy_tkinter.py is not vacuous: it must flag
an eager module-level import while ignoring a function-local one.
"""

import ast
import importlib.util
import os
import sys

from app_support import PROJECT_DIR

_HERE = os.path.dirname(os.path.abspath(__file__))
_NAME = "app_lazy_helpers_under_test"


def _helpers():
    if _NAME in sys.modules:
        return sys.modules[_NAME]
    spec = importlib.util.spec_from_file_location(
        _NAME, os.path.join(_HERE, "test_app_lazy_tkinter.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _offenders(source):
    helpers = _helpers()
    tree = ast.parse(source)
    return [node for node in helpers._top_level_statements(tree)
            if helpers._is_tkinter_import(node)]


EAGER = "import tkinter\n\n\ndef main():\n    return 0\n"
EAGER_FROM = "from tkinter import Tk\n\n\ndef main():\n    return 0\n"
LAZY = "def main():\n    import tkinter as tk\n    return 0\n"
LAZY_FROM = "def main():\n    from tkinter import Tk\n    return 0\n"


def test_c2_guard_flags_eager_imports():
    assert _offenders(EAGER), "guard missed `import tkinter` at module level"
    assert _offenders(EAGER_FROM), "guard missed `from tkinter import Tk`"


def test_c2_guard_ignores_function_local_imports():
    assert _offenders(LAZY) == []
    assert _offenders(LAZY_FROM) == []


def test_c2_guard_flags_class_body_import():
    source = "class Renderer:\n    import tkinter\n"
    assert _offenders(source), "guard missed tkinter imported in a class body"


def test_c2_app_py_exists_and_is_non_empty():
    path = os.path.join(PROJECT_DIR, "app.py")
    assert os.path.getsize(path) > 0
