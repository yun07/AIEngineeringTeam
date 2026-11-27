"""Shared helper: import app.py in a subprocess with tkinter blocked."""

import os
import subprocess
import sys

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run_app_probe(script):
    """Run `script` in a fresh interpreter inside the project directory.

    Returns a CompletedProcess in text mode, so stdout/stderr are captured.
    """
    return subprocess.run(
        [sys.executable, "-c", script],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
        timeout=120,
    )


# Blocks any import of tkinter _and_ any submodule of it, then imports app.
BLOCK_TK_IMPORT = """
import sys

class _Blocker:
    def find_module(self, name, path=None):
        return None
    def find_spec(self, name, path=None, target=None):
        if name == "tkinter" or name.startswith("tkinter."):
            raise ImportError("tkinter is blocked by the QA harness")
        return None

sys.meta_path.insert(0, _Blocker())
import app
print("IMPORTED")
"""

# Same, but also reports whether tkinter ended up in sys.modules.
BLOCK_TK_AND_REPORT_MODULES = """
import json
import sys

class _Blocker:
    def find_spec(self, name, path=None, target=None):
        if name == "tkinter" or name.startswith("tkinter."):
            raise ImportError("tkinter is blocked by the QA harness")
        return None

sys.meta_path.insert(0, _Blocker())
before = set(sys.modules)
import app
after = set(sys.modules)
print(json.dumps({
    "callable_main": callable(getattr(app, "main", None)),
    "tkinter_loaded": any(m == "tkinter" or m.startswith("tkinter.")
                          for m in sys.modules),
    "new_modules": sorted(m for m in after - before),
}))
"""
