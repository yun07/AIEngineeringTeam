"""C3: README.md documents the graphical game and the headless mode.

The headless section must name `game.py` together with both `--seed` and
`--ticks` in an actual example command.
"""

import os
import re

from app_support import PROJECT_DIR

README_PATH = os.path.join(PROJECT_DIR, "README.md")


def _readme():
    with open(README_PATH, encoding="utf-8") as handle:
        return handle.read()


def test_c3_readme_exists_and_is_not_empty():
    assert os.path.isfile(README_PATH)
    text = _readme()
    assert len(text.strip()) > 0


def test_c3_readme_documents_graphical_launch():
    text = _readme()
    lowered = text.lower()
    assert "app.py" in text, "README must name app.py"
    # an actual launch command for the graphical mode
    assert re.search(r"python3?\s+app\.py", text), "no `python app.py` command"
    assert "tkinter" in lowered, "README must mention the optional tkinter renderer"


def test_c3_readme_documents_headless_seed_and_ticks():
    text = _readme()
    assert "headless" in text.lower(), "README must document the headless mode"
    # some command line must contain game.py with both --seed and --ticks
    for line in text.splitlines():
        if "game.py" not in line or not line.lstrip().startswith("python"):
            continue
        if "--seed" in line and "--ticks" in line:
            assert re.search(r"--seed\s+\d+", line), line
            assert re.search(r"--ticks\s+\d+", line), line
            return
    raise AssertionError("no `python game.py --seed N --ticks N` example found")
