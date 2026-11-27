"""C1 (negative): app must degrade gracefully when no display exists.

A blocked tkinter import must make `main()` report the problem and return a
non-zero status instead of raising, so the optional renderer can never be
required for acceptance.
"""

import os
import sys

from app_support import PROJECT_DIR

PROBE = """
import sys

class _Blocker:
    def find_spec(self, name, path=None, target=None):
        if name == "tkinter" or name.startswith("tkinter."):
            raise ImportError("tkinter is blocked by the QA harness")
        return None

sys.meta_path.insert(0, _Blocker())
import app
try:
    status = app.main()
except BaseException as exc:  # must NOT happen
    print("RAISED:" + type(exc).__name__)
    raise SystemExit(3)
print("STATUS=%r" % (status,))
"""


def test_c1_missing_tkinter_main_falls_back_without_raising():
    import subprocess

    proc = subprocess.run(
        [sys.executable, "-c", PROBE],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
        timeout=60,
        env={**os.environ, "DISPLAY": ""},
    )
    assert proc.returncode == 0, (proc.returncode, proc.stdout, proc.stderr)
    assert "RAISED:" not in proc.stdout, proc.stdout
    assert "STATUS=" in proc.stdout, proc.stdout
    status = eval(proc.stdout.split("STATUS=")[1].strip().splitlines()[0])
    assert status != 0, "main() must signal the unavailable renderer"
    assert "game.py" in proc.stdout, "should point at the headless fallback"
