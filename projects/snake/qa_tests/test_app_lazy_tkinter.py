"""C2: app.py does not import tkinter at module load.

The tkinter import must live inside a function body, so a blocked tkinter
still allows `import app` to succeed (see test_app_import.py).
"""

import ast
import os

from app_support import PROJECT_DIR, run_app_probe

APP_PATH = os.path.join(PROJECT_DIR, "app.py")


def _module_source():
    with open(APP_PATH, encoding="utf-8") as handle:
        return handle.read()


def _is_tkinter_import(node):
    if isinstance(node, ast.Import):
        return any(a.name == "tkinter" or a.name.startswith("tkinter.")
                   for a in node.names)
    if isinstance(node, ast.ImportFrom):
        return (node.module or "").split(".")[0] == "tkinter"
    return False


def _top_level_statements(tree):
    """Yield only statements executed at module import time (no bodies)."""
    stack = list(tree.body)
    while stack:
        node = stack.pop()
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue  # its body runs only when called: lazy, not module load
        if isinstance(node, ast.ClassDef):
            stack.extend(node.body)  # class body does run at import time
            continue
        yield node
        for child in ast.iter_child_nodes(node):
            stack.append(child)


def test_c2_no_module_level_tkinter_import():
    tree = ast.parse(_module_source(), filename=APP_PATH)
    offenders = [getattr(node, "lineno", "?")
                 for node in _top_level_statements(tree)
                 if _is_tkinter_import(node)]
    assert offenders == [], f"module-level tkinter import at lines {offenders}"


def test_c2_tkinter_import_occurs_inside_a_function():
    tree = ast.parse(_module_source(), filename=APP_PATH)
    in_function = any(
        _is_tkinter_import(sub)
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        for sub in ast.walk(node)
    )
    assert in_function, "app.py never imports tkinter inside a function body"


def test_c2_import_app_loads_no_tkinter_module():
    proc = run_app_probe("""
import sys
import app
loaded = [m for m in sys.modules if m == "tkinter" or m.startswith("tkinter.")]
assert loaded == [], loaded
print("NO_TK")
""")
    assert proc.returncode == 0, (proc.returncode, proc.stdout, proc.stderr)
    assert proc.stdout.strip() == "NO_TK"
    assert proc.stderr == "", repr(proc.stderr)
