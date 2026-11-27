"""C1: import app succeeds with tkinter blocked, is silent, exposes main."""

import importlib
import os
import sys

from app_support import PROJECT_DIR, run_app_probe


def test_c1_app_import_with_tkinter_blocked_is_silent_and_has_main():
    proc = run_app_probe("""
import sys

class _Blocker:
    def find_spec(self, name, path=None, target=None):
        if name == "tkinter" or name.startswith("tkinter."):
            raise ImportError("tkinter is blocked by the QA harness")
        return None

sys.meta_path.insert(0, _Blocker())
import app
assert callable(app.main), "app.main is not callable"
print("OK")
""")
    assert proc.returncode == 0, (proc.returncode, proc.stdout, proc.stderr)
    # no output at all during the import: the only line is the probe's own.
    assert proc.stdout == "OK\n", repr(proc.stdout)
    assert proc.stderr == "", repr(proc.stderr)


def test_c1_app_main_is_callable_in_process():
    added = PROJECT_DIR not in sys.path
    if added:
        sys.path.insert(0, PROJECT_DIR)
    try:
        saved_tk = sys.modules.pop("tkinter", None)
        app = importlib.import_module("app")
    finally:
        if saved_tk is not None:
            sys.modules.setdefault("tkinter", saved_tk)
        if added:
            sys.path.remove(PROJECT_DIR)
    assert callable(getattr(app, "main", None))
    assert hasattr(app, "game"), "app must drive game.py"


def test_c1_app_file_exists_next_to_game():
    assert os.path.isfile(os.path.join(PROJECT_DIR, "app.py"))
    assert os.path.isfile(os.path.join(PROJECT_DIR, "game.py"))
